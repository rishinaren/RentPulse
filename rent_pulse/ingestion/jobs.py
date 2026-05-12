from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from rent_pulse.config import DatasetSource, RentPulseConfig, load_sources
from rent_pulse.ingestion.fetchers import fetch_source
from rent_pulse.ingestion.parser import parse_dataset_bytes
from rent_pulse.records import build_raw_records, records_to_jsonl
from rent_pulse.storage.postgres import PostgresStager
from rent_pulse.storage.s3 import S3Landing


@dataclass(frozen=True)
class IngestionResult:
    source_name: str
    dataset_type: str
    row_count: int
    original_s3_key: str | None
    normalized_s3_key: str | None
    postgres_staged: bool


def _select_sources(sources: list[DatasetSource], requested: list[str] | None) -> list[DatasetSource]:
    if not requested:
        return sources
    requested_set = set(requested)
    selected = [source for source in sources if source.name in requested_set or source.dataset_type in requested_set]
    missing = requested_set - {source.name for source in selected} - {source.dataset_type for source in selected}
    if missing:
        raise ValueError(f"Unknown RentPulse source(s): {', '.join(sorted(missing))}")
    return selected


def run_ingestion(
    source_names: list[str] | None = None,
    dry_run: bool = False,
    upload_to_s3: bool = True,
    stage_postgres: bool = True,
    config: RentPulseConfig | None = None,
) -> list[IngestionResult]:
    active_config = config or RentPulseConfig.from_env()
    run_id = uuid.uuid4().hex
    ingest_date = datetime.now(timezone.utc).date().isoformat()
    sources = _select_sources(load_sources(active_config), source_names)
    s3_landing = S3Landing(active_config) if upload_to_s3 and not dry_run else None
    postgres = PostgresStager(active_config) if stage_postgres and not dry_run and active_config.postgres_url else None

    if postgres:
        postgres.ensure_schema()

    results: list[IngestionResult] = []
    for source in sources:
        downloaded = fetch_source(source, active_config)
        rows = parse_dataset_bytes(downloaded.content, source.file_format)
        original_s3_key = None
        normalized_s3_key = None

        if s3_landing:
            extension = source.file_format.lower().strip(".")
            original_s3_key = s3_landing.raw_key(source.name, extension, ingest_date, run_id)
            s3_landing.put_bytes(original_s3_key, downloaded.content, downloaded.content_type)

        records = build_raw_records(rows, source, run_id, original_s3_key=original_s3_key)

        if s3_landing:
            normalized_s3_key = s3_landing.normalized_key(source.name, ingest_date, run_id)
            s3_landing.put_text(normalized_s3_key, records_to_jsonl(records), "application/json")

        postgres_staged = False
        if postgres:
            postgres.stage_records(records)
            postgres_staged = True

        results.append(
            IngestionResult(
                source_name=source.name,
                dataset_type=source.dataset_type,
                row_count=len(records),
                original_s3_key=original_s3_key,
                normalized_s3_key=normalized_s3_key,
                postgres_staged=postgres_staged,
            )
        )
    return results
