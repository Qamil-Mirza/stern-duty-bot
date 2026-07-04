import datetime

REQUIRED_FIELDS = ["Stern RAM A", "Stern RAM B", "Stern ARD", "RD"]

_FORMATS_WITH_YEAR = ["%B %d, %Y", "%B %d %Y", "%m/%d/%Y", "%Y-%m-%d"]
_FORMATS_WITHOUT_YEAR = ["%B %d", "%m/%d"]


def parse_duty_date(text, year):
    """Parse a sheet date cell like "July 5" into a date, or None."""
    text = str(text).strip()
    for fmt in _FORMATS_WITH_YEAR:
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    for fmt in _FORMATS_WITHOUT_YEAR:
        try:
            return datetime.datetime.strptime(f"{text} {year}", f"{fmt} %Y").date()
        except ValueError:
            pass
    return None


def find_duty_row(rows, target_date, year):
    """Return the first row whose Duty Date matches target_date, or None."""
    for row in rows:
        if parse_duty_date(row.get("Duty Date", ""), year) == target_date:
            return row
    return None


def missing_fields(row):
    """Return the required staff columns that are blank in this row."""
    return [f for f in REQUIRED_FIELDS if not str(row.get(f, "")).strip()]
