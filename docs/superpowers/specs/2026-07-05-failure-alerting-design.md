# Failure Alerting for Stern Duty Bot

**Date:** 2026-07-05
**Status:** Approved design, pending spec review

## Problem

The bot runs headless via cron at 09:00 daily (`0 9 * * * ... python -m duty_bot`).
When a run fails it logs to `logs/cron.log` and exits non-zero, but nobody is
watching that log. Failures are therefore effectively silent. The operator wants
a Slack DM whenever a run fails.

## Goal

On any error exit, post a descriptive message to a separate Slack incoming
webhook (an existing webhook that DMs the operator). Alerting must never crash
the bot or mask the underlying failure.

## Scope

In scope — alert on every error-exit path:
1. Google Sheets read failure (`__main__.py`, currently the `except Exception`
   around `fetch_rows`). This is also the path that catches OAuth `RefreshError`
   (expired/revoked refresh token), so auth failures are covered here.
2. Duty row missing required fields.
3. Slack post to the main duty channel failing.

Also in scope — a new pre-flight guard:
4. Before any Google call, verify the OAuth token file
   (`secrets/authorized_user.json`, i.e. `config.oauth_token_path`) exists and is
   non-empty. If not, alert and exit 1 rather than letting `gspread.oauth` fall
   into its interactive browser flow, which would hang forever under cron.

Out of scope (benign, non-error exits — no alert):
- "Already posted for <date>; skipping."
- "No duty row found for today."
- Successful posts.

## Auth-failure analysis (context for why this design is sufficient)

- `gspread.oauth` only launches the interactive browser flow when the token file
  is **missing**; when it exists, credentials load and refresh happens on-demand
  during the Sheets request.
- An invalid/expired refresh token raises `google.auth.exceptions.RefreshError`
  during the request, which propagates out of `fetch_rows` and is caught by the
  existing `except Exception`. So auth failures reach an alertable path — they do
  not hang.
- The app is Internal to a Workspace org, so the 7-day refresh-token expiry
  (External + Testing only) does not apply. Remaining auth risks (password
  change, admin revocation, 6-month inactivity, authorizing account leaving the
  org) are rare and all raise → alertable.
- The only silent-hang case is a missing/corrupt token file → addressed by the
  pre-flight guard (item 4).

## Design

### Config (`duty_bot/config.py`)
- Add `slack_alert_webhook_url: str` to the `Config` dataclass.
- Load from `os.getenv("SLACK_ALERT_WEBHOOK_URL", "")`. Optional; empty disables
  alerting.

### Alert helper (`duty_bot/slack.py`)
- Add `send_alert(webhook_url, text)`:
  - No-op (return immediately) when `webhook_url` is empty/falsy.
  - Otherwise POST `{"text": text}` to the webhook, mirroring `post_message`.
  - Wrap the POST in `try/except Exception`; on failure, log a warning and
    swallow it. Alerting must never raise — a failing alert must not crash the
    bot or obscure the real error.

### Wiring (`duty_bot/__main__.py`)
- Pre-flight guard: after `load_config()` and before `fetch_rows`, check that the
  token file exists and is non-empty. On failure, `send_alert(...)` with a clear
  message and `return 1`.
- At each of the three existing `return 1` error points, call
  `send_alert(config.slack_alert_webhook_url, <message>)` immediately before
  returning.
- Message format names the stage and includes the error text, e.g.:
  - `⚠️ Stern duty bot: failed to read Google Sheet — <error>`
  - `⚠️ Stern duty bot: duty row for <date> missing required fields: <fields>`
  - `⚠️ Stern duty bot: failed to post to Slack — <error>`
  - `⚠️ Stern duty bot: OAuth token file missing or empty at <path>; run the interactive login to refresh it.`

### Env docs
- Add `SLACK_ALERT_WEBHOOK_URL=` to `.env.example` with a short comment
  describing it as the webhook for failure DMs.

## Testing (`tests/test_main.py`, `tests/test_message_format.py` as fitting)

- Alert fires on the Sheets-read failure path (mock `fetch_rows` to raise;
  assert `send_alert`/webhook POST called with a message containing the error).
- Alert fires on missing-required-fields path.
- Alert fires on Slack-post failure path.
- Alert fires on the pre-flight missing-token-file path (and Google is never
  touched).
- No alert on success, on already-posted skip, or on no-row-today.
- `send_alert` is a no-op when the webhook URL is empty (no HTTP call).
- `send_alert` swallows a POST exception without raising.

## Non-goals / YAGNI
- No retries, batching, rate-limiting, or alert deduplication.
- No alerting on benign skips or successes.
- No change to the primary posting behavior or the Google auth flow itself.
