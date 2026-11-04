-- The Bank of Canada moves its policy rate in steps of 0.25 points.
-- A value off that grid usually means the series changed or I parsed the wrong field.
select
    rate_date,
    rate_pct
from {{ ref('stg_boc__interest_rates') }}
where
    rate_name = 'policy_rate'
    and mod(rate_pct * 100, 25) <> 0
