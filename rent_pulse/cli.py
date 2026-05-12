from __future__ import annotations

import argparse
import json
import sys

from rent_pulse.aws.athena import run_athena_validations
from rent_pulse.aws.glue_catalog import sync_glue_catalog
from rent_pulse.aws.quicksight import publish_quicksight_assets, refresh_quicksight_datasets
from rent_pulse.config import RentPulseConfig, load_sources
from rent_pulse.ingestion.jobs import run_ingestion
from rent_pulse.storage.postgres import PostgresStager
from rent_pulse.warehouse.dbt_cloud import trigger_dbt_cloud_job
from rent_pulse.warehouse.snowflake import SnowflakeRunner


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, default=str))


def cmd_sources(_: argparse.Namespace) -> int:
    config = RentPulseConfig.from_env()
    _print_json([source.__dict__ | {"url": source.resolved_url()} for source in load_sources(config)])
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    results = run_ingestion(
        source_names=args.source,
        dry_run=args.dry_run,
        upload_to_s3=not args.no_s3,
        stage_postgres=not args.no_postgres,
    )
    _print_json([result.__dict__ for result in results])
    return 0


def cmd_bootstrap_postgres(_: argparse.Namespace) -> int:
    PostgresStager(RentPulseConfig.from_env()).ensure_schema()
    print("Postgres staging schema is ready.")
    return 0


def cmd_glue_sync(_: argparse.Namespace) -> int:
    _print_json(sync_glue_catalog())
    return 0


def cmd_athena_validate(_: argparse.Namespace) -> int:
    _print_json(run_athena_validations())
    return 0


def cmd_snowflake_bootstrap(_: argparse.Namespace) -> int:
    SnowflakeRunner(RentPulseConfig.from_env()).bootstrap()
    print("Snowflake schemas, stage, and raw table are ready.")
    return 0


def cmd_snowflake_load(_: argparse.Namespace) -> int:
    SnowflakeRunner(RentPulseConfig.from_env()).copy_raw_records()
    print("Snowflake raw records loaded from S3.")
    return 0


def cmd_dbt_cloud_run(_: argparse.Namespace) -> int:
    _print_json(trigger_dbt_cloud_job())
    return 0


def cmd_quicksight_refresh(_: argparse.Namespace) -> int:
    _print_json(refresh_quicksight_datasets())
    return 0


def cmd_quicksight_publish(args: argparse.Namespace) -> int:
    _print_json(publish_quicksight_assets(args.manifest))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RentPulse public housing intelligence platform")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sources_parser = subparsers.add_parser("sources", help="List configured source feeds")
    sources_parser.set_defaults(func=cmd_sources)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest configured source feeds")
    ingest_parser.add_argument("--source", action="append", help="Source name or dataset_type to ingest")
    ingest_parser.add_argument("--dry-run", action="store_true", help="Fetch and parse without S3/Postgres writes")
    ingest_parser.add_argument("--no-s3", action="store_true", help="Skip S3 landing")
    ingest_parser.add_argument("--no-postgres", action="store_true", help="Skip Postgres staging")
    ingest_parser.set_defaults(func=cmd_ingest)

    subparsers.add_parser("bootstrap-postgres", help="Create Postgres staging tables").set_defaults(
        func=cmd_bootstrap_postgres
    )
    subparsers.add_parser("glue-sync", help="Create/update Glue crawler and start cataloging").set_defaults(
        func=cmd_glue_sync
    )
    subparsers.add_parser("athena-validate", help="Run Athena validation SQL").set_defaults(
        func=cmd_athena_validate
    )
    subparsers.add_parser("snowflake-bootstrap", help="Create Snowflake objects").set_defaults(
        func=cmd_snowflake_bootstrap
    )
    subparsers.add_parser("snowflake-load", help="Copy normalized S3 records into Snowflake").set_defaults(
        func=cmd_snowflake_load
    )
    subparsers.add_parser("dbt-cloud-run", help="Trigger the dbt Cloud job").set_defaults(func=cmd_dbt_cloud_run)
    subparsers.add_parser("quicksight-refresh", help="Refresh configured QuickSight datasets").set_defaults(
        func=cmd_quicksight_refresh
    )
    publish_parser = subparsers.add_parser("quicksight-publish", help="Create/update QuickSight assets")
    publish_parser.add_argument("--manifest", default="quicksight/dashboard_manifest.json")
    publish_parser.set_defaults(func=cmd_quicksight_publish)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
