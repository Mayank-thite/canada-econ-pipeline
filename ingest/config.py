"""Series I pull and a few settings. Everything here is public and keyless."""

import os
from datetime import date

BOC_BASE_URL = "https://www.bankofcanada.ca/valet"
STATCAN_BASE_URL = "https://www150.statcan.gc.ca/t1/wds/rest"

# Bank of Canada Valet series. FX rates are CAD per one unit of foreign currency.
BOC_SERIES = {
    "FXUSDCAD": "fx",
    "FXEURCAD": "fx",
    "FXGBPCAD": "fx",
    "FXJPYCAD": "fx",
    "FXCNYCAD": "fx",
    "V39079": "rate",  # Target for the overnight rate (policy rate)
    "AVG.INTWO": "rate",  # CORRA
}

# Statistics Canada vectors.
STATCAN_VECTORS = {
    41690973: "cpi_all_items",  # Table 18-10-0004-01, Canada, all-items CPI, 2002=100, not seasonally adjusted
    2062815: "unemployment_rate",  # Table 14-10-0287-01, Canada, 15+, seasonally adjusted
}

# First load goes back this far. CPI needs one extra year before the FX start for YoY.
BOC_START_DATE = date(2017, 1, 1)
STATCAN_START_DATE = date(2016, 1, 1)

# On incremental runs I re-pull a small window so revisions and late rows get picked up.
BOC_LOOKBACK_DAYS = 7
STATCAN_LOOKBACK_MONTHS = 3

HTTP_TIMEOUT = 30
HTTP_RETRIES = 4


def database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://{user}:{pw}@{host}:{port}/{db}".format(
            user=os.environ.get("PGUSER", "econ"),
            pw=os.environ.get("PGPASSWORD", "econ"),
            host=os.environ.get("PGHOST", "localhost"),
            port=os.environ.get("PGPORT", "5432"),
            db=os.environ.get("PGDATABASE", "econ"),
        ),
    )
