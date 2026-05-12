from __future__ import annotations

from pathlib import Path

from rent_pulse.config import RentPulseConfig


class PostgresStager:
    def __init__(self, config: RentPulseConfig):
        config.require("postgres_url")
        self.config = config

    def _connect(self):
        import psycopg2

        return psycopg2.connect(self.config.postgres_url)

    def ensure_schema(self) -> None:
        schema_path = self.config.project_root / "sql" / "postgres" / "001_staging_schema.sql"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(schema_path.read_text(encoding="utf-8"))

    def stage_records(self, records: list[dict]) -> None:
        if not records:
            return
        import psycopg2.extras

        rows = [
            (
                record["dataset_name"],
                record["dataset_type"],
                record["source_url"],
                record["source_row_id"],
                record["record_hash"],
                record["run_id"],
                record.get("original_s3_key"),
                record["extracted_at"],
                record["ingested_at"],
                psycopg2.extras.Json(record["payload"]),
            )
            for record in records
        ]
        sql = """
            insert into rentpulse_staging.raw_records (
                dataset_name,
                dataset_type,
                source_url,
                source_row_id,
                record_hash,
                run_id,
                original_s3_key,
                extracted_at,
                ingested_at,
                payload
            )
            values %s
            on conflict (dataset_name, source_row_id, record_hash) do nothing
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                psycopg2.extras.execute_values(cursor, sql, rows, page_size=1000)
