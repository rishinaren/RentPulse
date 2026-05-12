with source as (
    select *
    from {{ source('raw', 'raw_records') }}
    where dataset_name = 'mta_subway_stations'
)

select
    payload:"Complex ID"::string as station_complex_id,
    lower(payload:"Is Complex"::string) = 'true' as is_complex,
    try_to_number(payload:"Number Of Stations In Complex"::string) as station_count,
    payload:"Stop Name"::string as stop_name,
    payload:"Display Name"::string as display_name,
    payload:"Borough"::string as borough_code,
    case payload:"Borough"::string
        when 'M' then 'Manhattan'
        when 'Q' then 'Queens'
        when 'Bk' then 'Brooklyn'
        when 'Bx' then 'Bronx'
        when 'SI' then 'Staten Island'
        else payload:"Borough"::string
    end as borough,
    lower(payload:"CBD"::string) = 'true' as in_cbd,
    payload:"Daytime Routes"::string as daytime_routes,
    payload:"Structure Type"::string as structure_type,
    try_to_decimal(payload:"Latitude"::string, 12, 8) as latitude,
    try_to_decimal(payload:"Longitude"::string, 12, 8) as longitude,
    try_to_number(payload:"ADA"::string) as ada_score,
    payload:"ADA Notes"::string as ada_notes,
    ingested_at,
    run_id
from source
where payload:"Complex ID" is not null
