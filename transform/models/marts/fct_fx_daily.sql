-- Daily FX with rolling averages and 30 day annualized volatility.
-- Windows count business days (rows), not calendar days.
-- Rolling values stay null until the window is full.
with base as (
    select
        currency_code,
        rate_date,
        cad_per_unit,
        log_return,
        count(*) over w7 as n7,
        avg(cad_per_unit) over w7 as avg7,
        count(*) over w30 as n30,
        avg(cad_per_unit) over w30 as avg30,
        count(log_return) over w30 as n_ret30,
        stddev_samp(log_return) over w30 as sd30
    from {{ ref('int_fx_daily_returns') }}
    window
        w7 as (partition by currency_code order by rate_date rows between 6 preceding and current row),
        w30 as (partition by currency_code order by rate_date rows between 29 preceding and current row)
)

select
    currency_code,
    rate_date,
    cad_per_unit,
    round((log_return * 100)::numeric, 4) as daily_change_pct,
    case when n7 = 7 then round(avg7, 6) end as rolling_avg_7d,
    case when n30 = 30 then round(avg30, 6) end as rolling_avg_30d,
    case when n_ret30 = 30 then round((sd30 * sqrt(252) * 100)::numeric, 3) end as volatility_30d_annualized_pct
from base
