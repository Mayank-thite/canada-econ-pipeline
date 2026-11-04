-- Daily FX rates, CAD per one unit of foreign currency.
select
    series_id as boc_series_id,
    substr(series_id, 3, 3) as currency_code,
    obs_date as rate_date,
    value::numeric(18, 6) as cad_per_unit,
    loaded_at
from {{ source('boc', 'boc_observations') }}
where series_id like 'FX%'
