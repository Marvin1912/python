"""HTTP endpoints: HTML index, readings CRUD, stats, healthz."""

import logging
from datetime import datetime
from typing import Any, Optional

from flask import Flask, jsonify, render_template, request

from . import db, repository
from .categorize import ValidationError, validate_reading

log = logging.getLogger(__name__)


def register(app: Flask) -> None:
    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/api/readings")
    def create_reading():
        payload = request.get_json(silent=True) or {}
        try:
            systolic = _required_int(payload, "systolic")
            diastolic = _required_int(payload, "diastolic")
            pulse = _optional_int(payload, "pulse")
            measured_at = _optional_datetime(payload, "measured_at")
            note = (payload.get("note") or "").strip() or None

            validate_reading(systolic, diastolic, pulse)
        except ValidationError as exc:
            return jsonify({"error": str(exc)}), 400

        reading = repository.insert_reading(
            systolic=systolic,
            diastolic=diastolic,
            pulse=pulse,
            note=note,
            measured_at=measured_at,
        )
        return jsonify(reading), 201

    @app.get("/api/readings")
    def list_readings():
        range_key = request.args.get("range", "all")
        try:
            items = repository.list_readings(range_key)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"items": items})

    @app.get("/api/stats")
    def stats():
        range_key = request.args.get("range", "all")
        try:
            return jsonify(repository.stats(range_key))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.get("/healthz")
    def healthz():
        ok = db.ping()
        return (
            jsonify({"status": "ok" if ok else "degraded", "db": "ok" if ok else "down"}),
            200 if ok else 503,
        )


def _required_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if value is None or value == "":
        raise ValidationError(f"{key} is required")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{key} must be an integer")


def _optional_int(payload: dict[str, Any], key: str) -> Optional[int]:
    value = payload.get(key)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{key} must be an integer")


def _optional_datetime(payload: dict[str, Any], key: str) -> Optional[datetime]:
    value = payload.get(key)
    if not value:
        return None
    raw = str(value)
    # `<input type="datetime-local">` produces strings like "2026-05-09T10:30"
    # without timezone info; tolerate that and the standard ISO form.
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        raise ValidationError(f"{key} must be ISO 8601 (e.g. 2026-05-09T10:30)")
