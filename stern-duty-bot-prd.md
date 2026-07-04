# PRD: Stern Duty Slack Bot

## 1. Purpose

Build a simple Dockerized script that reads the official Google Sheets duty rotation, finds the Stern duty staff for today's date, formats the message, and posts it to a Slack channel using an incoming webhook.

This replaces Slack Workflow Builder, since workflows are not free.

## 2. Scope

The bot should only handle the Stern duty rotation.

It should read these fields from the Google Sheet:

- Duty Date
- Day
- Date Text
- Stern RAM A
- Stern RAM B
- Stern ARD
- RD

It should post this Slack message format:

```text
Duty Rotation DAY, DATE

RD: @person
ARD: @person
RAM A (phone/transport): @person
RAM B (rounds/backup): @person
```

Example:

```text
Duty Rotation Sunday, July 5

RD: <@U123RD>
ARD: <@U456ARD>
RAM A (phone/transport): <@U789RAMA>
RAM B (rounds/backup): <@U999RAMB>
```

## 3. Non-Goals

Do not build:

- A web app
- A database
- A long-running server
- A Slack slash command
- A Google Sheet editor
- Multi-hall support
- Automatic Slack user lookup

Keep this as a small script that runs once, posts once, and exits.

## 4. Data Source

The bot reads directly from the official Google Sheet, not from a copied sheet.

Configuration should come from environment variables:

```bash
GOOGLE_SHEET_ID=...
GOOGLE_SHEET_TAB_NAME=Staff Duty Rotation
GOOGLE_OAUTH_CLIENT_JSON=/app/secrets/oauth_client.json
GOOGLE_OAUTH_TOKEN_JSON=/app/secrets/authorized_user.json
TIMEZONE=America/Los_Angeles
DUTY_YEAR=2026
SLACK_WEBHOOK_URL=...
```

The bot authenticates via OAuth as a user who can already open the sheet (needed because the sheet's Workspace blocks sharing with service-account addresses outside its domain). It requests read-only access only.

## 5. Expected Sheet Columns

The script should be configurable, but the columns it reads are:

```text
Duty Date | Stern RAM A | Stern RAM B | Stern ARD | RD
```

Example row:

```text
July 5 | Simran Kaur | Stedmon Searcie | Natalie Villanueva | Anica Terbijhe
```

Headers are matched by prefix, so the real sheet's trailing spaces and parenthetical notes (e.g. `Stern RAM A\n(Duty Phone/Transport)`, `RD\n(Stern/Bowles)`) are handled automatically. The weekday and displayed date are derived from `Duty Date`; there are no separate `Day`/`Date Text` columns. The original sheet also includes parallel Bowles columns — ignore them.

## 6. Date Matching

The bot should use today's date in the configured timezone.

Default timezone:

```text
America/Los_Angeles
```

The bot should find the row where `Duty Date` matches today's date.

The sheet may display dates like:

```text
July 5
```

Because the sheet may omit the year, the app should use:

```text
DUTY_YEAR=2026
```

For testing, the CLI should allow overriding the date:

```bash
python -m duty_bot --date 2026-07-05 --dry-run
```

## 7. Staff Mentions

Use a simple local YAML file to map names to Slack mentions.

Path:

```text
config/staff_directory.yml
```

Example:

```yaml
staff:
  "Qamil Mirza bin Abdullah": "<@U123456789>"
  "Simran Kaur": "<@U234567890>"
  "Stedmon Searcie": "<@U345678901>"
  "Natalie Villanueva": "<@U456789012>"
  "Anica Terbijhe": "<@U567890123>"
```

If a name is missing from the directory, use the raw name and log a warning. Do not fail the whole run.

## 8. Slack Posting

Use a Slack incoming webhook.

The webhook URL must be passed through:

```bash
SLACK_WEBHOOK_URL=...
```

Never commit the webhook URL.

Payload format:

```json
{
  "text": "Duty Rotation Sunday, July 5\n\nRD: <@U123>\nARD: <@U456>\nRAM A (phone/transport): <@U789>\nRAM B (rounds/backup): <@U999>"
}
```

## 9. CLI Requirements

The app should support:

```bash
python -m duty_bot
```

Runs for today's date and posts to Slack.

```bash
python -m duty_bot --dry-run
```

Prints the message but does not post.

```bash
python -m duty_bot --date 2026-07-05 --dry-run
```

Tests a specific date.

```bash
python -m duty_bot --date 2026-07-05 --force
```

Posts for a specific date even if it was already posted.

## 10. Duplicate Post Protection

Keep this simple.

Use a local state file:

```text
data/last_posted.json
```

Example:

```json
{
  "last_posted_date": "2026-07-05"
}
```

If the bot already posted for today's date, skip posting unless `--force` is provided.

Do not update the state file during `--dry-run`.

## 11. Error Handling

### No matching row

Log:

```text
No duty row found for today.
```

Do not post. Exit normally.

### Missing required field

If RD, ARD, RAM A, or RAM B is empty, log an error and do not post.

### Slack post fails

Log the status code and response body. Exit with error.

Do not update `last_posted.json`.

### Google Sheets read fails

Log the error and exit with error.

## 12. Docker Requirements

The container should run the script once and exit.

Use a lightweight Python image:

```dockerfile
FROM python:3.12-slim
```

Provide:

- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `README.md`

Example Docker Compose usage:

```bash
docker compose run --rm duty-bot --dry-run --date 2026-07-05
```

Example scheduled run with cron:

```cron
0 9 * * * cd /opt/stern-duty-bot && docker compose run --rm duty-bot >> logs/cron.log 2>&1
```

## 13. Suggested Repo Structure

```text
stern-duty-bot/
├── duty_bot/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py
│   ├── sheets.py
│   ├── parser.py
│   ├── slack.py
│   ├── staff_directory.py
│   └── state.py
├── config/
│   └── staff_directory.yml.example
├── data/
│   └── .gitkeep
├── secrets/
│   └── .gitkeep
├── tests/
│   ├── test_parser.py
│   └── test_message_format.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 14. Dependencies

Use simple Python libraries:

```text
gspread
google-auth
requests
PyYAML
python-dotenv
```

Optional for testing:

```text
pytest
```

## 15. Acceptance Criteria

The project is done when:

1. This works locally:

```bash
python -m duty_bot --dry-run --date 2026-07-05
```

2. It prints:

```text
Duty Rotation Sunday, July 5

RD: <@...>
ARD: <@...>
RAM A (phone/transport): <@...>
RAM B (rounds/backup): <@...>
```

3. This posts to Slack:

```bash
python -m duty_bot --force --date 2026-07-05
```

4. This works through Docker:

```bash
docker compose run --rm duty-bot --dry-run --date 2026-07-05
```

5. Duplicate posts are skipped unless `--force` is used.

6. The app reads from the original Google Sheet.

7. No secrets are committed to GitHub.

## 16. README Requirements

The README should explain:

- How to create a Slack incoming webhook
- How to set up Google OAuth credentials (Desktop app client) and do the one-time login
- How to configure `.env`
- How to fill `staff_directory.yml`
- How to run locally
- How to run with Docker
- How to schedule with cron
- How to test with `--dry-run`

## 17. Implementation Notes

Prioritize simplicity over abstraction.

A good first version can be:

1. Load config from env
2. Read all rows from Google Sheets
3. Find today's row
4. Resolve names using `staff_directory.yml`
5. Format message
6. Post to Slack
7. Save `last_posted.json`

Avoid adding features unless they are needed for the daily duty post.
