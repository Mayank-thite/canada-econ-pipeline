# Connecting Power BI to the marts

The marts live in Postgres in the `marts` schema. Power BI Desktop can read them directly.
I use Import mode because the tables are small (about 15,000 rows in total) and it keeps the report fast.

## 1. Get the database running

Run the pipeline once so the tables exist:

```bash
make all
```

That leaves Postgres running on `localhost:5432`, database `econ`, user `econ`, password `econ`
(the values from `.env.example`).

## 2. Connect

1. Open Power BI Desktop and pick **Get data > Database > PostgreSQL database**.
2. Server: `localhost:5432`. Database: `econ`. Data connectivity mode: **Import**.
3. When it asks for credentials, pick **Database** and enter `econ` / `econ`.
4. If you get an encryption error, untick "Encrypt connections" for this local source.
   The Docker database does not have SSL set up.
5. In the Navigator, tick these tables:
   - `marts.dim_currency`
   - `marts.fct_fx_daily`
   - `marts.fct_rates_daily`
   - `marts.fct_cpi_monthly`
   - `marts.fct_macro_monthly`
   - `marts.fct_policy_rate_changes`
6. Click **Load**.

Recent versions of Power BI Desktop ship with the Npgsql driver. If yours says the provider is
missing, install Npgsql from its GitHub releases page and restart Power BI.

## 3. Model

- Create the `Date` table from `measures.dax` (Modeling > New table) and mark it as a date table.
- Relationships:
  - `dim_currency[currency_code]` 1 to many `fct_fx_daily[currency_code]`
  - `Date[Date]` 1 to many `fct_fx_daily[rate_date]`
  - `Date[Date]` 1 to many `fct_rates_daily[rate_date]`
  - `Date[Month Start]` to `fct_macro_monthly[month]` and `fct_cpi_monthly[month]`.
    These are many to one from `Date`, so set the filter direction to single, from `Date` to the fact.
- Hide the raw key columns in report view.

## 4. Measures

All measures are in [`measures.dax`](measures.dax). The main ones:

| Measure | What it shows |
|---|---|
| `Latest Rate` | Last available rate for the selected currency |
| `Rate Change %` | Change from the first to the last day in the selected period |
| `Avg 30d Volatility %` | Average of the 30 day annualized volatility |
| `Latest Policy Rate %` | Bank of Canada target for the overnight rate |
| `Latest CPI YoY %` | Headline inflation for the latest released month |
| `Real Policy Rate %` | Policy rate minus inflation |
| `Unemployment Change vs 12m Ago (pts)` | Change in unemployment over the last year |

## 5. Suggested report pages

- **FX**: line chart of `cad_per_unit` and `rolling_avg_30d` by `rate_date`, a currency slicer
  on `dim_currency[currency_name]`, cards for `Latest Rate` and `Rate Change %`.
- **Macro**: line chart of `inflation_yoy_pct` and `policy_rate_eom_pct` by month, a column chart of
  `unemployment_rate_pct`, and a card for `Real Policy Rate %`.

## Refreshing

Click **Refresh** after `make all` has run again. If you want the cloud version to refresh on a
schedule you need a Postgres that the Power BI service can reach and an on-premises data gateway.
I have not set that up; the GitHub Pages dashboard covers the daily view.
