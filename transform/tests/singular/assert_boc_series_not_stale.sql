{{ config(severity='warn') }}
-- Warns when one Bank of Canada series stops updating while the others keep going.
-- Source freshness only looks at the newest row in the whole table, so it would not catch this.
-- CORRA is published the next morning, so a 1 day lag is normal. 3 days is a real problem.
with last_dates as (
    select
        series_id,
        max(obs_date) as last_obs_date
    from {{ source('boc', 'boc_observations') }}
    group by series_id
),

overall as (
    select max(last_obs_date) as newest_obs_date
    from last_dates
)

select
    last_dates.series_id,
    last_dates.last_obs_date
from last_dates
cross join overall
where last_dates.last_obs_date < overall.newest_obs_date - interval '3 days'
