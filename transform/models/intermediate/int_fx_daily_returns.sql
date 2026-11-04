-- Adds the previous business day rate and the daily log return for each currency.
with rates as (
    select
        currency_code,
        rate_date,
        cad_per_unit,
        lag(cad_per_unit) over (partition by currency_code order by rate_date) as prev_cad_per_unit
    from {{ ref('stg_boc__fx_rates') }}
)

select
    currency_code,
    rate_date,
    cad_per_unit,
    prev_cad_per_unit,
    case
        when prev_cad_per_unit is not null
            then ln(cad_per_unit / prev_cad_per_unit)
    end as log_return
from rates
