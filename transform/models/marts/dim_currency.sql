-- One row per tracked currency, with the date range I have data for.
select
    c.currency_code,
    c.currency_name,
    c.boc_series_id,
    min(r.rate_date) as first_rate_date,
    max(r.rate_date) as last_rate_date,
    count(r.rate_date) as n_observations
from {{ ref('currencies') }} as c
left join {{ ref('stg_boc__fx_rates') }} as r on c.currency_code = r.currency_code
group by c.currency_code, c.currency_name, c.boc_series_id
