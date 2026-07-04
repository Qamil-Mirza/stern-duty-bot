from duty_bot.state import load_last_posted, save_last_posted


def test_missing_state_file_returns_none(tmp_path):
    assert load_last_posted(tmp_path / "last_posted.json") is None


def test_round_trips_last_posted_date(tmp_path):
    path = tmp_path / "data" / "last_posted.json"
    save_last_posted(path, "2026-07-05")
    assert load_last_posted(path) == "2026-07-05"
