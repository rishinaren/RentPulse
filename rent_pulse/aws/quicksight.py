from __future__ import annotations

import json
import time
from pathlib import Path

from rent_pulse.config import RentPulseConfig


class QuickSightPublisher:
    def __init__(self, config: RentPulseConfig):
        config.require("quicksight_account_id")
        self.config = config
        import boto3

        self.client = boto3.client("quicksight", region_name=config.aws_region)

    def refresh_datasets(self) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        for dataset_id in self.config.quicksight_dataset_ids:
            ingestion_id = f"rentpulse-{int(time.time())}"
            response = self.client.create_ingestion(
                AwsAccountId=self.config.quicksight_account_id,
                DataSetId=dataset_id,
                IngestionId=ingestion_id,
            )
            results.append(
                {
                    "dataset_id": dataset_id,
                    "ingestion_id": ingestion_id,
                    "status": response.get("IngestionStatus", "REQUESTED"),
                }
            )
        return results

    def create_or_update_snowflake_data_source(self, manifest: dict) -> dict[str, str]:
        from botocore.exceptions import ClientError

        self.config.require("snowflake_account", "snowflake_user", "snowflake_password")
        data_source = manifest["data_source"]
        parameters = {
            "SnowflakeParameters": {
                "Host": data_source.get("host", self.config.snowflake_account),
                "Database": data_source.get("database", self.config.snowflake_database),
                "Warehouse": data_source.get("warehouse", self.config.snowflake_warehouse),
            }
        }
        credentials = {
            "CredentialPair": {
                "Username": data_source.get("username", self.config.snowflake_user),
                "Password": data_source.get("password", self.config.snowflake_password),
            }
        }
        create_args = {
            "AwsAccountId": self.config.quicksight_account_id,
            "DataSourceId": data_source["id"],
            "Name": data_source["name"],
            "Type": "SNOWFLAKE",
            "DataSourceParameters": parameters,
            "Credentials": credentials,
        }
        update_args = {key: value for key, value in create_args.items() if key != "Type"}
        try:
            self.client.create_data_source(**create_args)
            action = "created"
        except ClientError as error:
            if error.response["Error"]["Code"] != "ResourceExistsException":
                raise
            self.client.update_data_source(**update_args)
            action = "updated"
        return {"data_source_id": data_source["id"], "action": action}

    def create_or_update_dataset(self, data_source_arn: str, dataset: dict) -> dict[str, str]:
        from botocore.exceptions import ClientError

        args = {
            "AwsAccountId": self.config.quicksight_account_id,
            "DataSetId": dataset["id"],
            "Name": dataset["name"],
            "ImportMode": dataset.get("import_mode", "SPICE"),
            "PhysicalTableMap": {
                dataset["physical_table_id"]: {
                    "CustomSql": {
                        "DataSourceArn": data_source_arn,
                        "Name": dataset["name"],
                        "SqlQuery": dataset["sql"],
                        "Columns": dataset["columns"],
                    }
                }
            },
        }
        try:
            self.client.create_data_set(**args)
            action = "created"
        except ClientError as error:
            if error.response["Error"]["Code"] != "ResourceExistsException":
                raise
            self.client.update_data_set(**args)
            action = "updated"
        return {"dataset_id": dataset["id"], "action": action}

    def publish_from_manifest(self, manifest_path: Path) -> list[dict[str, str]]:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        results = [self.create_or_update_snowflake_data_source(manifest)]
        data_source_id = manifest["data_source"]["id"]
        data_source_arn = (
            f"arn:aws:quicksight:{self.config.aws_region}:{self.config.quicksight_account_id}:"
            f"datasource/{data_source_id}"
        )
        for dataset in manifest.get("datasets", []):
            results.append(self.create_or_update_dataset(data_source_arn, dataset))
        return results

    def share_dashboard(self) -> dict[str, str]:
        if not self.config.quicksight_share_principal_arn:
            return {"dashboard_id": self.config.quicksight_dashboard_id, "share": "skipped"}
        self.client.update_dashboard_permissions(
            AwsAccountId=self.config.quicksight_account_id,
            DashboardId=self.config.quicksight_dashboard_id,
            GrantPermissions=[
                {
                    "Principal": self.config.quicksight_share_principal_arn,
                    "Actions": [
                        "quicksight:DescribeDashboard",
                        "quicksight:ListDashboardVersions",
                        "quicksight:QueryDashboard",
                    ],
                }
            ],
        )
        return {"dashboard_id": self.config.quicksight_dashboard_id, "share": "updated"}


def refresh_quicksight_datasets(config: RentPulseConfig | None = None) -> list[dict[str, str]]:
    return QuickSightPublisher(config or RentPulseConfig.from_env()).refresh_datasets()


def publish_quicksight_assets(
    manifest_file: str | Path = "quicksight/dashboard_manifest.json",
    config: RentPulseConfig | None = None,
) -> list[dict[str, str]]:
    active_config = config or RentPulseConfig.from_env()
    path = Path(manifest_file)
    if not path.is_absolute():
        path = active_config.project_root / path
    publisher = QuickSightPublisher(active_config)
    results = publisher.publish_from_manifest(path)
    results.append(publisher.share_dashboard())
    return results
