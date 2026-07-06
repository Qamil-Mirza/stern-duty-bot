import duty_bot.slack as slack


def test_send_alert_noop_when_url_empty(monkeypatch):
    calls = []
    monkeypatch.setattr(slack.requests, "post", lambda *a, **k: calls.append(a))
    slack.send_alert("", "anything")
    assert calls == []


def test_send_alert_posts_text(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json

        class R:
            status_code = 200

        return R()

    monkeypatch.setattr(slack.requests, "post", fake_post)
    slack.send_alert("https://hooks.slack.example/alert", "boom")
    assert captured["url"] == "https://hooks.slack.example/alert"
    assert captured["json"] == {"text": "boom"}


def test_send_alert_swallows_exceptions(monkeypatch):
    def fake_post(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(slack.requests, "post", fake_post)
    # Must not raise.
    slack.send_alert("https://hooks.slack.example/alert", "boom")
