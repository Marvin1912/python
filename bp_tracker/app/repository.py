"""SQL queries for readings: insert, list, and stats."""

from datetime import datetime
from typing import Any, Optional

from . import db
from .categorize import (
    categorize,
    mean_arterial_pressure,
    pulse_pressure,
)

# Range query → SQL WHERE fragment. Validated against this whitelist before use.
_RANGE_WHERE = {
    "7d": "WHERE measured_at >= now() - interval '7 days'",
    "30d": "WHERE measured_at >= now() - interval '30 days'",
    "all": "",
}


def _range_sql(range_key: str) -> str:
    if range_key not in _RANGE_WHERE:
        raise ValueError(f"unknown range: {range_key}")
    return _RANGE_WHERE[range_key]


def _row_to_dict(row: tuple) -> dict[str, Any]:
    rid, measured_at, systolic, diastolic, pulse, note, created_at = row
    return {
        "id": rid,
        "measured_at": measured_at.isoformat(),
        "systolic": systolic,
        "diastolic": diastolic,
        "pulse": pulse,
        "note": note,
        "created_at": created_at.isoformat(),
        "category": categorize(systolic, diastolic),
        "map": mean_arterial_pressure(systolic, diastolic),
        "pulse_pressure": pulse_pressure(systolic, diastolic),
    }


def insert_reading(
    *,
    systolic: int,
    diastolic: int,
    pulse: Optional[int],
    note: Optional[str],
    measured_at: Optional[datetime],
) -> dict[str, Any]:
    schema = db.schema()
    sql = f"""
        INSERT INTO {schema}.readings (measured_at, systolic, diastolic, pulse, note)
        VALUES (COALESCE(%s, now()), %s, %s, %s, %s)
        RETURNING id, measured_at, systolic, diastolic, pulse, note, created_at
    """
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (measured_at, systolic, diastolic, pulse, note))
            row = cur.fetchone()
    return _row_to_dict(row)


def update_reading(
    reading_id: int,
    *,
    systolic: int,
    diastolic: int,
    pulse: Optional[int],
    note: Optional[str],
    measured_at: Optional[datetime],
) -> Optional[dict[str, Any]]:
    schema = db.schema()
    sql = f"""
        UPDATE {schema}.readings
        SET measured_at = COALESCE(%s, measured_at),
            systolic = %s,
            diastolic = %s,
            pulse = %s,
            note = %s
        WHERE id = %s
        RETURNING id, measured_at, systolic, diastolic, pulse, note, created_at
    """
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (measured_at, systolic, diastolic, pulse, note, reading_id))
            row = cur.fetchone()
    return _row_to_dict(row) if row else None


def delete_reading(reading_id: int) -> bool:
    schema = db.schema()
    sql = f"DELETE FROM {schema}.readings WHERE id = %s"
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (reading_id,))
            return cur.rowcount > 0


def list_readings(range_key: str) -> list[dict[str, Any]]:
    schema = db.schema()
    where = _range_sql(range_key)
    sql = f"""
        SELECT id, measured_at, systolic, diastolic, pulse, note, created_at
        FROM {schema}.readings
        {where}
        ORDER BY measured_at ASC
    """
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    return [_row_to_dict(r) for r in rows]


def stats(range_key: str) -> dict[str, Any]:
    """Average and median over a range, plus average MAP and pulse pressure.

    Median uses Postgres' percentile_cont for accuracy on small samples.
    """
    schema = db.schema()
    where = _range_sql(range_key)
    sql = f"""
        SELECT
            COUNT(*) AS n,
            AVG(systolic)::float AS sys_avg,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY systolic) AS sys_median,
            AVG(diastolic)::float AS dia_avg,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY diastolic) AS dia_median,
            AVG(pulse)::float AS pulse_avg,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY pulse) AS pulse_median,
            AVG(diastolic + (systolic - diastolic) / 3.0)::float AS map_avg,
            AVG(systolic - diastolic)::float AS pp_avg
        FROM {schema}.readings
        {where}
    """
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()

    n, sys_avg, sys_med, dia_avg, dia_med, pulse_avg, pulse_med, map_avg, pp_avg = row

    def _r1(value):
        return round(value, 1) if value is not None else None

    return {
        "count": n,
        "systolic": {"avg": _r1(sys_avg), "median": _r1(sys_med)},
        "diastolic": {"avg": _r1(dia_avg), "median": _r1(dia_med)},
        "pulse": {"avg": _r1(pulse_avg), "median": _r1(pulse_med)},
        "map_avg": _r1(map_avg),
        "pulse_pressure_avg": _r1(pp_avg),
    }
