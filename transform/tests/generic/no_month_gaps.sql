{#- Fails for every month missing between the first and last month in the column. -#}
{% test no_month_gaps(model, column_name) %}
with bounds as (
    select
        min({{ column_name }}) as first_month,
        max({{ column_name }}) as last_month
    from {{ model }}
),

expected as (
    select generate_series(first_month, last_month, interval '1 month')::date as month
    from bounds
)

select expected.month
from expected
left join {{ model }} as m on m.{{ column_name }} = expected.month
where m.{{ column_name }} is null
{% endtest %}
