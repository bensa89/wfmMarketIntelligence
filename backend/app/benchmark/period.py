from datetime import date, timedelta


def get_period_bounds(period_type: str) -> tuple[date, date]:
    """Return (period_start, period_end) for a period_type string."""
    today = date.today()
    days = {"30d": 30, "90d": 90, "180d": 180}.get(period_type)
    if days is None:
        raise ValueError(f"Unknown period_type: {period_type!r}. Expected '30d', '90d', or '180d'.")
    return today - timedelta(days=days), today
