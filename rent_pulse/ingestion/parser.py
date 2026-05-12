from __future__ import annotations

import csv
import io
import json
from typing import Any


def _stringify_row(row: dict[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in row.items()}


def parse_dataset_bytes(content: bytes, file_format: str) -> list[dict[str, Any]]:
    normalized_format = file_format.lower().strip(".")
    if normalized_format == "csv":
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        return [_stringify_row(dict(row)) for row in reader]
    if normalized_format == "json":
        payload = json.loads(content.decode("utf-8"))
        if isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict):
            rows = payload.get("records") or payload.get("data") or payload.get("rows") or []
        else:
            rows = []
        return [_stringify_row(row) for row in rows if isinstance(row, dict)]
    raise ValueError(f"Unsupported source format: {file_format}")
