select
    borough,
    count(distinct station_complex_id) as station_complex_count,
    sum(coalesce(station_count, 1)) as station_count,
    sum(case when ada_score > 0 then 1 else 0 end) as ada_station_complex_count,
    count_if(in_cbd) as cbd_station_complex_count
from {{ ref('stg_transit_access') }}
group by 1
