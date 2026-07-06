from duty_bot.config import load_config


def test_alert_webhook_defaults_to_empty(monkeypatch):
    monkeypatch.delenv("SLACK_ALERT_WEBHOOK_URL", raising=False)
    assert load_config().slack_alert_webhook_url == ""


def test_alert_webhook_read_from_env(monkeypatch):
    monkeypatch.setenv("SLACK_ALERT_WEBHOOK_URL", "https://hooks.slack.example/alert")
    assert load_config().slack_alert_webhook_url == "https://hooks.slack.example/alert"
