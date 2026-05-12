select
    md5(postal_code || '|' || signal_month::string) as affordability_id,
    postal_code,
    signal_month,
    zori_rent,
    zori_rent * 12 as annual_rent,
    (zori_rent * 12) / 0.30 as income_needed_at_30_pct,
    rent_yoy_pct,
    rent_volatility_band
from {{ ref('fct_rent_trends') }}
where zori_rent is not null
