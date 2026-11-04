"""The dashboard payload is built from mart frames. Tested with small hand-made frames."""

from datetime import date

import pandas as pd

from scripts.export_marts import build_dashboard_payload


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
        }
    )
    dim = pd.DataFrame({"currency_code": ["USD", "EUR"], "currency_name": ["US dollar", "Euro"]})
    p = build_dashboard_payload(fx, rates, macro, dim)
    assert p["kpis"]["usdcad"] == {"value": 1.41, "date": "2026-01-05"}
    assert p["kpis"]["policy_rate"] == {"value": 2.5, "date": "2026-01-05"}
    assert p["kpis"]["cpi_yoy"] == {"value": 2.4, "date": "2025-11-01"}
    assert p["kpis"]["unemployment"] == {"value": 6.6, "date": "2025-12-01"}
    assert len(p["usdcad_daily"]["rows"]) == 2
    assert p["macro_monthly"]["rows"][1][1] is None
    assert {r[0] for r in p["latest_fx"]} == {"USD", "EUR"}
