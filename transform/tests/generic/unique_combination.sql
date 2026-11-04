{#- Fails when the combination of the given columns is not unique. -#}
{% test unique_combination(model, columns) %}
select
    {{ columns | join(', ') }},
    count(*) as n_rows
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
