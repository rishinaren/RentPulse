use database {{ snowflake_database }};
use schema raw;

create file format if not exists jsonl_format
    type = json
    strip_outer_array = false
    compression = auto;

create stage if not exists {{ snowflake_s3_stage_name }}
    url = 's3://{{ s3_bucket }}/{{ s3_prefix }}/normalized/'
    storage_integration = {{ snowflake_storage_integration }}
    file_format = jsonl_format;

create table if not exists raw_records (
    dataset_name string not null,
    dataset_type string not null,
    source_url string not null,
    source_row_id string not null,
    record_hash string not null,
    extracted_at timestamp_tz,
    ingested_at timestamp_tz,
    run_id string not null,
    original_s3_key string,
    payload variant not null,
    loaded_at timestamp_tz not null default current_timestamp(),
    constraint raw_records_unique unique (dataset_name, source_row_id, record_hash)
);

create table if not exists load_audit (
    load_id string default uuid_string(),
    loaded_at timestamp_tz default current_timestamp(),
    stage_name string,
    rows_loaded number,
    status string
);
