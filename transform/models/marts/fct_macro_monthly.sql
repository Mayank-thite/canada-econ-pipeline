-- One row per month: inflation, unemployment, rates and USD/CAD side by side.
-- The month spine runs from the first FX month up to the last complete month of FX data.
-- CPI and unemployment come out about 5 to 7 weeks after month end, so the latest months can be null.
with bounds as (
    select
        date_trunc('month', min(rate_date))::date as first_month,
        (date_trunc('month', max(rate_date)) - interval '1 month')::date as last_month
    from {{ ref('stg_boc__fx_rates') }}
),

spine as (
    select generate_series(first_month, last_month, interval '1 month')::date as month
    from bounds
),

usd as (
    select
        month,
        cad_per_unit_avg,
        cad_per_unit_eom
    from {{ ref('int_fx_monthly') }}
    where currency_code = 'USD'
)

select
    spine.month,
    cpi.cpi_index,
    cpi.inflation_yoy_pct,
    u.unemployment_rate_pct,
    r.policy_rate_eom_pct,
    r.corra_avg_pct,
    round(r.policy_rate_eom_pct - cpi.inflation_yoy_pct, 2) as real_policy_rate_pct,
    round(usd.cad_per_unit_avg, 4) as usdcad_avg,
    round(usd.cad_per_unit_eom, 4) as usdcad_eom
from spine
left join {{ ref('fct_cpi_monthly') }} as cpi on spine.month = cpi.month
left join {{ ref('stg_statcan__unemployment') }} as u on spine.month = u.month
left join {{ ref('int_rates_monthly') }} as r on spine.month = r.month
left join usd on spine.month = usd.month
