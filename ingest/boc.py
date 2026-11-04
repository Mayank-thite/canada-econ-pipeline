"""Bank of Canada Valet API: fetch and parse observations."""

from datetime import date
from decimal import Decimal, InvalidOperation

import requests

from ingest.config import BOC_BASE_URL, HTTP_TIMEOUT


class SchemaError(ValueError):
    """The API answered, but not in the shape I expect."""


def fetch_observations(session: requests.Session, series: list[str], start: date, end: date | None = None) -> dict:
    url = f"{BOC_BASE_URL}/observations/{','.join(series)}/json"
    params = {"start_date": start.isoformat()}
    if end:
        params["end_date"] = end.isoformat()
    resp = session.get(url, params=params, timeout=HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def parse_series_detail(payload: dict) -> list[dict]:
    detail = payload.get("seriesDetail")
    if not isinstance(detail, dict):
        raise SchemaError("Valet response has no seriesDetail object")
    rows = []
    for series_id, meta in detail.items():
        rows.append(
            {
                "series_id": series_id,
                "label": meta.get("label"),
                "description": meta.get("description"),
                "unit": (meta.get("metadata") or {}).get("unit"),
                "frequency": (meta.get("metadata") or {}).get("frequency"),
            }
        )
    return rows


def parse_observations(payload: dict, series: list[str]) -> list[dict]:
    """Turn the wide Valet layout into long rows of (series_id, obs_date, value).

    Missing values (holidays, a series that had no fix that day) are skipped.
    """
    obs = payload.get("observations")
    if not isinstance(obs, list):
        raise SchemaError("Valet response has no observations list")
    rows = []
    for item in obs:
        if "d" not in item:
            raise SchemaError(f"Observation without a date key: {item}")
        obs_date = date.fromisoformat(item["d"])
        for series_id in series:
            cell = item.get(series_id)
            if not cell or cell.get("v") in (None, ""):
                continue
            try:
                value = Decimal(cell["v"])
            except InvalidOperation as exc:
                raise SchemaError(f"Non numeric value {cell['v']!r} for {series_id}") from exc
            rows.append({"series_id": series_id, "obs_date": obs_date, "value": value})
    return rows
