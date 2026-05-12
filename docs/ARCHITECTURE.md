# RentPulse Architecture

## Source Layer

Python jobs in `rent_pulse.ingestion` read source metadata from `config/sources.json`, fetch CSV/JSON data, preserve original files, and normalize rows into JSONL records with source name, dataset type, row IDs, record hashes, run IDs, and timestamps.

## Data Lake Layer

Amazon S3 stores two prefixes:

- `raw/dataset_name=<name>/ingest_date=<date>/run_id=<run>/source.<format>`
- `normalized/dataset_name=<name>/ingest_date=<date>/run_id=<run>/records.jsonl`

AWS Glue crawls the normalized prefix. Athena uses `athena/create_raw_records_table.sql` and `athena/validation_queries.sql` for exploration and quality checks.

## Warehouse Layer

Snowflake DDL in `snowflake/ddl` creates raw, staging, intermediate, and analytics schemas. `snowflake/copy_raw_records.sql` copies JSONL records into a load buffer and merges new records into `raw.raw_records`.

## Transformation Layer

dbt Cloud builds:

- Staging models over raw JSON payloads.
- Intermediate ZIP/month market and development signals.
- Dimensions for listings and neighborhoods.
- Incremental facts for listing history and rent trends.
- Analytics marts for scorecards, affordability, inventory churn, development, and transit impact.

## Orchestration And Output

Airflow DAG `rentpulse_daily_pipeline` runs the full sequence from ingestion through QuickSight refresh. QuickSight datasets are defined in `quicksight/dashboard_manifest.json` and point to Snowflake analytics marts.
