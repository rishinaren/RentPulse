with listing_history as (
    select * from {{ ref('fct_listing_history') }}
),

daily as (
    select
        postal_code,
        neighborhood,
        borough,
        snapshot_date,
        count(distinct listing_id) as listing_count,
        count_if(listing_status = 'active') as active_listing_count,
        count_if(listing_status = 'leased') as leased_listing_count,
        avg(rent) as avg_listing_rent,
        median(rent) as median_listing_rent,
        avg(days_on_market) as avg_days_on_market,
        count_if(rent_change_amount <> 0) as listings_with_price_changes
    from listing_history
    group by 1, 2, 3, 4
)

select
    md5(postal_code || '|' || snapshot_date::string) as inventory_churn_id,
    postal_code,
    neighborhood,
    borough,
    snapshot_date,
    listing_count,
    active_listing_count,
    leased_listing_count,
    avg_listing_rent,
    median_listing_rent,
    avg_days_on_market,
    listings_with_price_changes,
    listing_count - lag(listing_count) over (partition by postal_code order by snapshot_date) as listing_count_delta
from daily
