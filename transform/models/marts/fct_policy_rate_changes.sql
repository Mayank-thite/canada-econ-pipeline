-- One row per change in the Bank of Canada policy rate, with how USD/CAD moved around it.
--
-- Series V39079 changes on the day the new rate takes effect. Since 2022 that is the day after the
-- 9:45 am announcement, and before that it was usually the same day. So I measure USD/CAD from two
-- business days before the effective date to one business day after. That window always starts before
-- the announcement and ends after a full day of trading on the new rate.
--
-- To judge whether a move is big, I compare it with the same 3 business day window on every day in
-- the data, and give each change its percentile among all those windows.
-- Holds are not in here: the series only shows changes, not decision dates.
with policy as (
    select
        rate_date,
        policy_rate_pct,
        lag(policy_rate_pct) over (order by rate_date) as previous_rate_pct
    from {{ ref('fct_rates_daily') }}
    where policy_rate_pct is not null
),

usd as (
    select
        rate_date,
        cad_per_unit,
        row_number() over (order by rate_date) as day_index
    from {{ ref('stg_boc__fx_rates') }}
    where currency_code = 'USD'
),

windows as (
    select
        mid.rate_date,
        before_day.rate_date as window_start,
        after_day.rate_date as window_end,
        before_day.cad_per_unit as usdcad_start,
        after_day.cad_per_unit as usdcad_end,
        ln(after_day.cad_per_unit / before_day.cad_per_unit) * 100 as usdcad_change_pct
    from usd as mid
    inner join usd as before_day on mid.day_index - 2 = before_day.day_index
    inner join usd as after_day on mid.day_index + 1 = after_day.day_index
),

all_days as (
    select percentile_cont(0.5) within group (order by abs(usdcad_change_pct)) as median_abs_move_all_days_pct
    from windows
),

ranked as (
    select
        windows.*,
        all_days.median_abs_move_all_days_pct,
        percent_rank() over (order by abs(windows.usdcad_change_pct)) as abs_move_percentile
    from windows
    cross join all_days
)

select
    policy.rate_date as effective_date,
    policy.previous_rate_pct,
    policy.policy_rate_pct as new_rate_pct,
    round((policy.policy_rate_pct - policy.previous_rate_pct) * 100)::int as change_bps,
    case when policy.policy_rate_pct > policy.previous_rate_pct then 'hike' else 'cut' end as direction,
    ranked.window_start,
    ranked.window_end,
    ranked.usdcad_start,
    ranked.usdcad_end,
    round(ranked.usdcad_change_pct::numeric, 3) as usdcad_change_pct,
    round((ranked.abs_move_percentile * 100)::numeric, 1) as abs_move_percentile,
    round(ranked.median_abs_move_all_days_pct::numeric, 3) as median_abs_move_all_days_pct,
    -- Textbook direction: a hike should make CAD stronger (USD/CAD down), a cut weaker (USD/CAD up).
    case
        when ranked.usdcad_change_pct is null then null
        when policy.policy_rate_pct > policy.previous_rate_pct then ranked.usdcad_change_pct < 0
        else ranked.usdcad_change_pct > 0
    end as cad_moved_textbook_direction
from policy
left join ranked on policy.rate_date = ranked.rate_date
where policy.policy_rate_pct <> policy.previous_rate_pct
