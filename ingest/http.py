"""A requests session with retries and backoff."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ingest.config import HTTP_RETRIES


def make_session() -> requests.Session:
    retry = Retry(
        total=HTTP_RETRIES,
        backoff_factor=2,  # 0s, 2s, 4s, 8s
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
        raise_on_status=False,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers["User-Agent"] = "canada-econ-pipeline (portfolio project)"
    return session
