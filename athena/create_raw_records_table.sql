create external table if not exists ${glue_database}.${raw_table} (
    dataset_name string,
    dataset_type string,
    source_url string,
    source_row_id string,
    record_hash string,
    extracted_at string,
    ingested_at string,
    run_id string,
    original_s3_key string,
    payload map<string,string>
)
row format serde 'org.openx.data.jsonserde.JsonSerDe'
stored as textfile
location 's3://${s3_bucket}/${s3_prefix}/normalized/';

msck repair table ${glue_database}.${raw_table};
