import datetime

from duty_bot.parser import find_duty_row, missing_fields, parse_duty_date


def test_parses_month_day_using_configured_year():
    assert parse_duty_date("July 5", 2026) == datetime.date(2026, 7, 5)


def test_parses_date_that_already_includes_year():
    assert parse_duty_date("July 5, 2026", 2026) == datetime.date(2026, 7, 5)


def test_ignores_surrounding_whitespace():
    assert parse_duty_date("  July 5  ", 2026) == datetime.date(2026, 7, 5)


def test_unparseable_date_returns_none():
    assert parse_duty_date("no date here", 2026) is None
    assert parse_duty_date("", 2026) is None


ROWS = [
    {
        "Duty Date": "July 4",
        "Day": "Saturday",
        "Date Text": "July 4",
        "Stern RAM A": "Alice A",
        "Stern RAM B": "Bob B",
        "Stern ARD": "Cara C",
        "RD": "Dan D",
    },
    {
        "Duty Date": "July 5",
        "Day": "Sunday",
        "Date Text": "July 5",
        "Stern RAM A": "Simran Kaur",
        "Stern RAM B": "Stedmon Searcie",
        "Stern ARD": "Natalie Villanueva",
        "RD": "Anica Terbijhe",
    },
]


def test_finds_row_matching_target_date():
    row = find_duty_row(ROWS, datetime.date(2026, 7, 5), 2026)
    assert row is not None
    assert row["RD"] == "Anica Terbijhe"


def test_returns_none_when_no_row_matches():
    assert find_duty_row(ROWS, datetime.date(2026, 12, 25), 2026) is None


def test_skips_rows_with_unparseable_dates():
    rows = [{"Duty Date": "TBD"}, *ROWS]
    row = find_duty_row(rows, datetime.date(2026, 7, 4), 2026)
    assert row is not None
    assert row["RD"] == "Dan D"


def test_missing_fields_empty_when_row_complete():
    assert missing_fields(ROWS[1]) == []


def test_missing_fields_reports_blank_required_columns():
    row = dict(ROWS[1], RD="", **{"Stern RAM A": "  "})
    assert missing_fields(row) == ["Stern RAM A", "RD"]
