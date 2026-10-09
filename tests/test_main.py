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
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "authorized_user.json").write_text('{"refresh_token": "x"}')
    monkeypatch.setattr(main_mod, "fetch_rows", lambda config: [ROW])
    sent = []
    monkeypatch.setattr(main_mod, "post_message", lambda url, text: sent.append(text))
    alerts = []
    monkeypatch.setattr(main_mod, "send_alert", lambda url, text: alerts.append(text))
    return sent, alerts


def read_state(tmp_path):
    path = tmp_path / "data" / "last_posted.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())["last_posted_date"]


def test_dry_run_prints_message_without_posting(posts, tmp_path, capsys):
    sent, alerts = posts
    assert main_mod.main(["--dry-run", "--date", "2026-07-05"]) == 0
    assert EXPECTED_MESSAGE in capsys.readouterr().out
    assert sent == []
    assert read_state(tmp_path) is None


def test_posts_message_and_records_state(posts, tmp_path):
    sent, alerts = posts
    assert main_mod.main(["--date", "2026-07-05"]) == 0
    assert sent == [EXPECTED_MESSAGE]
    assert read_state(tmp_path) == "2026-07-05"


def test_ram_a_override_replaces_only_ram_a(posts):
    sent, alerts = posts
    assert main_mod.main(["--date", "2026-07-05", "--ram-a", "Stedmon Searcie"]) == 0
    assert sent == [
        "Duty Rotation Sunday, July 5\n"
        "\n"
        "RD: <@URD>\n"
        "ARD: <@UARD>\n"
        "RAM A (phone/transport): <@URAMB>\n"
        "RAM B (rounds/backup): <@URAMB>"
    ]


def test_override_can_fill_a_missing_field(posts, monkeypatch):
    sent, alerts = posts
    incomplete = dict(ROW, RD="")
    monkeypatch.setattr(main_mod, "fetch_rows", lambda config: [incomplete])
    assert main_mod.main(["--date", "2026-07-05", "--rd", "Anica Terbijhe"]) == 0
    assert sent == [EXPECTED_MESSAGE]
    assert alerts == []


def test_override_does_not_mutate_shared_row(posts):
    sent, alerts = posts
    main_mod.main(["--date", "2026-07-05", "--ram-a", "Stedmon Searcie"])
    assert ROW["Stern RAM A"] == "Simran Kaur"


def test_skips_duplicate_post_for_same_date(posts):
    sent, alerts = posts
    main_mod.main(["--date", "2026-07-05"])
    assert main_mod.main(["--date", "2026-07-05"]) == 0
    assert len(sent) == 1


def test_force_reposts_same_date(posts):
    sent, alerts = posts
    main_mod.main(["--date", "2026-07-05"])
    assert main_mod.main(["--date", "2026-07-05", "--force"]) == 0
    assert len(sent) == 2


def test_no_matching_row_exits_normally_without_posting(posts):
    sent, alerts = posts
    assert main_mod.main(["--date", "2026-12-25"]) == 0
    assert sent == []


def test_missing_required_field_errors_without_posting(posts, monkeypatch):
    sent, alerts = posts
    incomplete = dict(ROW, RD="")
    monkeypatch.setattr(main_mod, "fetch_rows", lambda config: [incomplete])
    assert main_mod.main(["--date", "2026-07-05"]) == 1
    assert sent == []


def test_sheet_read_failure_exits_with_error(posts, monkeypatch):
    sent, alerts = posts

    def boom(config):
        raise RuntimeError("sheet unavailable")

    monkeypatch.setattr(main_mod, "fetch_rows", boom)
    assert main_mod.main(["--date", "2026-07-05"]) == 1
    assert sent == []


def test_slack_failure_exits_with_error_and_keeps_state_clean(tmp_path, posts, monkeypatch):
    sent, alerts = posts

    def boom(url, text):
        raise RuntimeError("Slack post failed: status=500 body=oops")

    monkeypatch.setattr(main_mod, "post_message", boom)
    assert main_mod.main(["--date", "2026-07-05"]) == 1
    assert read_state(tmp_path) is None


def test_alert_on_sheet_read_failure(posts, monkeypatch):
    sent, alerts = posts

    def boom(config):
        raise RuntimeError("sheet unavailable")

    monkeypatch.setattr(main_mod, "fetch_rows", boom)
    assert main_mod.main(["--date", "2026-07-05"]) == 1
    assert len(alerts) == 1
    assert "sheet unavailable" in alerts[0]


def test_alert_on_missing_required_field(posts, monkeypatch):
    sent, alerts = posts
    incomplete = dict(ROW, RD="")
    monkeypatch.setattr(main_mod, "fetch_rows", lambda config: [incomplete])
    assert main_mod.main(["--date", "2026-07-05"]) == 1
    assert len(alerts) == 1
    assert "missing required fields" in alerts[0]


def test_alert_on_slack_failure(posts, monkeypatch):
    sent, alerts = posts

    def boom(url, text):
        raise RuntimeError("Slack post failed: status=500 body=oops")

    monkeypatch.setattr(main_mod, "post_message", boom)
    assert main_mod.main(["--date", "2026-07-05"]) == 1
    assert len(alerts) == 1
    assert "failed to post to Slack" in alerts[0]


def test_alert_on_missing_token_file(posts, tmp_path, monkeypatch):
    sent, alerts = posts
    called = []
    monkeypatch.setattr(main_mod, "fetch_rows", lambda config: called.append(1) or [])
    (tmp_path / "secrets" / "authorized_user.json").unlink()
    assert main_mod.main(["--date", "2026-07-05"]) == 1
    assert called == []  # Google was never touched
    assert len(alerts) == 1
    assert "token file" in alerts[0]


def test_no_alert_on_success(posts):
    sent, alerts = posts
    assert main_mod.main(["--date", "2026-07-05"]) == 0
    assert alerts == []


def test_no_alert_on_no_row(posts):
    sent, alerts = posts
    assert main_mod.main(["--date", "2026-12-25"]) == 0
    assert alerts == []


def test_alert_on_unexpected_exception(posts, monkeypatch):
    sent, alerts = posts

    def boom(path):
        raise ValueError("corrupt state file")

    monkeypatch.setattr(main_mod, "load_last_posted", boom)
    assert main_mod.main(["--date", "2026-07-05"]) == 1
    assert len(alerts) == 1
    assert "unexpected error" in alerts[0]
    assert "corrupt state file" in alerts[0]
