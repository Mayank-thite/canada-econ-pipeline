"""Export the marts to CSV and Parquet, and write the JSON the dashboard reads.

python -m scripts.export_marts
"""

import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

from ingest.config import database_url
from ingest.db import connect

ROOT = Path(__file__).resolve().parents[1]
MARTS_DIR = ROOT / "data" / "marts"
DASHBOARD_JSON = ROOT / "docs" / "data" / "dashboard.json"
MARTS = ["dim_currency", "fct_fx_daily", "fct_rates_daily", "fct_cpi_monthly", "fct_macro_monthly"]

log = logging.getLogger("export")


def _clean(value):
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return float(value) if not isinstance(value, str) else value


def records(df: pd.DataFrame, cols: list[str]) -> list[list]:
    """Compact row lists keep the dashboard JSON small."""
    return [[_clean(v) for v in row] for row in df[cols].itertuples(index=False, name=None)]


def build_dashboard_payload(fx: pd.DataFrame, rates: pd.DataFrame, macro: pd.DataFrame, dim: pd.DataFrame) -> dict:
    fx = fx.sort_values(["currency_code", "rate_date"])
    usd = fx[fx["currency_code"] == "USD"]
    latest_fx = fx.groupby("currency_code").tail(1).merge(dim[["currency_code", "currency_name"]], on="currency_code")
    macro = macro.sort_values("month")
    last_cpi = macro.dropna(subset=["inflation_yoy_pct"]).tail(1)
    last_unemp = macro.dropna(subset=["unemployment_rate_pct"]).tail(1)
    last_usd = usd.tail(1)
    last_policy = rates.dropna(subset=["policy_rate_pct"]).sort_values("rate_date").tail(1)
    return {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kpis": {
            "usdcad": {
                "value": _clean(last_usd["cad_per_unit"].iloc[0]),
                "date": _clean(last_usd["rate_date"].iloc[0]),
            },
            "usdcad_vol": {
                "value": _clean(last_usd["volatility_30d_annualized_pct"].iloc[0]),
                "date": _clean(last_usd["rate_date"].iloc[0]),
            },
            "policy_rate": {
                "value": _clean(last_policy["policy_rate_pct"].iloc[0]),
                "date": _clean(last_policy["rate_date"].iloc[0]),
            },
            "cpi_yoy": {
                "value": _clean(last_cpi["inflation_yoy_pct"].iloc[0]),
                "date": _clean(last_cpi["month"].iloc[0]),
            },
            "unemployment": {
                "value": _clean(last_unemp["unemployment_rate_pct"].iloc[0]),
                "date": _clean(last_unemp["month"].iloc[0]),
            },
        },
        "usdcad_daily": {
            "columns": ["date", "rate", "avg_30d", "vol_30d"],
            "rows": records(usd, ["rate_date", "cad_per_unit", "rolling_avg_30d", "volatility_30d_annualized_pct"]),
        },
        "macro_monthly": {
            "columns": ["month", "cpi_yoy", "unemployment", "policy_rate", "corra_avg", "usdcad_avg"],
            "rows": records(
                macro,
                [
                    "month",
                    "inflation_yoy_pct",
                    "unemployment_rate_pct",
                    "policy_rate_eom_pct",
                    "corra_avg_pct",
                    "usdcad_avg",
                ],
            ),
        },
        "latest_fx": records(
            latest_fx,
            [
                "currency_code",
                "currency_name",
                "rate_date",
                "cad_per_unit",
                "rolling_avg_30d",
                "volatility_30d_annualized_pct",
            ],
        ),
    }


def read_table(conn, table: str) -> pd.DataFrame:
    """Read a table with psycopg2. Postgres numeric comes back as Decimal, so I cast those to float."""
    with conn.cursor() as cur:
        cur.execute(f"select * from {table}")
        cols = [c.name for c in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=cols)
    for col in df.columns:
        sample = df[col].dropna()
        if not sample.empty and isinstance(sample.iloc[0], Decimal):
            df[col] = df[col].astype(float)
    return df


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    conn = connect(database_url())
    MARTS_DIR.mkdir(parents=True, exist_ok=True)
    frames = {}
    for name in MARTS:
        df = read_table(conn, f"marts.{name}")
        frames[name] = df
        df.to_csv(MARTS_DIR / f"{name}.csv", index=False)
        df.to_parquet(MARTS_DIR / f"{name}.parquet", index=False)
        log.info("Exported %s: %d rows", name, len(df))

    payload = build_dashboard_payload(
        frames["fct_fx_daily"], frames["fct_rates_daily"], frames["fct_macro_monthly"], frames["dim_currency"]
    )
    DASHBOARD_JSON.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_JSON.write_text(json.dumps(payload, separators=(",", ":")))
    conn.close()
    log.info("Wrote %s (%d bytes)", DASHBOARD_JSON.relative_to(ROOT), DASHBOARD_JSON.stat().st_size)


if __name__ == "__main__":
    main()
