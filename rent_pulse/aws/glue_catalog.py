from __future__ import annotations

import time

from rent_pulse.config import RentPulseConfig


class GlueCatalogManager:
    def __init__(self, config: RentPulseConfig):
        config.require("s3_bucket", "glue_role_arn")
        self.config = config
        import boto3

        self.client = boto3.client("glue", region_name=config.aws_region)

    @property
    def normalized_s3_target(self) -> str:
        prefix = self.config.s3_prefix.strip("/")
        path = f"{prefix}/normalized/" if prefix else "normalized/"
        return f"s3://{self.config.s3_bucket}/{path}"

    def ensure_database(self) -> None:
        from botocore.exceptions import ClientError

        try:
            self.client.create_database(
                DatabaseInput={
                    "Name": self.config.glue_database,
                    "Description": "RentPulse raw and normalized data lake catalog",
                }
            )
        except ClientError as error:
            if error.response["Error"]["Code"] != "AlreadyExistsException":
                raise

    def ensure_crawler(self) -> None:
        from botocore.exceptions import ClientError

        crawler_input = {
            "Name": self.config.glue_crawler_name,
            "Role": self.config.glue_role_arn,
            "DatabaseName": self.config.glue_database,
            "Description": "Catalog RentPulse normalized JSONL records in S3",
            "Targets": {"S3Targets": [{"Path": self.normalized_s3_target}]},
            "SchemaChangePolicy": {
                "UpdateBehavior": "UPDATE_IN_DATABASE",
                "DeleteBehavior": "LOG",
            },
            "Configuration": '{"Version":1.0,"CrawlerOutput":{"Partitions":{"AddOrUpdateBehavior":"InheritFromTable"}}}',
        }
        try:
            self.client.create_crawler(**crawler_input)
        except ClientError as error:
            if error.response["Error"]["Code"] != "AlreadyExistsException":
                raise
            update_input = crawler_input.copy()
            update_input.pop("Name")
            self.client.update_crawler(Name=self.config.glue_crawler_name, **update_input)

    def start_crawler(self) -> str:
        from botocore.exceptions import ClientError

        try:
            self.client.start_crawler(Name=self.config.glue_crawler_name)
            return "STARTED"
        except ClientError as error:
            if error.response["Error"]["Code"] == "CrawlerRunningException":
                return "ALREADY_RUNNING"
            raise

    def wait_for_crawler(self, max_wait_seconds: int = 900, poll_seconds: int = 15) -> str:
        deadline = time.monotonic() + max_wait_seconds
        while True:
            response = self.client.get_crawler(Name=self.config.glue_crawler_name)
            state = response["Crawler"]["State"]
            if state == "READY":
                return state
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Glue crawler {self.config.glue_crawler_name} did not finish within {max_wait_seconds} seconds"
                )
            time.sleep(poll_seconds)

    def sync(self) -> dict[str, str]:
        self.ensure_database()
        self.ensure_crawler()
        state = self.start_crawler()
        final_state = self.wait_for_crawler()
        return {
            "database": self.config.glue_database,
            "crawler": self.config.glue_crawler_name,
            "target": self.normalized_s3_target,
            "state": state,
            "final_state": final_state,
        }


def sync_glue_catalog(config: RentPulseConfig | None = None) -> dict[str, str]:
    return GlueCatalogManager(config or RentPulseConfig.from_env()).sync()
