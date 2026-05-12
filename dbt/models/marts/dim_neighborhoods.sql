with listing_neighborhoods as (
    select distinct
        postal_code,
        neighborhood,
        borough
    from {{ ref('stg_listing_snapshots') }}
    where postal_code is not null
),

development as (
    select
        postal_code,
        any_value(neighborhood_code) as neighborhood_code,
        any_value(borough) as borough,
        sum(housing_projects) as housing_projects,
        sum(affordable_rental_units) as affordable_rental_units,
        sum(permit_count) as permit_count
    from {{ ref('int_neighborhood_development_signals') }}
    group by 1
)

select
    md5(coalesce(listing_neighborhoods.postal_code, development.postal_code, '') || '|' || coalesce(listing_neighborhoods.neighborhood, development.neighborhood_code, 'unknown')) as neighborhood_id,
    coalesce(listing_neighborhoods.postal_code, development.postal_code) as postal_code,
    coalesce(listing_neighborhoods.neighborhood, development.neighborhood_code, 'Unknown') as neighborhood,
    coalesce(listing_neighborhoods.borough, development.borough) as borough,
    development.neighborhood_code,
    coalesce(development.housing_projects, 0) as housing_projects,
    coalesce(development.affordable_rental_units, 0) as affordable_rental_units,
    coalesce(development.permit_count, 0) as permit_count
from listing_neighborhoods
full outer join development
    on listing_neighborhoods.postal_code = development.postal_code
