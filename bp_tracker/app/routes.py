"""HTTP endpoints: HTML index, readings CRUD, stats, healthz."""

import logging
from datetime import date, datetime
from io import BytesIO
from typing import Any, Optional

from flask import Flask, jsonify, render_template, request, send_file

from . import db, pdf_export, repository
from .categorize import ValidationError, validate_reading
from .repository import DISPLAY_TZ

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

    @app.put("/api/readings/<int:reading_id>")
    def update_reading(reading_id: int):
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

        reading = repository.update_reading(
            reading_id,
            systolic=systolic,
            diastolic=diastolic,
            pulse=pulse,
            note=note,
            measured_at=measured_at,
        )
        if reading is None:
            return jsonify({"error": "reading not found"}), 404
        return jsonify(reading)

    @app.delete("/api/readings/<int:reading_id>")
    def delete_reading(reading_id: int):
        if not repository.delete_reading(reading_id):
            return jsonify({"error": "reading not found"}), 404
        return ("", 204)

    @app.get("/api/readings/export.pdf")
    def export_readings_pdf():
        range_key = request.args.get("range", "all")
        try:
            items = repository.list_readings(range_key)
            stats_data = repository.stats(range_key)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        pdf_bytes = pdf_export.build_readings_pdf(range_key, items, stats_data)
        filename = f"bp-readings-{range_key}-{date.today().isoformat()}.pdf"
        return send_file(
            BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )

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
        dt = datetime.fromisoformat(raw)
    except ValueError:
        raise ValidationError(f"{key} must be ISO 8601 (e.g. 2026-05-09T10:30)")
    # Treat naive input as Europe/Berlin wall-clock time.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=DISPLAY_TZ)
    return dt
