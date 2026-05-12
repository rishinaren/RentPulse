create schema if not exists rentpulse_staging;

create table if not exists rentpulse_staging.raw_records (
    id bigserial primary key,
    dataset_name text not null,
    dataset_type text not null,
    source_url text not null,
    source_row_id text not null,
    record_hash text not null,
    run_id text not null,
    original_s3_key text,
    extracted_at timestamptz not null,
    ingested_at timestamptz not null default now(),
    payload jsonb not null,
    created_at timestamptz not null default now(),
    unique (dataset_name, source_row_id, record_hash)
);

create index if not exists idx_rentpulse_raw_records_dataset
    on rentpulse_staging.raw_records (dataset_name, ingested_at desc);

create index if not exists idx_rentpulse_raw_records_payload_gin
    on rentpulse_staging.raw_records using gin (payload);

create table if not exists rentpulse_staging.ingestion_runs (
    run_id text primary key,
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    status text not null default 'running',
    notes text
);
