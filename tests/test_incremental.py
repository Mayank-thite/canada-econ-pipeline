"""Watermark logic and SQL building. No network or database needed."""

from datetime import date, timedelta

from ingest import db
from ingest.main import incremental_start, months_back


def test_first_run_uses_default():
    assert incremental_start(None, date(2017, 1, 1), timedelta(days=7)) == date(2017, 1, 1)


def test_later_run_rewinds_by_lookback():
    assert incremental_start(date(2026, 11, 3), date(2017, 1, 1), timedelta(days=7)) == date(2026, 10, 27)


def test_lookback_never_goes_before_default():
    assert incremental_start(date(2017, 1, 3), date(2017, 1, 1), timedelta(days=7)) == date(2017, 1, 1)


def test_months_back_crosses_year():
    assert months_back(date(2026, 2, 1), 3) == date(2025, 11, 1)
    assert months_back(date(2026, 9, 1), 3) == date(2026, 6, 1)


def test_upsert_sql_updates_non_key_columns():
    sql, cols = db.build_upsert_sql("boc_observations")
    assert cols == ["series_id", "obs_date", "value"]
    assert "on conflict (series_id, obs_date)" in sql
    assert "value = excluded.value" in sql
    assert "series_id = excluded" not in sql
