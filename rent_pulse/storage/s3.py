from __future__ import annotations

from rent_pulse.config import RentPulseConfig


class S3Landing:
    def __init__(self, config: RentPulseConfig):
        config.require("s3_bucket")
        self.config = config
        import boto3

        self.client = boto3.client("s3", region_name=config.aws_region)

    def _key(self, suffix: str) -> str:
        prefix = self.config.s3_prefix.strip("/")
        clean_suffix = suffix.strip("/")
        return f"{prefix}/{clean_suffix}" if prefix else clean_suffix

    def raw_key(self, source_name: str, extension: str, ingest_date: str, run_id: str) -> str:
        return self._key(
            f"raw/dataset_name={source_name}/ingest_date={ingest_date}/run_id={run_id}/source.{extension}"
        )

    def normalized_key(self, source_name: str, ingest_date: str, run_id: str) -> str:
        return self._key(
            f"normalized/dataset_name={source_name}/ingest_date={ingest_date}/run_id={run_id}/records.jsonl"
        )

    def put_bytes(self, key: str, content: bytes, content_type: str = "application/octet-stream") -> None:
        self.client.put_object(
            Bucket=self.config.s3_bucket,
            Key=key,
            Body=content,
            ContentType=content_type or "application/octet-stream",
        )

    def put_text(self, key: str, content: str, content_type: str = "text/plain") -> None:
        self.put_bytes(key, content.encode("utf-8"), content_type)
