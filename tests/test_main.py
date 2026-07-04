import json

import pytest

import duty_bot.__main__ as main_mod

ROW = {
    "Duty Date": "July 5",
    "Day": "Sunday",
    "Date Text": "July 5",
    "Stern RAM A": "Simran Kaur",
    "Stern RAM B": "Stedmon Searcie",
    "Stern ARD": "Natalie Villanueva",
    "RD": "Anica Terbijhe",
}

EXPECTED_MESSAGE = (
    "Duty Rotation Sunday, July 5\n"
    "\n"
    "RD: <@URD>\n"
    "ARD: <@UARD>\n"
    "RAM A (phone/transport): <@URAMA>\n"
    "RAM B (rounds/backup): <@URAMB>"
)


@pytest.fixture
def posts(tmp_path, monkeypatch):
    """Isolated cwd, env config, fake sheet, and captured Slack posts."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet123")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.example/abc")
    monkeypatch.setenv("DUTY_YEAR", "2026")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "staff_directory.yml").write_text(
        "staff:\n"
        '  "Anica Terbijhe": "<@URD>"\n'
        '  "Natalie Villanueva": "<@UARD>"\n'
        '  "Simran Kaur": "<@URAMA>"\n'
        '  "Stedmon Searcie": "<@URAMB>"\n'
    )
    monkeypatch.setattr(main_mod, "fetch_rows", lambda config: [ROW])
    sent = []
    monkeypatch.setattr(main_mod, "post_message", lambda url, text: sent.append(text))
    return sent


def read_state(tmp_path):
    path = tmp_path / "data" / "last_posted.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())["last_posted_date"]


def test_dry_run_prints_message_without_posting(posts, tmp_path, capsys):
    assert main_mod.main(["--dry-run", "--date", "2026-07-05"]) == 0
    assert EXPECTED_MESSAGE in capsys.readouterr().out
    assert posts == []
    assert read_state(tmp_path) is None


def test_posts_message_and_records_state(posts, tmp_path):
    assert main_mod.main(["--date", "2026-07-05"]) == 0
    assert posts == [EXPECTED_MESSAGE]
    assert read_state(tmp_path) == "2026-07-05"


def test_skips_duplicate_post_for_same_date(posts):
    main_mod.main(["--date", "2026-07-05"])
    assert main_mod.main(["--date", "2026-07-05"]) == 0
    assert len(posts) == 1


def test_force_reposts_same_date(posts):
    main_mod.main(["--date", "2026-07-05"])
    assert main_mod.main(["--date", "2026-07-05", "--force"]) == 0
    assert len(posts) == 2


def test_no_matching_row_exits_normally_without_posting(posts):
    assert main_mod.main(["--date", "2026-12-25"]) == 0
    assert posts == []


def test_missing_required_field_errors_without_posting(posts, monkeypatch):
    incomplete = dict(ROW, RD="")
    monkeypatch.setattr(main_mod, "fetch_rows", lambda config: [incomplete])
    assert main_mod.main(["--date", "2026-07-05"]) == 1
    assert posts == []


def test_sheet_read_failure_exits_with_error(posts, monkeypatch):
    def boom(config):
        raise RuntimeError("sheet unavailable")

    monkeypatch.setattr(main_mod, "fetch_rows", boom)
    assert main_mod.main(["--date", "2026-07-05"]) == 1
    assert posts == []


def test_slack_failure_exits_with_error_and_keeps_state_clean(tmp_path, posts, monkeypatch):
    def boom(url, text):
        raise RuntimeError("Slack post failed: status=500 body=oops")

    monkeypatch.setattr(main_mod, "post_message", boom)
    assert main_mod.main(["--date", "2026-07-05"]) == 1
    assert read_state(tmp_path) is None
