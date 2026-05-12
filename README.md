# RentPulse

RentPulse is a public housing intelligence platform for tracking rental pricing, inventory, amenities, permits, transit access, and neighborhood signals over time. It uses the requested stack only: Python, Amazon S3, AWS Glue, Amazon Athena, Snowflake, dbt Cloud, Airflow, AWS QuickSight, Postgres, and Git/CI/CD.

## What This Builds

- Python ingestion jobs collect public housing, permit, rental price, inventory, transit, and listing snapshot feeds.
- Original files and normalized JSONL records land in Amazon S3.
- AWS Glue catalogs the S3 data lake so Athena can run validation and exploration queries.
- Postgres stores staging copies for operational replay and source-level checks.
- Snowflake loads normalized raw records from S3.
- dbt Cloud builds staging models, incremental history, dimensions, facts, and analytics marts.
- Airflow orchestrates ingestion, Glue, Athena, Snowflake, dbt Cloud, and QuickSight in dependency order.
- QuickSight publishes recruiter-friendly marts for neighborhood scorecards, rent trends, affordability, development, and transit analysis.
- GitHub Actions runs CI/CD validation for tests, syntax, source metadata, and dry-run ingestion.

## Source Feeds

The default source manifest is [config/sources.json](config/sources.json). It includes:

- Zillow Research ZIP ZORI rent price history.
- Zillow Research ZIP housing inventory signal.
- NYC Open Data Housing New York Units by Building.
- NYC Open Data DOB NOW approved permits.
- State of New York MTA Subway Stations and Complexes.
- A local listing snapshot seed with rent, amenities, status, and location fields.

The listing source is intentionally configurable through `RENT_PULSE_LISTINGS_URL`. Public unit-level rental listing feeds with amenities are not consistently exposed by city portals, so production should point this variable at an approved public or partner CSV/JSON feed with the same columns as [data/sample/listing_snapshots.csv](data/sample/listing_snapshots.csv).

## Local Setup

```bash
cd /Users/rishi/Desktop/proj/RentPulse
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Dry-run the included listing feed:

```bash
python -m rent_pulse ingest --source listing_snapshots --dry-run
```

List configured feeds:

```bash
python -m rent_pulse sources
```

## Cloud Run Order

After filling `.env` with AWS, Postgres, Snowflake, dbt Cloud, and QuickSight values:

```bash
python -m rent_pulse bootstrap-postgres
python -m rent_pulse ingest
python -m rent_pulse glue-sync
python -m rent_pulse athena-validate
python -m rent_pulse snowflake-bootstrap
python -m rent_pulse snowflake-load
python -m rent_pulse dbt-cloud-run
python -m rent_pulse quicksight-publish
python -m rent_pulse quicksight-refresh
```

## Airflow

Install Airflow dependencies separately because Airflow is large:

```bash
pip install -r requirements-airflow.txt
export AIRFLOW_HOME=/Users/rishi/Desktop/proj/RentPulse/airflow
airflow db migrate
airflow dags list
```

The DAG is [airflow/dags/rentpulse_daily_pipeline.py](airflow/dags/rentpulse_daily_pipeline.py). It runs daily and executes:

1. Python ingestion to S3 and Postgres.
2. AWS Glue crawler/catalog sync.
3. Athena table setup and validations.
4. Snowflake bootstrap and raw copy.
5. dbt Cloud job trigger.
6. QuickSight asset publish and SPICE refresh.

## dbt Cloud

Create a dbt Cloud project pointing at [dbt](dbt), connect it to Snowflake, and set these environment variables in dbt Cloud:

- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_USER`
- `SNOWFLAKE_PASSWORD`
- `SNOWFLAKE_ROLE`
- `SNOWFLAKE_WAREHOUSE`
- `SNOWFLAKE_DATABASE`

Configure the dbt Cloud job to run:

```bash
dbt source freshness
dbt build
```

## QuickSight

[quicksight/dashboard_manifest.json](quicksight/dashboard_manifest.json) defines Snowflake-backed datasets for:

- Neighborhood scorecard.
- Rent trends and volatility.
- Affordability.
- Development activity.
- Transit price effect.

Use `python -m rent_pulse quicksight-publish` to create/update datasets, then build or adjust the QuickSight dashboard visually using those datasets. Use `RENTPULSE_QUICKSIGHT_SHARE_PRINCIPAL_ARN` when you are ready to grant dashboard access.

## Verification

```bash
python -m unittest discover -s tests
python -m compileall rent_pulse scripts airflow/dags
python -m rent_pulse ingest --source listing_snapshots --dry-run
```

## Public Data Notes

Zillow notes that its CSV paths can change and its data is updated monthly. Keep [config/sources.json](config/sources.json) under version control and update the URLs if Zillow changes a download path. NYC and New York State Socrata endpoints are public and support CSV/JSON reads without an app token for normal development volumes.
