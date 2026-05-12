use database {{ snowflake_database }};
use schema raw;

create temporary table if not exists raw_records_load_buffer like raw_records;
truncate table raw_records_load_buffer;

copy into raw_records_load_buffer (
    dataset_name,
    dataset_type,
    source_url,
    source_row_id,
    record_hash,
    extracted_at,
    ingested_at,
    run_id,
    original_s3_key,
    payload
)
from (
    select
        $1:dataset_name::string,
        $1:dataset_type::string,
        $1:source_url::string,
        $1:source_row_id::string,
        $1:record_hash::string,
        try_to_timestamp_tz($1:extracted_at::string),
        try_to_timestamp_tz($1:ingested_at::string),
        $1:run_id::string,
        $1:original_s3_key::string,
        $1:payload
    from @{{ snowflake_s3_stage_name }}
)
file_format = (format_name = jsonl_format)
pattern = '.*records[.]jsonl'
on_error = 'CONTINUE';

merge into raw_records as target
using raw_records_load_buffer as source
    on target.dataset_name = source.dataset_name
   and target.source_row_id = source.source_row_id
   and target.record_hash = source.record_hash
when not matched then insert (
    dataset_name,
    dataset_type,
    source_url,
    source_row_id,
    record_hash,
    extracted_at,
    ingested_at,
    run_id,
    original_s3_key,
    payload
) values (
    source.dataset_name,
    source.dataset_type,
    source.source_url,
    source.source_row_id,
    source.record_hash,
    source.extracted_at,
    source.ingested_at,
    source.run_id,
    source.original_s3_key,
    source.payload
);

insert into load_audit (stage_name, rows_loaded, status)
select '{{ snowflake_s3_stage_name }}', count(*), 'loaded'
from raw_records_load_buffer;
