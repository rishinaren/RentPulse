{{ config(materialized='incremental', unique_key='zip_month_signal_id', incremental_strategy='merge') }}

select
    zip_month_signal_id,
    postal_code,
    state_name,
    signal_month,
    zori_rent,
    active_inventory,
    rent_mom_delta,
    rent_yoy_pct,
    inventory_mom_delta,
    six_month_rent_volatility,
    case
        when abs(coalesce(six_month_rent_volatility, 0)) >= 150 then 'high volatility'
        when abs(coalesce(six_month_rent_volatility, 0)) >= 75 then 'moderate volatility'
        else 'stable'
    end as rent_volatility_band
from {{ ref('int_zip_month_market_signals') }}
{% if is_incremental() %}
where signal_month >= (select coalesce(max(signal_month), '1900-01-01') from {{ this }})
{% endif %}
