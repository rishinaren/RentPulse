with housing as (
    select
        borough,
        postal_code,
        neighborhood_code,
        count(distinct housing_building_id) as housing_projects,
        sum(coalesce(counted_rental_units, 0)) as affordable_rental_units,
        sum(coalesce(total_units, 0)) as total_housing_units
    from {{ ref('stg_neighborhood_housing') }}
    group by 1, 2, 3
),

permits as (
    select
        borough,
        postal_code,
        neighborhood_code,
        count(distinct permit_id) as permit_count,
        sum(coalesce(estimated_job_cost, 0)) as estimated_development_cost,
        max(issued_date) as latest_permit_issued_date
    from {{ ref('stg_permits') }}
    group by 1, 2, 3
)

select
    md5(coalesce(housing.postal_code, permits.postal_code, '') || '|' || coalesce(housing.neighborhood_code, permits.neighborhood_code, '')) as development_signal_id,
    coalesce(housing.borough, permits.borough) as borough,
    coalesce(housing.postal_code, permits.postal_code) as postal_code,
    coalesce(housing.neighborhood_code, permits.neighborhood_code) as neighborhood_code,
    coalesce(housing.housing_projects, 0) as housing_projects,
    coalesce(housing.affordable_rental_units, 0) as affordable_rental_units,
    coalesce(housing.total_housing_units, 0) as total_housing_units,
    coalesce(permits.permit_count, 0) as permit_count,
    coalesce(permits.estimated_development_cost, 0) as estimated_development_cost,
    permits.latest_permit_issued_date
from housing
full outer join permits
    on housing.postal_code = permits.postal_code
   and coalesce(housing.neighborhood_code, '') = coalesce(permits.neighborhood_code, '')
