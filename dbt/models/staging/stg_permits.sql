with source as (
    select *
    from {{ source('raw', 'raw_records') }}
    where dataset_name = 'nyc_dob_approved_permits'
)

select
    md5(coalesce(payload:"job_filing_number"::string, '') || '|' || coalesce(payload:"work_permit"::string, '') || '|' || coalesce(payload:"sequence_number"::string, '')) as permit_id,
    payload:"job_filing_number"::string as job_filing_number,
    payload:"work_permit"::string as work_permit,
    payload:"sequence_number"::string as sequence_number,
    payload:"filing_reason"::string as filing_reason,
    payload:"house_no"::string as house_number,
    payload:"street_name"::string as street_name,
    payload:"borough"::string as borough,
    payload:"zip_code"::string as postal_code,
    payload:"community_board"::string as community_board,
    payload:"census_tract"::string as census_tract,
    payload:"nta"::string as neighborhood_code,
    payload:"work_type"::string as work_type,
    try_to_date(payload:"approved_date"::string) as approved_date,
    try_to_date(payload:"issued_date"::string) as issued_date,
    try_to_date(payload:"expired_date"::string) as expired_date,
    payload:"job_description"::string as job_description,
    try_to_decimal(regexp_replace(payload:"estimated_job_costs"::string, '[^0-9.]', ''), 14, 2) as estimated_job_cost,
    payload:"permit_status"::string as permit_status,
    try_to_decimal(payload:"latitude"::string, 12, 8) as latitude,
    try_to_decimal(payload:"longitude"::string, 12, 8) as longitude,
    ingested_at,
    run_id
from source
where payload:"job_filing_number" is not null
