"""
US Stock Market Calendar with holiday handling
"""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")

# US Stock Market holidays (NYSE/NASDAQ)
# These are the typical holidays - may need annual updates
US_MARKET_HOLIDAYS_2024 = [
    date(2024, 1, 1),   # New Year's Day
    date(2024, 1, 15),  # Martin Luther King Jr. Day
    date(2024, 2, 19),  # Presidents Day
    date(2024, 3, 29),  # Good Friday
    date(2024, 5, 27),  # Memorial Day
    date(2024, 6, 19),  # Juneteenth
    date(2024, 7, 4),   # Independence Day
    date(2024, 9, 2),   # Labor Day
    date(2024, 11, 28), # Thanksgiving
    date(2024, 12, 25), # Christmas
]

US_MARKET_HOLIDAYS_2025 = [
    date(2025, 1, 1),   # New Year's Day
    date(2025, 1, 20),  # Martin Luther King Jr. Day
    date(2025, 2, 17),  # Presidents Day
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 26),  # Memorial Day
    date(2025, 6, 19),  # Juneteenth
    date(2025, 7, 4),   # Independence Day
    date(2025, 9, 1),   # Labor Day
    date(2025, 11, 27), # Thanksgiving
    date(2025, 12, 25), # Christmas
]

US_MARKET_HOLIDAYS_2026 = [
    date(2026, 1, 1),   # New Year's Day
    date(2026, 1, 19),  # Martin Luther King Jr. Day
    date(2026, 2, 16),  # Presidents Day
    date(2026, 4, 3),   # Good Friday
    date(2026, 5, 25),  # Memorial Day
    date(2026, 6, 19),  # Juneteenth
    date(2026, 7, 3),   # Independence Day (observed)
    date(2026, 9, 7),   # Labor Day
    date(2026, 11, 26), # Thanksgiving
    date(2026, 12, 25), # Christmas
]

# Combine all holidays
ALL_HOLIDAYS = set(US_MARKET_HOLIDAYS_2024 + US_MARKET_HOLIDAYS_2025 + US_MARKET_HOLIDAYS_2026)

# Early close days (typically 1:00 PM ET close)
EARLY_CLOSE_DAYS_2024 = [
    date(2024, 7, 3),   # Day before Independence Day
    date(2024, 11, 29), # Day after Thanksgiving
    date(2024, 12, 24), # Christmas Eve
]

EARLY_CLOSE_DAYS_2025 = [
    date(2025, 7, 3),   # Day before Independence Day
    date(2025, 11, 28), # Day after Thanksgiving
    date(2025, 12, 24), # Christmas Eve
]

EARLY_CLOSE_DAYS_2026 = [
    date(2026, 7, 2),   # Day before Independence Day (observed)
    date(2026, 11, 27), # Day after Thanksgiving
    date(2026, 12, 24), # Christmas Eve
]

ALL_EARLY_CLOSE_DAYS = set(EARLY_CLOSE_DAYS_2024 + EARLY_CLOSE_DAYS_2025 + EARLY_CLOSE_DAYS_2026)


def is_market_holiday(check_date: date) -> bool:
    """Check if a given date is a market holiday"""
    return check_date in ALL_HOLIDAYS


def is_early_close_day(check_date: date) -> bool:
    """Check if a given date is an early close day"""
    return check_date in ALL_EARLY_CLOSE_DAYS


def is_market_open(now: datetime = None) -> bool:
    """
    Check if the market is currently open

    Args:
        now: Datetime to check (defaults to current time)

    Returns:
        True if market is open, False otherwise
    """
    if now is None:
        now = datetime.now(EASTERN)
    else:
        now = now.astimezone(EASTERN)

    # Check if weekend
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False

    # Check if holiday
    if is_market_holiday(now.date()):
        return False

    # Check market hours
    market_open_time = time(9, 30)  # 9:30 AM ET

    # Check for early close
    if is_early_close_day(now.date()):
        market_close_time = time(13, 0)  # 1:00 PM ET
    else:
        market_close_time = time(16, 0)  # 4:00 PM ET

    current_time = now.time()

    return market_open_time <= current_time <= market_close_time


def get_market_close_time(check_date: date) -> time:
    """Get the market close time for a given date"""
    if is_early_close_day(check_date):
        return time(13, 0)  # 1:00 PM ET
    return time(16, 0)  # 4:00 PM ET


def is_trading_day(check_date: date) -> bool:
    """Check if a given date is a trading day (not weekend or holiday)"""
    # Create a datetime for the date
    dt = datetime.combine(check_date, time(12, 0), tzinfo=EASTERN)

    # Check if weekend
    if dt.weekday() >= 5:
        return False

    # Check if holiday
    if is_market_holiday(check_date):
        return False

    return True


def next_trading_day(from_date: date = None) -> date:
    """Get the next trading day after the given date"""
    if from_date is None:
        from_date = datetime.now(EASTERN).date()

    check_date = from_date
    while True:
        check_date = date.fromordinal(check_date.toordinal() + 1)
        if is_trading_day(check_date):
            return check_date


def previous_trading_day(from_date: date = None) -> date:
    """Get the previous trading day before the given date"""
    if from_date is None:
        from_date = datetime.now(EASTERN).date()

    check_date = from_date
    while True:
        check_date = date.fromordinal(check_date.toordinal() - 1)
        if is_trading_day(check_date):
            return check_date
