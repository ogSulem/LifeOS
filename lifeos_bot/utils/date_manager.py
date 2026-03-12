from __future__ import annotations

from datetime import date, timedelta


def shift_day(day: date, delta_days: int) -> date:
    return day + timedelta(days=delta_days)
