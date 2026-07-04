from duty_bot.sheets import _normalize_row


def test_normalizes_messy_live_headers():
    raw = {
        "Duty Date ": "July 5",
        "Bowles RAM A\n(Duty Phone/Transport)": "Ignore Me",
        "Stern RAM A\n(Duty Phone/Transport)": "Simran Kaur",
        "Stern RAM B (Rounds/Backup)": "Stedmon Searcie",
        "Bowles ARD \n(Holds Duty Phone)": "Ignore Me",
        "Stern ARD\n(Holds Duty Phone)": "Natalie Villanueva",
        "RD\n(Stern/Bowles)": "Anica Terbijhe",
        "Name": "Someone",
    }
    assert _normalize_row(raw) == {
        "Duty Date": "July 5",
        "Stern RAM A": "Simran Kaur",
        "Stern RAM B": "Stedmon Searcie",
        "Stern ARD": "Natalie Villanueva",
        "RD": "Anica Terbijhe",
    }


def test_bowles_columns_do_not_leak_into_stern_fields():
    raw = {
        "Bowles RAM A\n(Duty Phone/Transport)": "Bowles Person",
        "Bowles ARD \n(Holds Duty Phone)": "Bowles ARD Person",
    }
    assert _normalize_row(raw) == {}
