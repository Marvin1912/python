"""Postgres connection pool, schema bootstrap, and a small context-manager helper."""

import logging
import os
import re
from contextlib import contextmanager
from typing import Optional

import psycopg2
from psycopg2 import pool as pg_pool

log = logging.getLogger(__name__)

_pool: Optional[pg_pool.SimpleConnectionPool] = None
_schema: str = "bp"

# Keep this strict — we interpolate the schema name into DDL/DML, so we treat
# it as an identifier, not user input.
_SCHEMA_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def init_pool() -> None:
    """Initialize the global pool from BP_DB_* env vars and remember the schema."""
    global _pool, _schema

    schema = os.environ.get("BP_DB_SCHEMA", "bp")
    if not _SCHEMA_RE.match(schema):
        raise ValueError(
            f"BP_DB_SCHEMA={schema!r} is not a valid Postgres identifier"
        )
    _schema = schema

    _pool = pg_pool.SimpleConnectionPool(
        minconn=1,
        maxconn=int(os.environ.get("BP_DB_POOL_MAX", "5")),
        host=os.environ.get("BP_DB_HOST", "localhost"),
        port=int(os.environ.get("BP_DB_PORT", "5432")),
        dbname=os.environ.get("BP_DB_NAME", "bptracker"),
        user=os.environ.get("BP_DB_USER", "bp"),
        password=os.environ.get("BP_DB_PASSWORD", ""),
    )
    log.info("Postgres pool initialized (schema=%s)", _schema)


def schema() -> str:
    return _schema


@contextmanager
def get_conn():
    """Yield a pooled connection; commit on success, rollback on error."""
    if _pool is None:
        raise RuntimeError("DB pool not initialized; call init_pool() first")
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def bootstrap_schema() -> None:
    """Create the schema, table, and index if they do not yet exist. Idempotent."""
    ddl = f"""
        CREATE SCHEMA IF NOT EXISTS {_schema};

        CREATE TABLE IF NOT EXISTS {_schema}.readings (
            id           BIGSERIAL PRIMARY KEY,
            measured_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            systolic     SMALLINT NOT NULL CHECK (systolic BETWEEN 50 AND 250),
            diastolic    SMALLINT NOT NULL CHECK (diastolic BETWEEN 30 AND 150),
            pulse        SMALLINT NULL CHECK (pulse BETWEEN 20 AND 250),
            note         TEXT NULL,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS readings_measured_at_idx
            ON {_schema}.readings (measured_at DESC);
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
    log.info("Schema bootstrap complete")


def ping() -> bool:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except psycopg2.Error as exc:  # pragma: no cover
        log.warning("DB ping failed: %s", exc)
        return False
