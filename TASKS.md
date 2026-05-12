# RentPulse Build Tasks

## Project Control
- [x] Confirm the requested technology stack is represented without introducing a competing platform.
- [x] Create a reproducible project layout for ingestion, lake, warehouse, orchestration, dashboard, and CI/CD.
- [x] Document implementation notes where public data availability creates a necessary adapter boundary.

## Source And Ingestion Layer
- [x] Define configurable public source metadata for rental pricing, inventory, housing units, permits, transit access, and listing snapshots.
- [x] Implement Python download jobs for CSV, JSON, and local sample feeds.
- [x] Normalize source rows into JSONL records with lineage, hashes, run IDs, and timestamps.
- [x] Land original source files and normalized records in Amazon S3 prefixes.
- [x] Stage normalized records in Postgres for operational checks and replay.

## Data Lake Layer
- [x] Add AWS Glue crawler/catalog automation for raw and normalized S3 objects.
- [x] Add Athena external table and validation queries for record counts, freshness, and required datasets.

## Warehouse Layer
- [x] Add Snowflake schemas, file formats, external stage, raw table, and copy logic.
- [x] Add dbt Cloud-compatible models for listings, neighborhoods, permits, transit access, historical rent movement, inventory, churn, affordability, and development activity.
- [x] Add dbt tests for uniqueness, freshness-style checks, and referential integrity.

## Orchestration And Quality
- [x] Add an Airflow DAG that runs ingestion, Glue cataloging, Athena checks, Snowflake loading, dbt Cloud execution, and QuickSight refresh.
- [x] Add Python and SQL quality checks that fail loudly when required cloud settings are missing.

## User-Facing Output
- [x] Add QuickSight dataset/dashboard automation based on Snowflake marts.
- [x] Add a dashboard manifest mapping public-facing visuals to the dbt marts.

## Git And CI/CD
- [x] Add GitHub Actions CI/CD for Python tests, syntax checks, SQL/dbt asset checks, and DAG import sanity.
- [x] Add setup and operations documentation so the stack can be deployed with the listed technologies.
