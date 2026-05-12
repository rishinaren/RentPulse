with source as (
    select *
    from {{ source('raw', 'raw_records') }}
    where dataset_name = 'nyc_housing_units_by_building'
)

select
    md5(coalesce(payload:"project_id"::string, '') || '|' || coalesce(payload:"building_id"::string, '')) as housing_building_id,
    payload:"project_id"::string as project_id,
    payload:"project_name"::string as project_name,
    try_to_date(payload:"project_start_date"::string) as project_start_date,
    try_to_date(payload:"project_completion_date"::string) as project_completion_date,
    payload:"building_id"::string as building_id,
    payload:"house_number"::string as house_number,
    payload:"street_name"::string as street_name,
    payload:"borough"::string as borough,
    payload:"postcode"::string as postal_code,
    payload:"bbl"::string as bbl,
    payload:"bin"::string as bin,
    payload:"community_board"::string as community_board,
    payload:"neighborhood_tabulation_area"::string as neighborhood_code,
    try_to_decimal(payload:"latitude"::string, 12, 8) as latitude,
    try_to_decimal(payload:"longitude"::string, 12, 8) as longitude,
    payload:"reporting_construction_type"::string as construction_type,
    payload:"extended_affordability_status"::string as extended_affordability_status,
    try_to_number(payload:"counted_rental_units"::string) as counted_rental_units,
    try_to_number(payload:"all_counted_units"::string) as all_counted_units,
    try_to_number(payload:"total_units"::string) as total_units,
    ingested_at,
    run_id
from source
where payload:"project_id" is not null
