-- Monthly view of the policy rate (value on the last business day) and CORRA (monthly average).
with ranked as (
    select
        rate_name,
        rate_date,
        rate_pct,
        date_trunc('month', rate_date)::date as month,
        row_number() over (
            partition by rate_name, date_trunc('month', rate_date)
            order by rate_date desc
        ) as rn_desc
    from {{ ref('stg_boc__interest_rates') }}
)

select
    month,
    max(case when rate_name = 'policy_rate' and rn_desc = 1 then rate_pct end) as policy_rate_eom_pct,
    avg(case when rate_name = 'corra' then rate_pct end)::numeric(8, 4) as corra_avg_pct
from ranked
group by month
