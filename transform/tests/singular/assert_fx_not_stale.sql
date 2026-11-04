{{ config(severity='warn') }}
-- Warns when one currency stops updating while others keep going.
with last_dates as (
    select
        currency_code,
        last_rate_date,
        max(last_rate_date) over () as overall_last_date
    from {{ ref('dim_currency') }}
)

select
    currency_code,
    last_rate_date
from last_dates
where last_rate_date < overall_last_date - interval '3 days'
