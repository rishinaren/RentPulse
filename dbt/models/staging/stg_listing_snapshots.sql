with source as (
    select *
    from {{ source('raw', 'raw_records') }}
    where dataset_name = 'listing_snapshots'
)

select
    md5(source_row_id || '|' || coalesce(record_hash, '')) as listing_snapshot_id,
    payload:"listing_id"::string as listing_id,
    try_to_date(payload:"snapshot_date"::string) as snapshot_date,
    payload:"address"::string as address,
    payload:"postal_code"::string as postal_code,
    payload:"neighborhood"::string as neighborhood,
    payload:"borough"::string as borough,
    try_to_decimal(payload:"rent"::string, 12, 2) as rent,
    try_to_number(payload:"bedrooms"::string) as bedrooms,
    try_to_decimal(payload:"bathrooms"::string, 8, 2) as bathrooms,
    try_to_number(payload:"sqft"::string) as sqft,
    payload:"property_type"::string as property_type,
    split(coalesce(payload:"amenities"::string, ''), '|') as amenities,
    payload:"status"::string as listing_status,
    try_to_date(payload:"listed_date"::string) as listed_date,
    try_to_decimal(payload:"latitude"::string, 12, 8) as latitude,
    try_to_decimal(payload:"longitude"::string, 12, 8) as longitude,
    ingested_at,
    run_id
from source
where payload:"listing_id" is not null
