# Failure Alerting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** DM a Slack alert webhook whenever a daily bot run fails, and convert the missing-token-file hang into a loud, alerted failure.

**Architecture:** Add an optional `SLACK_ALERT_WEBHOOK_URL` config value and a `send_alert()` helper that no-ops when unset and never raises. Wire `send_alert()` into every error-exit path in `__main__.py`, plus a new pre-flight guard that checks the OAuth token file exists before touching Google.

**Tech Stack:** Python 3.13, `requests`, `pytest`, `python-dotenv`, `gspread`.

## Global Constraints

- Alerting must NEVER raise or crash the bot, and must never mask the underlying failure.
- Alert only on error exits (`return 1`). Do NOT alert on benign exits: already-posted skip, no-row-for-today, or success.
- Empty/unset `SLACK_ALERT_WEBHOOK_URL` disables alerting (no HTTP call).
- Follow existing test style in `tests/test_main.py`: monkeypatch names on `duty_bot.__main__` (e.g. `fetch_rows`, `post_message`, `send_alert`), isolate cwd via `tmp_path`.
- Alert message copy uses the exact strings in this plan (leading `⚠️ Stern duty bot: ...`).

---

### Task 1: Config value + env docs

**Files:**
- Modify: `duty_bot/config.py` (add field to `Config` dataclass + `load_config`)
- Modify: `.env.example` (document the new var)
- Test: `tests/test_config.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `Config.slack_alert_webhook_url: str` — empty string when unset.

- [ ] **Step 1: Write the failing test**

Create `tests/test_config.py`:

```python
from duty_bot.config import load_config


def test_alert_webhook_defaults_to_empty(monkeypatch):
    monkeypatch.delenv("SLACK_ALERT_WEBHOOK_URL", raising=False)
    assert load_config().slack_alert_webhook_url == ""


def test_alert_webhook_read_from_env(monkeypatch):
    monkeypatch.setenv("SLACK_ALERT_WEBHOOK_URL", "https://hooks.slack.example/alert")
    assert load_config().slack_alert_webhook_url == "https://hooks.slack.example/alert"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `TypeError` (unexpected/ missing `slack_alert_webhook_url`) or `AttributeError`.

- [ ] **Step 3: Write minimal implementation**

In `duty_bot/config.py`, add the field to the `Config` dataclass (after `slack_webhook_url`):

```python
    slack_webhook_url: str
    slack_alert_webhook_url: str
```

And in `load_config()`'s `Config(...)` call, add (after the `slack_webhook_url=` line):

```python
        slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL", ""),
        slack_alert_webhook_url=os.getenv("SLACK_ALERT_WEBHOOK_URL", ""),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Document the var in `.env.example`**

Append to `.env.example` (after the `SLACK_WEBHOOK_URL=` line):

```
# Slack incoming webhook for failure alerts (DMs the operator). Optional; leave
# blank to disable alerting.
SLACK_ALERT_WEBHOOK_URL=
```

- [ ] **Step 6: Run the full suite to confirm nothing else broke**

Run: `python -m pytest -q`
Expected: PASS (all existing tests + 2 new).

- [ ] **Step 7: Commit**

```bash
git add duty_bot/config.py .env.example tests/test_config.py
git commit -m "Add optional SLACK_ALERT_WEBHOOK_URL config"
```

---

### Task 2: `send_alert` helper

**Files:**
- Modify: `duty_bot/slack.py` (add `send_alert`)
- Test: `tests/test_slack.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `send_alert(webhook_url: str, text: str) -> None` — no-ops on empty
  `webhook_url`; POSTs `{"text": text}` otherwise; catches and logs any
  exception so it never raises.

- [ ] **Step 1: Write the failing test**

Create `tests/test_slack.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_slack.py -v`
Expected: FAIL — `AttributeError: module 'duty_bot.slack' has no attribute 'send_alert'`.

- [ ] **Step 3: Write minimal implementation**

In `duty_bot/slack.py`, add at the top after `import requests`:

```python
import logging

logger = logging.getLogger("duty_bot")
```

And add this function at the end of the file:

```python
def send_alert(webhook_url, text):
    """Best-effort failure alert to a Slack webhook. Never raises.

    No-ops when webhook_url is empty. Any error posting the alert is logged and
    swallowed so alerting can never crash the bot or mask the real failure.
    """
    if not webhook_url:
        return
    try:
        response = requests.post(webhook_url, json={"text": text}, timeout=30)
        if response.status_code != 200:
            logger.warning(
                "Alert webhook returned status=%s body=%s",
                response.status_code,
                response.text,
            )
    except Exception as error:  # noqa: BLE001 - alerting must never raise
        logger.warning("Failed to send alert: %s", error)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_slack.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add duty_bot/slack.py tests/test_slack.py
git commit -m "Add send_alert helper that never raises"
```

---

### Task 3: Wire alerts + pre-flight token guard into main

**Files:**
- Modify: `duty_bot/__main__.py` (import `send_alert`, add guard + alert calls)
- Modify: `tests/test_main.py` (fixture creates token file; add alert assertions + new tests)

**Interfaces:**
- Consumes: `Config.slack_alert_webhook_url` (Task 1); `send_alert` (Task 2).
- Produces: no new public interface.

- [ ] **Step 1: Update the `posts` fixture so existing tests pass the new guard**

The pre-flight guard (added in Step 5) requires the OAuth token file to exist.
Update the `posts` fixture in `tests/test_main.py` to create it and to capture
alerts. Replace the fixture body's setup with these additions.

After the `config` dir creation block, add a token file:

```python
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "authorized_user.json").write_text('{"refresh_token": "x"}')
```

After the `post_message` monkeypatch line, capture alerts and return both lists:

```python
    monkeypatch.setattr(main_mod, "post_message", lambda url, text: sent.append(text))
    alerts = []
    monkeypatch.setattr(main_mod, "send_alert", lambda url, text: alerts.append(text))
    return sent, alerts
```

Every existing test currently binds `posts` as the sent-list. Update each test
signature that uses it to unpack, e.g. change `def test_x(posts, ...):` bodies
that reference `posts` to first do `sent, alerts = posts`. Concretely, in each
existing test replace uses of `posts` with `sent` and add `sent, alerts = posts`
as the first line. For the assertions that read `posts == [...]` or
`len(posts)`, use `sent` instead.

- [ ] **Step 2: Add the new failing tests**

Append to `tests/test_main.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL — new alert tests fail (`send_alert` not imported / not called;
no guard); pre-existing tests may error until the fixture unpacking in Step 1 is
applied. Confirm the failures are about missing alert calls / guard, not syntax.

- [ ] **Step 4: Import send_alert into main**

In `duty_bot/__main__.py`, update the slack import (line 10):

```python
from duty_bot.slack import format_message, post_message, send_alert
```

- [ ] **Step 5: Add the pre-flight token guard**

In `duty_bot/__main__.py`, after `config = load_config()` and the `target_date`
block, before the `if not args.force and not args.dry_run:` block, add:

```python
    token_path = config.oauth_token_path
    if not args.dry_run and (
        not os.path.exists(token_path) or os.path.getsize(token_path) == 0
    ):
        message = (
            f"⚠️ Stern duty bot: OAuth token file missing or empty at {token_path}; "
            "run the interactive login to refresh it."
        )
        logger.error(message)
        send_alert(config.slack_alert_webhook_url, message)
        return 1
```

Add `import os` to the imports at the top of the file (alphabetically near
`import logging`).

- [ ] **Step 6: Add alert calls at the three error exits**

In the `fetch_rows` except block, change it to:

```python
    try:
        rows = fetch_rows(config)
    except Exception as error:
        message = f"⚠️ Stern duty bot: failed to read Google Sheet — {error}"
        logger.error(message)
        send_alert(config.slack_alert_webhook_url, message)
        return 1
```

In the `missing` block, change it to:

```python
    missing = missing_fields(row)
    if missing:
        message = (
            f"⚠️ Stern duty bot: duty row for {target_date} missing required "
            f"fields: {', '.join(missing)}"
        )
        logger.error(message)
        send_alert(config.slack_alert_webhook_url, message)
        return 1
```

In the `post_message` except block, change it to:

```python
    try:
        post_message(config.slack_webhook_url, text)
    except RuntimeError as error:
        message = f"⚠️ Stern duty bot: failed to post to Slack — {error}"
        logger.error(message)
        send_alert(config.slack_alert_webhook_url, message)
        return 1
```

Note: the `SLACK_WEBHOOK_URL is not set` branch (`return 1`) may also alert for
completeness — add the same two-line pattern there:

```python
    if not config.slack_webhook_url:
        message = "⚠️ Stern duty bot: SLACK_WEBHOOK_URL is not set."
        logger.error(message)
        send_alert(config.slack_alert_webhook_url, message)
        return 1
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m pytest tests/test_main.py -v`
Expected: PASS (all existing + 6 new).

- [ ] **Step 8: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS (everything green).

- [ ] **Step 9: Commit**

```bash
git add duty_bot/__main__.py tests/test_main.py
git commit -m "Alert on all failure paths and guard missing token file"
```

---

## Self-Review

**Spec coverage:**
- Config `slack_alert_webhook_url` → Task 1. ✓
- `send_alert` no-op/never-raise → Task 2. ✓
- Alerts on all 3 error exits → Task 3 Step 6. ✓
- Pre-flight token guard → Task 3 Step 5. ✓
- `.env.example` doc → Task 1 Step 5. ✓
- Tests for every alert path + no-alert-on-benign + no-op/swallow → Tasks 2 & 3. ✓

**Placeholder scan:** none — every step shows concrete code/commands.

**Type consistency:** `send_alert(webhook_url, text)` signature identical in Task 2
definition, Task 3 import, and all monkeypatch/call sites. `slack_alert_webhook_url`
field name consistent across config, main, and tests.
