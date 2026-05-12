with rent as (
    select * from {{ ref('stg_rent_prices') }}
),

inventory as (
    select * from {{ ref('stg_inventory') }}
),

joined as (
    select
        coalesce(rent.postal_code, inventory.postal_code) as postal_code,
        coalesce(rent.state_name, inventory.state_name) as state_name,
        coalesce(rent.rent_month, inventory.inventory_month) as signal_month,
        rent.zori_rent,
        inventory.active_inventory
    from rent
    full outer join inventory
        on rent.postal_code = inventory.postal_code
       and rent.rent_month = inventory.inventory_month
)

select
    md5(postal_code || '|' || signal_month::string) as zip_month_signal_id,
    postal_code,
    state_name,
    signal_month,
    zori_rent,
    active_inventory,
    zori_rent - lag(zori_rent) over (partition by postal_code order by signal_month) as rent_mom_delta,
    (zori_rent / nullif(lag(zori_rent, 12) over (partition by postal_code order by signal_month), 0)) - 1 as rent_yoy_pct,
    active_inventory - lag(active_inventory) over (partition by postal_code order by signal_month) as inventory_mom_delta,
    stddev_samp(zori_rent) over (
        partition by postal_code
        order by signal_month
        rows between 5 preceding and current row
    ) as six_month_rent_volatility
from joined
where postal_code is not null
  and signal_month is not null
