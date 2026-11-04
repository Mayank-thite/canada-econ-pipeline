"""Postgres helpers: create the raw schema, upsert rows, read watermarks."""

from datetime import date

import psycopg2
from psycopg2.extras import execute_values

DDL = """
create schema if not exists raw;

create table if not exists raw.boc_series (
    series_id   text primary key,
    label       text,
    description text,
    unit        text,
    frequency   text,
    loaded_at   timestamptz not null default now()
);

create table if not exists raw.boc_observations (
    series_id text not null,
    obs_date  date not null,
    value     numeric not null,
    loaded_at timestamptz not null default now(),
    primary key (series_id, obs_date)
);

create table if not exists raw.statcan_series (
    vector_id      bigint primary key,
    product_id     bigint,
    coordinate     text,
    title_en       text,
    frequency_code int,
    decimals       int,
    loaded_at      timestamptz not null default now()
);

create table if not exists raw.statcan_observations (
    vector_id    bigint not null,
    product_id   bigint,
    ref_period   date not null,
    value        numeric not null,
    decimals     int,
    status_code  int,
    symbol_code  int,
    release_time timestamp,
    loaded_at    timestamptz not null default now(),
    primary key (vector_id, ref_period)
);

create table if not exists raw.ingest_runs (
    run_id      bigserial primary key,
    source      text not null,
    started_at  timestamptz not null,
    finished_at timestamptz,
    rows_upserted int,
    status      text not null,
    error       text
);
"""

UPSERTS = {
    "boc_series": (
        ["series_id", "label", "description", "unit", "frequency"],
        "series_id",
    ),
    "boc_observations": (["series_id", "obs_date", "value"], "series_id, obs_date"),
    "statcan_series": (
        ["vector_id", "product_id", "coordinate", "title_en", "frequency_code", "decimals"],
        "vector_id",
    ),
    "statcan_observations": (
        [
            "vector_id",
            "product_id",
            "ref_period",
            "value",
            "decimals",
            "status_code",
            "symbol_code",
            "release_time",
        ],
        "vector_id, ref_period",
    ),
}


def connect(url: str):
    return psycopg2.connect(url)


def ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(DDL)
    conn.commit()


def build_upsert_sql(table: str) -> tuple[str, list[str]]:
    cols, key = UPSERTS[table]
    key_cols = {k.strip() for k in key.split(",")}
    updates = ", ".join(f"{c} = excluded.{c}" for c in cols if c not in key_cols)
    sql = (
        f"insert into raw.{table} ({', '.join(cols)}) values %s "
        f"on conflict ({key}) do update set {updates}, loaded_at = now()"
    )
    return sql, cols


def upsert(conn, table: str, rows: list[dict]) -> int:
    """Insert or update rows. Running it twice with the same rows leaves the table the same."""
    if not rows:
        return 0
    sql, cols = build_upsert_sql(table)
    values = [tuple(r.get(c) for c in cols) for r in rows]
    with conn.cursor() as cur:
        execute_values(cur, sql, values, page_size=1000)
    return len(values)


def max_date(conn, table: str, date_col: str, key_col: str, key) -> date | None:
    with conn.cursor() as cur:
        cur.execute(f"select max({date_col}) from raw.{table} where {key_col} = %s", (key,))
        return cur.fetchone()[0]


def log_run(conn, source, started_at, finished_at, rows, status, error=None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "insert into raw.ingest_runs (source, started_at, finished_at, rows_upserted, status, error)"
            " values (%s, %s, %s, %s, %s, %s)",
            (source, started_at, finished_at, rows, status, error),
        )
    conn.commit()
