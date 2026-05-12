with neighborhoods as (
    select * from {{ ref('dim_neighborhoods') }}
),

latest_rent as (
    select *
    from {{ ref('fct_rent_trends') }}
    qualify row_number() over (partition by postal_code order by signal_month desc) = 1
),

listing_churn as (
    select *
    from {{ ref('mart_inventory_churn') }}
    qualify row_number() over (partition by postal_code order by snapshot_date desc) = 1
),

development as (
    select * from {{ ref('mart_development_activity') }}
)

select
    md5(neighborhoods.neighborhood_id || '|' || coalesce(latest_rent.signal_month::string, 'no-rent')) as neighborhood_scorecard_id,
    neighborhoods.neighborhood_id,
    neighborhoods.postal_code,
    neighborhoods.neighborhood,
    neighborhoods.borough,
    latest_rent.signal_month as latest_rent_month,
    latest_rent.zori_rent,
    latest_rent.rent_yoy_pct,
    latest_rent.six_month_rent_volatility,
    latest_rent.rent_volatility_band,
    latest_rent.active_inventory,
    listing_churn.listing_count,
    listing_churn.active_listing_count,
    listing_churn.leased_listing_count,
    listing_churn.avg_days_on_market,
    neighborhoods.housing_projects,
    neighborhoods.affordable_rental_units,
    neighborhoods.permit_count,
    development.estimated_development_cost,
    development.development_activity_band,
    case
        when latest_rent.rent_volatility_band = 'high volatility' then 3
        when latest_rent.rent_volatility_band = 'moderate volatility' then 2
        else 1
    end
    + case
        when coalesce(development.permit_count, neighborhoods.permit_count, 0) >= 50 then 2
        when coalesce(development.permit_count, neighborhoods.permit_count, 0) >= 10 then 1
        else 0
    end as recruiter_demo_signal_score
from neighborhoods
left join latest_rent
    on neighborhoods.postal_code = latest_rent.postal_code
left join listing_churn
    on neighborhoods.postal_code = listing_churn.postal_code
left join development
    on neighborhoods.postal_code = development.postal_code
