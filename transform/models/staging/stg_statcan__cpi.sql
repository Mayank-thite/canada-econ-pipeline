-- Canada all-items CPI (2002 = 100), not seasonally adjusted. Table 18-10-0004-01.
select
    ref_period as month,
    value::numeric(10, 1) as cpi_index,
    release_time,
    loaded_at
from {{ source('statcan', 'statcan_observations') }}
where vector_id = {{ var('cpi_vector_id') }}
