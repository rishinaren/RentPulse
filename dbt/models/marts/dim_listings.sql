with ranked as (
    select
        *,
        row_number() over (partition by listing_id order by snapshot_date desc, ingested_at desc) as row_number
    from {{ ref('stg_listing_snapshots') }}
)

select
    listing_id,
    address,
    postal_code,
    neighborhood,
    borough,
    bedrooms,
    bathrooms,
    sqft,
    property_type,
    amenities,
    listed_date,
    latitude,
    longitude,
    listing_status as current_status,
    rent as current_rent,
    snapshot_date as latest_snapshot_date
from ranked
where row_number = 1
