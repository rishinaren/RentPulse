from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable

from rent_pulse.config import DatasetSource


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(payload: Any) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def source_row_id(row: dict[str, Any], source: DatasetSource, row_number: int) -> str:
    if source.primary_key:
        parts = []
        for key in source.primary_key:
            value = row.get(key)
            if value is None:
                value = row.get(key.lower())
            if value is None:
                value = row.get(key.replace(" ", "_"))
            parts.append(str(value or ""))
        if any(parts):
            return "|".join(parts)
    return f"{source.name}:{row_number}"


def build_raw_records(
    rows: Iterable[dict[str, Any]],
    source: DatasetSource,
    run_id: str,
    original_s3_key: str | None = None,
) -> list[dict[str, Any]]:
    ingested_at = utc_now_iso()
    records: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        row_id = source_row_id(row, source, index)
        record_payload = {
            "dataset_name": source.name,
            "dataset_type": source.dataset_type,
            "source_url": source.resolved_url(),
            "source_row_id": row_id,
            "payload": row,
        }
        records.append(
            {
                "dataset_name": source.name,
                "dataset_type": source.dataset_type,
                "source_url": source.resolved_url(),
                "source_row_id": row_id,
                "record_hash": stable_hash(record_payload),
                "extracted_at": ingested_at,
                "ingested_at": ingested_at,
                "run_id": run_id,
                "original_s3_key": original_s3_key,
                "payload": row,
            }
        )
    return records


def records_to_jsonl(records: Iterable[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(record, sort_keys=True, default=str) for record in records) + "\n"
