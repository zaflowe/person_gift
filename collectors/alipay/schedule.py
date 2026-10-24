"""Calendar schedule: no catch-up requests during the daily quiet window."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ZONE = ZoneInfo("Asia/Shanghai")


def allowed(now: datetime) -> bool:
    return now.astimezone(ZONE).hour >= 12


def next_slot(now: datetime, hours=(12, 16, 20)) -> datetime:
    local = now.astimezone(ZONE)
    for day in range(2):
        date = local + timedelta(days=day)
        for hour in sorted(hours):
            slot = date.replace(hour=hour, minute=0, second=0, microsecond=0)
            if slot > local:
                return slot
    raise ValueError("no_scheduled_hours")
