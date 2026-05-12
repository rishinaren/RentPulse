{{ config(materialized='incremental', unique_key='listing_snapshot_id', incremental_strategy='merge') }}

with history as (
    select
        listing_snapshot_id,
        listing_id,
        snapshot_date,
        postal_code,
        neighborhood,
        borough,
        rent,
        bedrooms,
        bathrooms,
        sqft,
        property_type,
        listing_status,
        datediff('day', listed_date, snapshot_date) as days_on_market,
        rent - lag(rent) over (partition by listing_id order by snapshot_date) as rent_change_amount,
        (rent / nullif(lag(rent) over (partition by listing_id order by snapshot_date), 0)) - 1 as rent_change_pct,
        ingested_at,
        run_id
    from {{ ref('stg_listing_snapshots') }}
    where listing_id is not null
)

select
    listing_snapshot_id,
    listing_id,
    snapshot_date,
    postal_code,
    neighborhood,
    borough,
    rent,
    bedrooms,
    bathrooms,
    sqft,
    property_type,
    listing_status,
    days_on_market,
    rent_change_amount,
    rent_change_pct,
    ingested_at,
    run_id
from history
{% if is_incremental() %}
where snapshot_date >= (select coalesce(max(snapshot_date), '1900-01-01') from {{ this }})
{% endif %}
