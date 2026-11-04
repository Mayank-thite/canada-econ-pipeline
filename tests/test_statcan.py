"""Parsing tests for the Statistics Canada WDS response. Fixtures recorded from the live API."""

import copy
from datetime import date, datetime
from decimal import Decimal

import pytest

from ingest import statcan
from ingest.boc import SchemaError


def test_parse_vector_data(statcan_payload):
    rows = statcan.parse_vector_data(statcan_payload)
    expected = sum(len(e["object"]["vectorDataPoint"]) for e in statcan_payload)
    assert len(rows) == expected
    row = rows[0]
    assert isinstance(row["ref_period"], date)
    assert row["ref_period"].day == 1
    assert isinstance(row["value"], Decimal)
    assert isinstance(row["release_time"], datetime)


def test_float_values_keep_their_decimal_text(statcan_payload):
    rows = statcan.parse_vector_data(statcan_payload)
    raw = statcan_payload[0]["object"]["vectorDataPoint"][0]["value"]
    assert rows[0]["value"] == Decimal(str(raw))


def test_null_value_is_skipped(statcan_payload):
    payload = copy.deepcopy(statcan_payload)
    payload[0]["object"]["vectorDataPoint"][0]["value"] = None
    full = statcan.parse_vector_data(statcan_payload)
    assert len(statcan.parse_vector_data(payload)) == len(full) - 1


def test_failed_status_raises(statcan_payload):
    payload = copy.deepcopy(statcan_payload)
    payload[0]["status"] = "FAILED"
    with pytest.raises(SchemaError):
        statcan.parse_vector_data(payload)


def test_non_list_raises():
    with pytest.raises(SchemaError):
        statcan.parse_vector_data({"status": "SUCCESS"})


def test_parse_series_info(statcan_info_payload):
    info = {r["vector_id"]: r for r in statcan.parse_series_info(statcan_info_payload)}
    assert info[41690973]["product_id"] == 18100004
    assert info[41690973]["title_en"] == "Canada;All-items"
    assert info[2062815]["product_id"] == 14100287
