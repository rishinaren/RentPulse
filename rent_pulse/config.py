from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_FILE = PROJECT_ROOT / "config" / "sources.json"

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return value.strip() if value is not None else default


@dataclass(frozen=True)
class DatasetSource:
    name: str
    dataset_type: str
    url: str
    file_format: str = "csv"
    primary_key: tuple[str, ...] = field(default_factory=tuple)
    enabled: bool = True
    attribution: str = ""
    notes: str = ""
    url_env: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DatasetSource":
        return cls(
            name=payload["name"],
            dataset_type=payload["dataset_type"],
            url=payload["url"],
            file_format=payload.get("format", payload.get("file_format", "csv")),
            primary_key=tuple(payload.get("primary_key", [])),
            enabled=bool(payload.get("enabled", True)),
            attribution=payload.get("attribution", ""),
            notes=payload.get("notes", ""),
            url_env=payload.get("url_env"),
        )

    def resolved_url(self) -> str:
        if self.url_env:
            override = _env(self.url_env)
            if override:
                return override
        return self.url


@dataclass(frozen=True)
class RentPulseConfig:
    project_root: Path
    source_file: Path
    environment: str
    local_tmp_dir: Path
    aws_region: str
    s3_bucket: str
    s3_prefix: str
    glue_database: str
    glue_role_arn: str
    glue_crawler_name: str
    athena_workgroup: str
    athena_output: str
    athena_raw_table: str
    postgres_url: str
    snowflake_account: str
    snowflake_user: str
    snowflake_password: str
    snowflake_role: str
    snowflake_warehouse: str
    snowflake_database: str
    snowflake_schema: str
    snowflake_storage_integration: str
    snowflake_s3_stage_name: str
    dbt_cloud_account_id: str
    dbt_cloud_job_id: str
    dbt_cloud_api_token: str
    quicksight_account_id: str
    quicksight_namespace: str
    quicksight_dataset_ids: tuple[str, ...]
    quicksight_dashboard_id: str
    quicksight_share_principal_arn: str

    @classmethod
    def from_env(cls, project_root: Path | None = None) -> "RentPulseConfig":
        root = project_root or PROJECT_ROOT
        source_file = Path(_env("RENTPULSE_SOURCE_FILE", str(DEFAULT_SOURCE_FILE)))
        if not source_file.is_absolute():
            source_file = root / source_file
        tmp_dir = Path(_env("RENTPULSE_LOCAL_TMP_DIR", ".tmp/rentpulse"))
        if not tmp_dir.is_absolute():
            tmp_dir = root / tmp_dir
        dataset_ids = tuple(
            item.strip()
            for item in _env("RENTPULSE_QUICKSIGHT_DATASET_IDS").split(",")
            if item.strip()
        )
        return cls(
            project_root=root,
            source_file=source_file,
            environment=_env("RENTPULSE_ENV", "dev"),
            local_tmp_dir=tmp_dir,
            aws_region=_env("AWS_REGION", "us-east-1"),
            s3_bucket=_env("RENTPULSE_S3_BUCKET"),
            s3_prefix=_env("RENTPULSE_S3_PREFIX", "rentpulse").strip("/"),
            glue_database=_env("RENTPULSE_GLUE_DATABASE", "rentpulse_raw"),
            glue_role_arn=_env("RENTPULSE_GLUE_ROLE_ARN"),
            glue_crawler_name=_env("RENTPULSE_GLUE_CRAWLER_NAME", "rentpulse-normalized-crawler"),
            athena_workgroup=_env("RENTPULSE_ATHENA_WORKGROUP", "primary"),
            athena_output=_env("RENTPULSE_ATHENA_OUTPUT"),
            athena_raw_table=_env("RENTPULSE_ATHENA_RAW_TABLE", "raw_records"),
            postgres_url=_env("RENTPULSE_POSTGRES_URL"),
            snowflake_account=_env("SNOWFLAKE_ACCOUNT"),
            snowflake_user=_env("SNOWFLAKE_USER"),
            snowflake_password=_env("SNOWFLAKE_PASSWORD"),
            snowflake_role=_env("SNOWFLAKE_ROLE", "RENTPULSE_ROLE"),
            snowflake_warehouse=_env("SNOWFLAKE_WAREHOUSE", "RENTPULSE_WH"),
            snowflake_database=_env("SNOWFLAKE_DATABASE", "RENTPULSE"),
            snowflake_schema=_env("SNOWFLAKE_SCHEMA", "RAW"),
            snowflake_storage_integration=_env("SNOWFLAKE_STORAGE_INTEGRATION", "RENTPULSE_S3_INT"),
            snowflake_s3_stage_name=_env("SNOWFLAKE_S3_STAGE_NAME", "RENTPULSE_RAW_STAGE"),
            dbt_cloud_account_id=_env("DBT_CLOUD_ACCOUNT_ID"),
            dbt_cloud_job_id=_env("DBT_CLOUD_JOB_ID"),
            dbt_cloud_api_token=_env("DBT_CLOUD_API_TOKEN"),
            quicksight_account_id=_env("RENTPULSE_QUICKSIGHT_AWS_ACCOUNT_ID"),
            quicksight_namespace=_env("RENTPULSE_QUICKSIGHT_NAMESPACE", "default"),
            quicksight_dataset_ids=dataset_ids,
            quicksight_dashboard_id=_env("RENTPULSE_QUICKSIGHT_DASHBOARD_ID", "rentpulse-public-dashboard"),
            quicksight_share_principal_arn=_env("RENTPULSE_QUICKSIGHT_SHARE_PRINCIPAL_ARN"),
        )

    def require(self, *field_names: str) -> None:
        missing = [name for name in field_names if not getattr(self, name)]
        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(f"Missing required RentPulse configuration: {joined}")


def load_sources(config: RentPulseConfig | None = None) -> list[DatasetSource]:
    active_config = config or RentPulseConfig.from_env()
    with active_config.source_file.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return [
        DatasetSource.from_dict(source)
        for source in payload.get("sources", [])
        if source.get("enabled", True)
    ]


def project_path(path: str | Path, config: RentPulseConfig | None = None) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    active_config = config or RentPulseConfig.from_env()
    return active_config.project_root / candidate
