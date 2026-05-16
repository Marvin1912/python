"""Render a readings export as a PDF document (reportlab Platypus)."""

from datetime import datetime
from io import BytesIO
from typing import Any

from .repository import DISPLAY_TZ

from reportlab.graphics.shapes import Circle, Drawing, Line, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_RANGE_LABELS = {
    "7d": "Last 7 days",
    "30d": "Last 30 days",
    "all": "All time",
}

# Match the on-screen badge palette in static/style.css.
_CATEGORY_COLORS = {
    "Normal": colors.HexColor("#16a34a"),
    "Elevated": colors.HexColor("#ca8a04"),
    "Stage 1": colors.HexColor("#ea580c"),
    "Stage 2": colors.HexColor("#dc2626"),
    "Hypertensive Crisis": colors.HexColor("#7f1d1d"),
}


def build_readings_pdf(
    range_key: str,
    readings: list[dict[str, Any]],
    stats: dict[str, Any],
) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="Blood Pressure Readings",
    )
    styles = getSampleStyleSheet()
    story: list[Any] = []

    range_label = _RANGE_LABELS.get(range_key, range_key)
    generated = datetime.now(DISPLAY_TZ).strftime("%Y-%m-%d %H:%M %Z")

    story.append(Paragraph("Blood Pressure Readings", styles["Title"]))
    story.append(Paragraph(f"Range: {range_label}", styles["Normal"]))
    story.append(Paragraph(f"Generated: {generated}", styles["Normal"]))
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Summary", styles["Heading2"]))
    story.append(_summary_table(stats))
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Measurement times", styles["Heading2"]))
    if readings:
        story.append(_times_scatter_drawing(readings))
    else:
        story.append(Paragraph("No readings in this range.", styles["Normal"]))
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Readings", styles["Heading2"]))
    if readings:
        # Show newest first in the export (DB order is ascending by measured_at).
        story.append(_readings_table(list(reversed(readings))))
    else:
        story.append(Paragraph("No readings in this range.", styles["Normal"]))

    doc.build(story)
    return buf.getvalue()


def _fmt(value: Any, suffix: str = "") -> str:
    if value is None:
        return "—"
    return f"{value}{suffix}"


def _summary_table(stats: dict[str, Any]) -> Table:
    sys_ = stats["systolic"]
    dia = stats["diastolic"]
    pulse = stats["pulse"]
    rows = [
        ["Readings", _fmt(stats["count"])],
        ["Systolic avg / median", f"{_fmt(sys_['avg'])} / {_fmt(sys_['median'])}"],
        ["Diastolic avg / median", f"{_fmt(dia['avg'])} / {_fmt(dia['median'])}"],
        ["Pulse avg / median", f"{_fmt(pulse['avg'])} / {_fmt(pulse['median'])}"],
        ["MAP avg", _fmt(stats["map_avg"], " mmHg")],
        ["Pulse pressure avg", _fmt(stats["pulse_pressure_avg"], " mmHg")],
    ]
    table = Table(rows, colWidths=[60 * mm, 60 * mm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _readings_table(readings: list[dict[str, Any]]) -> Table:
    header = [
        "Measured at",
        "Sys",
        "Dia",
        "Pulse",
        "Category",
        "MAP",
        "PP",
        "Note",
    ]
    body: list[list[Any]] = [header]
    cat_rows: list[tuple[int, str]] = []
    for idx, r in enumerate(readings, start=1):
        cat_rows.append((idx, r["category"]))
        body.append(
            [
                _format_measured_at(r["measured_at"]),
                str(r["systolic"]),
                str(r["diastolic"]),
                _fmt(r["pulse"]),
                r["category"],
                str(r["map"]),
                str(r["pulse_pressure"]),
                r.get("note") or "",
            ]
        )

    col_widths = [
        32 * mm,
        12 * mm,
        12 * mm,
        14 * mm,
        30 * mm,
        14 * mm,
        12 * mm,
        54 * mm,
    ]
    table = Table(body, colWidths=col_widths, repeatRows=1)

    style = TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("ALIGN", (1, 1), (6, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
    )
    for row_idx, category in cat_rows:
        color = _CATEGORY_COLORS.get(category)
        if color is not None:
            style.add("TEXTCOLOR", (4, row_idx), (4, row_idx), color)
            style.add("FONTNAME", (4, row_idx), (4, row_idx), "Helvetica-Bold")
    table.setStyle(style)
    return table


def _times_scatter_drawing(readings: list[dict[str, Any]]) -> Drawing:
    width = 170 * mm
    height = 40 * mm
    pad_left = 10 * mm
    pad_right = 5 * mm
    pad_top = 4 * mm
    pad_bottom = 10 * mm

    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom
    baseline_y = pad_bottom
    band_center_y = pad_bottom + plot_h / 2
    band_half_h = plot_h / 2 - 2

    drawing = Drawing(width, height)

    drawing.add(
        Line(
            pad_left,
            baseline_y,
            pad_left + plot_w,
            baseline_y,
            strokeColor=colors.grey,
            strokeWidth=0.5,
        )
    )
    for hour in (0, 3, 6, 9, 12, 15, 18, 21, 24):
        x = pad_left + (hour / 24) * plot_w
        drawing.add(
            Line(x, baseline_y - 1.5, x, baseline_y + 1.5, strokeColor=colors.grey, strokeWidth=0.5)
        )
        label = String(x, baseline_y - 8, f"{hour:02d}:00", fontSize=7, fillColor=colors.grey)
        label.textAnchor = "middle"
        drawing.add(label)

    for r in readings:
        try:
            dt = datetime.fromisoformat(r["measured_at"]).astimezone(DISPLAY_TZ)
        except ValueError:
            continue
        x_frac = (dt.hour + dt.minute / 60 + dt.second / 3600) / 24
        x = pad_left + x_frac * plot_w
        jitter = _jitter_from_id(int(r["id"]))
        y = band_center_y + jitter * 2 * band_half_h
        fill = _CATEGORY_COLORS.get(r.get("category", ""), colors.grey)
        drawing.add(Circle(x, y, 1.6, fillColor=fill, strokeColor=None))

    return drawing


def _jitter_from_id(reading_id: int) -> float:
    # Deterministic jitter in [-0.5, 0.5] — mirrors the JS implementation in static/app.js.
    return (((reading_id * 9301 + 49297) % 233280) / 233280) - 0.5


def _format_measured_at(value: str) -> str:
    # Repository emits ISO 8601 with timezone; render in Europe/Berlin.
    try:
        dt = datetime.fromisoformat(value).astimezone(DISPLAY_TZ)
    except ValueError:
        return value
    return dt.strftime("%Y-%m-%d %H:%M")
