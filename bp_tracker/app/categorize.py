"""Blood pressure validation, AHA category classification, and derived metrics."""

from typing import Optional

# Per-field guard rails (must match DB CHECK constraints).
SYS_MIN, SYS_MAX = 50, 250
DIA_MIN, DIA_MAX = 30, 150
PULSE_MIN, PULSE_MAX = 20, 250


class ValidationError(ValueError):
    pass


def validate_reading(systolic: int, diastolic: int, pulse: Optional[int]) -> None:
    if not (SYS_MIN <= systolic <= SYS_MAX):
        raise ValidationError(
            f"systolic must be between {SYS_MIN} and {SYS_MAX}"
        )
    if not (DIA_MIN <= diastolic <= DIA_MAX):
        raise ValidationError(
            f"diastolic must be between {DIA_MIN} and {DIA_MAX}"
        )
    if systolic <= diastolic:
        raise ValidationError("systolic must be greater than diastolic")
    if pulse is not None and not (PULSE_MIN <= pulse <= PULSE_MAX):
        raise ValidationError(
            f"pulse must be between {PULSE_MIN} and {PULSE_MAX}"
        )


def categorize(systolic: int, diastolic: int) -> str:
    """AHA/ACC 2025 hypertension category. Order matters: crisis first."""
    if systolic >= 180 or diastolic >= 120:
        return "Hypertensive Crisis"
    if systolic >= 140 or diastolic >= 90:
        return "Stage 2"
    if (130 <= systolic <= 139) or (80 <= diastolic <= 89):
        return "Stage 1"
    if 120 <= systolic <= 129 and diastolic < 80:
        return "Elevated"
    return "Normal"


def mean_arterial_pressure(systolic: int, diastolic: int) -> float:
    """MAP ≈ DBP + (SBP − DBP) / 3."""
    return round(diastolic + (systolic - diastolic) / 3.0, 1)


def pulse_pressure(systolic: int, diastolic: int) -> int:
    return systolic - diastolic
