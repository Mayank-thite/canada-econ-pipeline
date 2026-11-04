"""Run the extract and load step.

python -m ingest.main            # incremental, both sources
python -m ingest.main --full     # reload Bank of Canada data from the start date too
python -m ingest.main --source boc
"""

import argparse
import logging
import sys
from datetime import UTC, date, datetime, timedelta

import requests
from psycopg2.extensions import connection

from ingest import boc, db, statcan
from ingest.config import (
    BOC_LOOKBACK_DAYS,
    BOC_SERIES,
    BOC_START_DATE,
    STATCAN_START_DATE,
    STATCAN_VECTORS,
    database_url,
)
from ingest.http import make_session

log = logging.getLogger("ingest")


def incremental_start(last: date | None, default: date, lookback: timedelta) -> date:
    """Where to start pulling. First run uses the default; later runs re-pull a small window."""
    if last is None:
        return default
    return max(default, last - lookback)


def load_boc(conn: connection, session: requests.Session, full: bool) -> int:
    """Pull Bank of Canada series from the oldest watermark minus the look-back, and upsert them."""
    series = list(BOC_SERIES)
    starts = []
    for s in series:
        last = None if full else db.max_date(conn, "boc_observations", "obs_date", "series_id", s)
        starts.append(incremental_start(last, BOC_START_DATE, timedelta(days=BOC_LOOKBACK_DAYS)))
    start = min(starts)
    log.info("BoC: pulling %d series from %s", len(series), start)
    payload = boc.fetch_observations(session, series, start)
    meta = boc.parse_series_detail(payload)
    missing = set(series) - {m["series_id"] for m in meta}
    if missing:
        raise boc.SchemaError(f"Valet did not return series {sorted(missing)}")
    rows = boc.parse_observations(payload, series)
    db.upsert(conn, "boc_series", meta)
    n = db.upsert(conn, "boc_observations", rows)
    conn.commit()
    log.info("BoC: upserted %d observations", n)
    return n


def load_statcan(conn: connection, session: requests.Session, full: bool) -> int:
    """Pull the full Statistics Canada history every time so revisions to any month are picked up.

    `full` is accepted so every loader has the same signature. This source always does a full pull.
    """
    vectors = list(STATCAN_VECTORS)
    start = STATCAN_START_DATE
    end = date.today()
    log.info("StatCan: pulling %d vectors from %s", len(vectors), start)
    info = statcan.parse_series_info(statcan.fetch_series_info(session, vectors))
    rows = statcan.parse_vector_data(statcan.fetch_vector_range(session, vectors, start, end))
    db.upsert(conn, "statcan_series", info)
    n = db.upsert(conn, "statcan_observations", rows)
    conn.commit()
    log.info("StatCan: upserted %d observations", n)
    return n


LOADERS = {"boc": load_boc, "statcan": load_statcan}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", choices=[*LOADERS, "all"], default="all")
    parser.add_argument("--full", action="store_true", help="ignore watermarks and reload everything")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    conn = db.connect(database_url())
    db.ensure_schema(conn)
    session = make_session()
    sources = list(LOADERS) if args.source == "all" else [args.source]
    failed = []
    for source in sources:
        started = datetime.now(UTC)
        try:
            n = LOADERS[source](conn, session, args.full)
            db.log_run(conn, source, started, datetime.now(UTC), n, "success")
        except Exception as exc:  # keep going so one bad source does not block the other
            conn.rollback()
            log.exception("%s failed", source)
            db.log_run(conn, source, started, datetime.now(UTC), 0, "failed", str(exc)[:1000])
            failed.append(source)
    conn.close()
    if failed:
        log.error("Failed sources: %s", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
