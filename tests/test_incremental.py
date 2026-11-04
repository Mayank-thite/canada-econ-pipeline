"""Watermark logic and SQL building. No network or database needed."""

from datetime import date, timedelta

from ingest import db
from ingest.main import incremental_start


def test_first_run_uses_default():
    assert incremental_start(None, date(2017, 1, 1), timedelta(days=7)) == date(2017, 1, 1)


def test_later_run_rewinds_by_lookback():
    assert incremental_start(date(2026, 11, 3), date(2017, 1, 1), timedelta(days=7)) == date(2026, 10, 27)


def test_lookback_never_goes_before_default():
    assert incremental_start(date(2017, 1, 3), date(2017, 1, 1), timedelta(days=7)) == date(2017, 1, 1)


def test_upsert_sql_updates_non_key_columns():
    sql, cols = db.build_upsert_sql("boc_observations")
    assert cols == ["series_id", "obs_date", "value"]
    assert "on conflict (series_id, obs_date)" in sql
    assert "value = excluded.value" in sql
    assert "series_id = excluded" not in sql


def test_statcan_always_pulls_full_history(monkeypatch, statcan_payload, statcan_info_payload):
    """LFS revisions reach back years, so the StatCan load must never start from a watermark."""
    from unittest.mock import MagicMock

    from ingest import main as main_mod
    from ingest.config import STATCAN_START_DATE

    seen = {}

    def fake_range(_session, _vectors, start, end):
        seen["start"] = start
        return statcan_payload

    monkeypatch.setattr(main_mod.statcan, "fetch_vector_range", fake_range)
    monkeypatch.setattr(main_mod.statcan, "fetch_series_info", lambda *_: statcan_info_payload)
    monkeypatch.setattr(main_mod.db, "max_date", lambda *_: date(2026, 9, 1))
    monkeypatch.setattr(main_mod.db, "upsert", lambda _conn, _table, rows: len(rows))
    main_mod.load_statcan(MagicMock(), None, full=False)
    assert seen["start"] == STATCAN_START_DATE
