-- Monthly CPI with month over month and year over year inflation.
-- I join on the month a year earlier instead of using lag(12), so a missing month cannot shift the math.
select
    cur.month,
    cur.cpi_index,
    round((cur.cpi_index / prev_m.cpi_index - 1) * 100, 2) as inflation_mom_pct,
    round((cur.cpi_index / prev_y.cpi_index - 1) * 100, 2) as inflation_yoy_pct,
    cur.release_time
from {{ ref('stg_statcan__cpi') }} as cur
left join {{ ref('stg_statcan__cpi') }} as prev_m
    on prev_m.month = (cur.month - interval '1 month')::date
left join {{ ref('stg_statcan__cpi') }} as prev_y
    on prev_y.month = (cur.month - interval '12 months')::date
