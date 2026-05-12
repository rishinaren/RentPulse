from __future__ import annotations

import time
from pathlib import Path

from rent_pulse.config import RentPulseConfig


REQUIRED_DATASETS = {
    "zillow_zori_zip",
    "zillow_inventory_zip",
    "nyc_housing_units_by_building",
    "nyc_dob_approved_permits",
    "mta_subway_stations",
    "listing_snapshots",
}


def _named_statements(name: str, statement_text: str) -> list[tuple[str, str]]:
    statements = [statement.strip() for statement in statement_text.split(";") if statement.strip()]
    if len(statements) <= 1:
        return [(name, statements[0])] if statements else []
    return [(f"{name}_{index}", statement) for index, statement in enumerate(statements, start=1)]


def _split_sql_file(sql_text: str) -> list[tuple[str, str]]:
    queries: list[tuple[str, str]] = []
    current_name = "validation_query"
    statement_parts: list[str] = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("-- name:"):
            if statement_parts:
                queries.extend(_named_statements(current_name, "\n".join(statement_parts)))
                statement_parts = []
            current_name = stripped.split(":", 1)[1].strip()
            continue
        if stripped and not stripped.startswith("--"):
            statement_parts.append(line)
    if statement_parts:
        queries.extend(_named_statements(current_name, "\n".join(statement_parts)))
    return [(name, sql) for name, sql in queries if sql]


class AthenaValidator:
    def __init__(self, config: RentPulseConfig):
        config.require("athena_output")
        self.config = config
        import boto3

        self.client = boto3.client("athena", region_name=config.aws_region)

    def _render(self, sql: str) -> str:
        return (
            sql.replace("${glue_database}", self.config.glue_database)
            .replace("${raw_table}", self.config.athena_raw_table)
            .replace("${s3_bucket}", self.config.s3_bucket)
            .replace("${s3_prefix}", self.config.s3_prefix)
        )

    def _query_result_rows(self, query_id: str) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        next_token: str | None = None
        columns: list[str] | None = None
        while True:
            kwargs = {"QueryExecutionId": query_id}
            if next_token:
                kwargs["NextToken"] = next_token
            response = self.client.get_query_results(**kwargs)
            metadata = response.get("ResultSet", {}).get("ResultSetMetadata", {})
            if columns is None:
                columns = [column["Name"] for column in metadata.get("ColumnInfo", [])]
            for result_row in response.get("ResultSet", {}).get("Rows", []):
                values = [cell.get("VarCharValue", "") for cell in result_row.get("Data", [])]
                if columns and values == columns:
                    continue
                padded_values = values + [""] * max(len(columns or []) - len(values), 0)
                rows.append(dict(zip(columns or [], padded_values)))
            next_token = response.get("NextToken")
            if not next_token:
                return rows

    def _validate_result_rows(self, name: str, rows: list[dict[str, str]]) -> str:
        normalized_name = name.lower()
        if normalized_name == "raw_record_counts":
            if not rows:
                raise RuntimeError("Athena validation raw_record_counts failed: no raw records found")
            empty_datasets = [row.get("dataset_name", "") for row in rows if int(row.get("record_count", "0") or 0) <= 0]
            if empty_datasets:
                joined = ", ".join(empty_datasets)
                raise RuntimeError(f"Athena validation raw_record_counts failed: empty datasets {joined}")
            return "passed"
        if normalized_name == "required_dataset_presence":
            loaded_count = int(rows[0].get("loaded_dataset_count", "0") if rows else "0")
            if loaded_count < len(REQUIRED_DATASETS):
                raise RuntimeError(
                    "Athena validation required_dataset_presence failed: "
                    f"loaded {loaded_count} of {len(REQUIRED_DATASETS)} required datasets"
                )
            return "passed"
        if normalized_name == "duplicate_record_hashes":
            if rows:
                examples = ", ".join(
                    f"{row.get('dataset_name', '')}:{row.get('record_hash', '')}" for row in rows[:5]
                )
                raise RuntimeError(f"Athena validation duplicate_record_hashes failed: {examples}")
            return "passed"
        if normalized_name == "listing_snapshot_price_quality":
            invalid_count = int(rows[0].get("invalid_listing_rent_count", "0") if rows else "0")
            if invalid_count:
                raise RuntimeError(
                    "Athena validation listing_snapshot_price_quality failed: "
                    f"{invalid_count} listing snapshots have invalid rent"
                )
            return "passed"
        return "not_applicable"

    def run_query(self, name: str, sql: str) -> dict[str, str]:
        rendered = self._render(sql)
        response = self.client.start_query_execution(
            QueryString=rendered,
            QueryExecutionContext={"Database": self.config.glue_database},
            ResultConfiguration={"OutputLocation": self.config.athena_output},
            WorkGroup=self.config.athena_workgroup,
        )
        query_id = response["QueryExecutionId"]
        while True:
            status_response = self.client.get_query_execution(QueryExecutionId=query_id)
            status = status_response["QueryExecution"]["Status"]["State"]
            if status in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                break
            time.sleep(2)
        if status != "SUCCEEDED":
            reason = status_response["QueryExecution"]["Status"].get("StateChangeReason", "")
            raise RuntimeError(f"Athena validation {name} {status}: {reason}")
        rows = self._query_result_rows(query_id)
        validation = self._validate_result_rows(name, rows)
        return {"name": name, "query_execution_id": query_id, "state": status, "validation": validation}

    def run_file(self, sql_path: Path) -> list[dict[str, str]]:
        queries = _split_sql_file(sql_path.read_text(encoding="utf-8"))
        return [self.run_query(name, sql) for name, sql in queries]


def run_athena_validations(
    sql_file: str | Path = "athena/validation_queries.sql",
    config: RentPulseConfig | None = None,
) -> list[dict[str, str]]:
    active_config = config or RentPulseConfig.from_env()
    path = Path(sql_file)
    if not path.is_absolute():
        path = active_config.project_root / path
    return AthenaValidator(active_config).run_file(path)
