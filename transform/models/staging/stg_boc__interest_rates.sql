-- Policy rate (target for the overnight rate) and CORRA, in percent.
select
    series_id as boc_series_id,
    case series_id
        when 'V39079' then 'policy_rate'
        when 'AVG.INTWO' then 'corra'
    end as rate_name,
    obs_date as rate_date,
    value::numeric(8, 4) as rate_pct,
    loaded_at
from {{ source('boc', 'boc_observations') }}
where series_id in ('V39079', 'AVG.INTWO')
