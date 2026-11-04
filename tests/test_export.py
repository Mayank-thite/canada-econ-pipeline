"""The dashboard payload is built from mart frames. Tested with small hand-made frames."""

from datetime import date

import pandas as pd

from scripts.export_marts import build_dashboard_payload, summarize_policy_changes


def changes_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "effective_date": [date(2025, 10, 30), date(2026, 10, 29), date(2026, 11, 4)],
            "change_bps": [-25, 25, 25],
            "usdcad_change_pct": [0.42, 0.30, None],
            "abs_move_percentile": [51.0, 40.0, None],
            "median_abs_move_all_days_pct": [0.41, 0.41, 0.41],
            "cad_moved_textbook_direction": [True, False, None],
        }
    )


def test_policy_change_summary_skips_open_windows():
    s = summarize_policy_changes(changes_frame())
    assert s["n_changes"] == 2
    assert s["n_textbook_direction"] == 1
    assert s["median_abs_move_change_days_pct"] == 0.36
    assert s["median_abs_move_all_days_pct"] == 0.41
    assert s["median_percentile"] == 45.5
    assert s["first_date"] == "2025-10-30"


def test_payload_takes_latest_values():
    fx = pd.DataFrame(
        {
            "currency_code": ["USD", "USD", "EUR"],
            "rate_date": [date(2026, 1, 2), date(2026, 1, 5), date(2026, 1, 5)],
            "cad_per_unit": [1.40, 1.41, 1.55],
            "daily_change_pct": [None, 0.7, None],
            "rolling_avg_7d": [None, None, None],
            "rolling_avg_30d": [None, 1.405, None],
            "volatility_30d_annualized_pct": [None, 4.2, None],
        }
    )
    rates = pd.DataFrame(
        {"rate_date": [date(2026, 1, 2), date(2026, 1, 5)], "policy_rate_pct": [2.25, 2.5], "corra_pct": [2.2, None]}
    )
    macro = pd.DataFrame(
        {
            "month": [date(2025, 11, 1), date(2025, 12, 1)],
            "inflation_yoy_pct": [2.4, None],
            "unemployment_rate_pct": [6.5, 6.6],
            "policy_rate_eom_pct": [2.25, 2.25],
            "corra_avg_pct": [2.2, 2.21],
            "usdcad_avg": [1.39, 1.40],
            "real_policy_rate_pct": [-0.15, None],
        }
    )
    dim = pd.DataFrame({"currency_code": ["USD", "EUR"], "currency_name": ["US dollar", "Euro"]})
    p = build_dashboard_payload(fx, rates, macro, dim, changes_frame())
    assert p["kpis"]["usdcad"] == {"value": 1.41, "date": "2026-01-05"}
    assert p["kpis"]["policy_rate"] == {"value": 2.5, "date": "2026-01-05"}
    assert p["kpis"]["cpi_yoy"] == {"value": 2.4, "date": "2025-11-01"}
    assert p["kpis"]["unemployment"] == {"value": 6.6, "date": "2025-12-01"}
    assert len(p["usdcad_daily"]["rows"]) == 2
    assert p["macro_monthly"]["rows"][1][1] is None
    assert {r[0] for r in p["latest_fx"]} == {"USD", "EUR"}
    assert p["kpis"]["real_policy_rate"] == {
        "value": -0.15,
        "policy_rate": 2.25,
        "cpi_yoy": 2.4,
        "date": "2025-11-01",
    }
    assert len(p["policy_changes"]["rows"]) == 3
