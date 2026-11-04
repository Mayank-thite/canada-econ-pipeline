-- Canada unemployment rate, 15 years and over, seasonally adjusted. Table 14-10-0287-01.
select
    ref_period as month,
    value::numeric(5, 1) as unemployment_rate_pct,
    release_time,
    loaded_at
from {{ source('statcan', 'unemployment_observations') }}
where vector_id = {{ var('unemployment_vector_id') }}
