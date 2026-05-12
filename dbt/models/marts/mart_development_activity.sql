select
    development_signal_id as development_activity_id,
    borough,
    postal_code,
    neighborhood_code,
    housing_projects,
    affordable_rental_units,
    total_housing_units,
    permit_count,
    estimated_development_cost,
    latest_permit_issued_date,
    case
        when permit_count >= 100 or estimated_development_cost >= 100000000 then 'high development'
        when permit_count >= 25 or estimated_development_cost >= 25000000 then 'moderate development'
        else 'low development'
    end as development_activity_band
from {{ ref('int_neighborhood_development_signals') }}
