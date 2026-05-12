with listing_borough_rents as (
    select
        borough,
        snapshot_date,
        avg(rent) as avg_listing_rent,
        median(rent) as median_listing_rent,
        count(distinct listing_id) as listing_count
    from {{ ref('stg_listing_snapshots') }}
    group by 1, 2
),

transit as (
    select * from {{ ref('int_transit_access_by_borough') }}
)

select
    md5(listing_borough_rents.borough || '|' || listing_borough_rents.snapshot_date::string) as transit_price_effect_id,
    listing_borough_rents.borough,
    listing_borough_rents.snapshot_date,
    listing_borough_rents.avg_listing_rent,
    listing_borough_rents.median_listing_rent,
    listing_borough_rents.listing_count,
    transit.station_complex_count,
    transit.station_count,
    transit.ada_station_complex_count,
    transit.cbd_station_complex_count,
    listing_borough_rents.avg_listing_rent / nullif(transit.station_complex_count, 0) as rent_per_station_complex
from listing_borough_rents
left join transit
    on listing_borough_rents.borough = transit.borough
