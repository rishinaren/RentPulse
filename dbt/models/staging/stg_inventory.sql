with source as (
    select *
    from {{ source('raw', 'raw_records') }}
    where dataset_name = 'zillow_inventory_zip'
),

unpivoted as (
    select
        payload:"RegionID"::string as region_id,
        payload:"SizeRank"::number as size_rank,
        payload:"RegionName"::string as postal_code,
        payload:"RegionType"::string as region_type,
        payload:"StateName"::string as state_name,
        try_to_date(months.key::string) as inventory_month,
        try_to_number(months.value::string) as active_inventory,
        source.ingested_at,
        source.run_id
    from source,
    lateral flatten(input => source.payload) months
    where regexp_like(months.key::string, '^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
)

select
    md5(region_id || '|' || inventory_month::string) as inventory_id,
    region_id,
    size_rank,
    postal_code,
    region_type,
    state_name,
    inventory_month,
    active_inventory,
    ingested_at,
    run_id
from unpivoted
where active_inventory is not null
