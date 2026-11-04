"""Checks that loading the same rows twice leaves the table unchanged.

Runs only when a Postgres database is reachable (local `make db` or the CI service container).
"""

import os
from datetime import date
from decimal import Decimal

import pytest

from ingest import db
from ingest.config import database_url

psycopg2 = pytest.importorskip("psycopg2")


@pytest.fixture
def conn():
    try:
        c = db.connect(database_url())
    except psycopg2.OperationalError:
        pytest.skip("no Postgres reachable")
    db.ensure_schema(c)
    yield c
    with c.cursor() as cur:
        cur.execute("delete from raw.boc_observations where series_id = 'TEST_SERIES'")
    c.commit()
    c.close()


@pytest.mark.skipif(os.environ.get("SKIP_DB_TESTS") == "1", reason="SKIP_DB_TESTS=1")
def test_upsert_is_idempotent(conn):
    rows = [
        {"series_id": "TEST_SERIES", "obs_date": date(2026, 1, 2), "value": Decimal("1.2345")},
        {"series_id": "TEST_SERIES", "obs_date": date(2026, 1, 5), "value": Decimal("1.2400")},
    ]
    db.upsert(conn, "boc_observations", rows)
    db.upsert(conn, "boc_observations", rows)
    rows[1]["value"] = Decimal("1.2500")  # a revision
    db.upsert(conn, "boc_observations", rows)
    conn.commit()
    with conn.cursor() as cur:
        cur.execute(
            "select obs_date, value from raw.boc_observations where series_id = 'TEST_SERIES' order by obs_date"
        )
        got = cur.fetchall()
    assert got == [(date(2026, 1, 2), Decimal("1.2345")), (date(2026, 1, 5), Decimal("1.2500"))]
    assert db.max_date(conn, "boc_observations", "obs_date", "series_id", "TEST_SERIES") == date(2026, 1, 5)


@pytest.mark.skipif(os.environ.get("SKIP_DB_TESTS") == "1", reason="SKIP_DB_TESTS=1")
def test_failed_source_is_logged_and_exit_code_is_1(conn, monkeypatch):
    from ingest import main as main_mod

    def broken(*_args):
        raise main_mod.boc.SchemaError("simulated schema change")

    monkeypatch.setattr(main_mod, "LOADERS", {"boc": broken})
    assert main_mod.main(["--source", "boc"]) == 1
    with conn.cursor() as cur:
        cur.execute("select status, error from raw.ingest_runs order by run_id desc limit 1")
        status, error = cur.fetchone()
        cur.execute("delete from raw.ingest_runs where error = 'simulated schema change'")
    conn.commit()
    assert status == "failed"
    assert error == "simulated schema change"
