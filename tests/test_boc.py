"""Parsing tests for the Bank of Canada Valet response. Fixture recorded from the live API."""

import copy
from datetime import date
from decimal import Decimal

import pytest

from ingest import boc

SERIES = ["FXUSDCAD", "AVG.INTWO"]


def test_parse_observations_long_format(boc_payload):
    rows = boc.parse_observations(boc_payload, SERIES)
    n_days = len(boc_payload["observations"])
    assert len(rows) == n_days * 2
    first = rows[0]
    assert set(first) == {"series_id", "obs_date", "value"}
    assert isinstance(first["obs_date"], date)
    assert isinstance(first["value"], Decimal)


def test_parse_observations_values_match_payload(boc_payload):
    rows = boc.parse_observations(boc_payload, SERIES)
    obs = boc_payload["observations"][-1]
    usd = [r for r in rows if r["series_id"] == "FXUSDCAD" and r["obs_date"] == date.fromisoformat(obs["d"])]
    assert usd[0]["value"] == Decimal(obs["FXUSDCAD"]["v"])


def test_missing_value_is_skipped(boc_payload):
    payload = copy.deepcopy(boc_payload)
    del payload["observations"][0]["FXUSDCAD"]
    payload["observations"][1]["AVG.INTWO"]["v"] = ""
    rows = boc.parse_observations(payload, SERIES)
    assert len(rows) == len(payload["observations"]) * 2 - 2


def test_non_numeric_value_raises(boc_payload):
    payload = copy.deepcopy(boc_payload)
    payload["observations"][0]["FXUSDCAD"]["v"] = "n/a"
    with pytest.raises(boc.SchemaError):
        boc.parse_observations(payload, SERIES)


def test_missing_observations_key_raises():
    with pytest.raises(boc.SchemaError):
        boc.parse_observations({"seriesDetail": {}}, SERIES)


def test_parse_series_detail(boc_payload):
    meta = {m["series_id"]: m for m in boc.parse_series_detail(boc_payload)}
    assert set(meta) == set(SERIES)
    assert meta["FXUSDCAD"]["label"] == "USD/CAD"
    assert meta["FXUSDCAD"]["unit"] == "Canadian dollars per US dollar"


def test_series_detail_missing_raises():
    with pytest.raises(boc.SchemaError):
        boc.parse_series_detail({"observations": []})
