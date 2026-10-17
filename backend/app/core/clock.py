from datetime import datetime, date, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Tuple


class Clock:
    """Injectable clock so tests can freeze time."""

    def __init__(self, fixed_now: datetime | None = None):
        self._fixed_now = fixed_now

    def now(self, tz: str | None = None) -> datetime:
        if self._fixed_now is not None:
            now = self._fixed_now
        else:
            now = datetime.now(timezone.utc)
        if tz:
            return now.astimezone(ZoneInfo(tz))
        return now

    def today(self, tz: str) -> date:
        return self.now(tz).date()


def get_month_boundaries(ref: datetime, tz: str) -> Tuple[datetime, datetime, datetime, datetime]:
    """
    Returns (prev_start, prev_end, curr_start, curr_end) as timezone-aware datetimes.
    Boundaries are [start, end) — end is exclusive.
    """
    local = ref.astimezone(ZoneInfo(tz))
    year, month = local.year, local.month

    # Current month start
    curr_start = datetime(year, month, 1, tzinfo=ZoneInfo(tz))

    # Next month start = current month end (exclusive)
    if month == 12:
        curr_end = datetime(year + 1, 1, 1, tzinfo=ZoneInfo(tz))
    else:
        curr_end = datetime(year, month + 1, 1, tzinfo=ZoneInfo(tz))

    # Previous month
    if month == 1:
        prev_start = datetime(year - 1, 12, 1, tzinfo=ZoneInfo(tz))
        prev_end = curr_start
    else:
        prev_start = datetime(year, month - 1, 1, tzinfo=ZoneInfo(tz))
        prev_end = curr_start

    return prev_start, prev_end, curr_start, curr_end


# Default global instance (can be overridden in tests)
clock = Clock()
