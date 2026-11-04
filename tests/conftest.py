import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def boc_payload():
    return load("boc_valet_sample.json")


@pytest.fixture
def statcan_payload():
    return load("statcan_wds_sample.json")


@pytest.fixture
def statcan_info_payload():
    return load("statcan_series_info_sample.json")
