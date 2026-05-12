from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


def ingest_public_sources() -> list[dict]:
    from rent_pulse.ingestion.jobs import run_ingestion

    return [result.__dict__ for result in run_ingestion()]


def create_athena_table() -> list[dict]:
    from rent_pulse.aws.athena import run_athena_validations

    return run_athena_validations("athena/create_raw_records_table.sql")


def sync_glue() -> dict:
    from rent_pulse.aws.glue_catalog import sync_glue_catalog

    return sync_glue_catalog()


def validate_athena() -> list[dict]:
    from rent_pulse.aws.athena import run_athena_validations

    return run_athena_validations()


def bootstrap_snowflake() -> None:
    from rent_pulse.config import RentPulseConfig
    from rent_pulse.warehouse.snowflake import SnowflakeRunner

    SnowflakeRunner(RentPulseConfig.from_env()).bootstrap()


def load_snowflake_raw() -> None:
    from rent_pulse.config import RentPulseConfig
    from rent_pulse.warehouse.snowflake import SnowflakeRunner

    SnowflakeRunner(RentPulseConfig.from_env()).copy_raw_records()


def run_dbt_cloud() -> dict:
    from rent_pulse.warehouse.dbt_cloud import trigger_dbt_cloud_job

    return trigger_dbt_cloud_job()


def publish_quicksight() -> list[dict]:
    from rent_pulse.aws.quicksight import publish_quicksight_assets, refresh_quicksight_datasets

    results = publish_quicksight_assets()
    results.extend(refresh_quicksight_datasets())
    return results


default_args = {
    "owner": "rentpulse",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}


with DAG(
    dag_id="rentpulse_daily_pipeline",
    description="RentPulse S3, Glue, Athena, Snowflake, dbt Cloud, and QuickSight pipeline",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["rentpulse", "housing", "s3", "glue", "athena", "snowflake", "dbt-cloud", "quicksight"],
) as dag:
    ingest = PythonOperator(
        task_id="ingest_public_housing_sources_to_s3_and_postgres",
        python_callable=ingest_public_sources,
    )

    glue_catalog = PythonOperator(
        task_id="sync_aws_glue_catalog",
        python_callable=sync_glue,
    )

    athena_table = PythonOperator(
        task_id="create_athena_raw_records_table",
        python_callable=create_athena_table,
    )

    athena_quality = PythonOperator(
        task_id="run_athena_validation_queries",
        python_callable=validate_athena,
    )

    snowflake_bootstrap = PythonOperator(
        task_id="bootstrap_snowflake_objects",
        python_callable=bootstrap_snowflake,
    )

    snowflake_load = PythonOperator(
        task_id="copy_s3_jsonl_to_snowflake_raw",
        python_callable=load_snowflake_raw,
    )

    dbt_cloud = PythonOperator(
        task_id="trigger_dbt_cloud_transformations",
        python_callable=run_dbt_cloud,
    )

    quicksight = PythonOperator(
        task_id="publish_and_refresh_quicksight_dashboard",
        python_callable=publish_quicksight,
    )

    ingest >> glue_catalog >> athena_table >> athena_quality >> snowflake_bootstrap >> snowflake_load >> dbt_cloud >> quicksight
