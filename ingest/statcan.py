"""Statistics Canada Web Data Service: fetch and parse vector data."""

from datetime import date, datetime
from decimal import Decimal

import requests

from ingest.boc import SchemaError
from ingest.config import HTTP_TIMEOUT, STATCAN_BASE_URL


def fetch_vector_range(session: requests.Session, vector_ids: list[int], start: date, end: date) -> list:
    ids = ",".join(f'"{v}"' for v in vector_ids)
    url = (
        f"{STATCAN_BASE_URL}/getDataFromVectorByReferencePeriodRange"
        f"?vectorIds={ids}&startRefPeriod={start.isoformat()}&endReferencePeriod={end.isoformat()}"
    )
    resp = session.get(url, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_series_info(session: requests.Session, vector_ids: list[int]) -> list:
    resp = session.post(
        f"{STATCAN_BASE_URL}/getSeriesInfoFromVector",
        json=[{"vectorId": v} for v in vector_ids],
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def _objects(payload: list) -> list[dict]:
    if not isinstance(payload, list):
        raise SchemaError("WDS response is not a list")
    out = []
    for entry in payload:
        if entry.get("status") != "SUCCESS":
            raise SchemaError(f"WDS returned status {entry.get('status')}: {entry.get('object')}")
        out.append(entry["object"])
    return out


def parse_series_info(payload: list) -> list[dict]:
    return [
        {
            "vector_id": obj["vectorId"],
            "product_id": obj["productId"],
            "coordinate": obj.get("coordinate"),
            "title_en": obj.get("SeriesTitleEn"),
            "frequency_code": obj.get("frequencyCode"),
            "decimals": obj.get("decimals"),
        }
        for obj in _objects(payload)
    ]


def parse_vector_data(payload: list) -> list[dict]:
    rows = []
    for obj in _objects(payload):
        vector_id = obj["vectorId"]
        for point in obj.get("vectorDataPoint", []):
            if point.get("value") is None:
                continue
            release = point.get("releaseTime")
            rows.append(
                {
                    "vector_id": vector_id,
                    "product_id": obj.get("productId"),
                    "ref_period": date.fromisoformat(point["refPer"]),
                    "value": Decimal(str(point["value"])),
                    "decimals": point.get("decimals"),
                    "status_code": point.get("statusCode"),
                    "symbol_code": point.get("symbolCode"),
                    "release_time": datetime.fromisoformat(release) if release else None,
                }
            )
    return rows
