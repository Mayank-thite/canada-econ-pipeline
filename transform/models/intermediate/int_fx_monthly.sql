-- Monthly average and month end FX rate per currency.
with ranked as (
    select
        currency_code,
        rate_date,
        cad_per_unit,
        date_trunc('month', rate_date)::date as month,
        row_number() over (
            partition by currency_code, date_trunc('month', rate_date)
            order by rate_date desc
        ) as rn_desc
    from {{ ref('stg_boc__fx_rates') }}
)

select
    currency_code,
    month,
    avg(cad_per_unit)::numeric(18, 6) as cad_per_unit_avg,
    max(case when rn_desc = 1 then cad_per_unit end) as cad_per_unit_eom,
    count(*) as trading_days
from ranked
group by currency_code, month
