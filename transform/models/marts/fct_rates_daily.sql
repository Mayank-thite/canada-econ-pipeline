-- Daily policy rate and CORRA side by side. CORRA can be null on a day the policy rate has a value.
select
    rate_date,
    max(case when rate_name = 'policy_rate' then rate_pct end) as policy_rate_pct,
    max(case when rate_name = 'corra' then rate_pct end) as corra_pct
from {{ ref('stg_boc__interest_rates') }}
group by rate_date
