# Stern Duty Bot

A small script that reads the Stern duty rotation from Google Sheets and posts today's duty staff to Slack. It runs once, posts once, and exits — meant to be scheduled with cron.

Example post:

```text
Duty Rotation Sunday, July 5

RD: @Anica Terbijhe
ARD: @Natalie Villanueva
RAM A (phone/transport): @Simran Kaur
RAM B (rounds/backup): @Stedmon Searcie
```

## Setup

### 1. Create a Slack incoming webhook

1. Go to <https://api.slack.com/apps> and create a new app (from scratch) in your workspace.
2. Under **Incoming Webhooks**, toggle it on and click **Add New Webhook to Workspace**.
3. Pick the channel the duty post should go to.
4. Copy the webhook URL (`https://hooks.slack.com/services/...`) — you'll put it in `.env`.

### 2. Set up Google authentication (OAuth)

The bot authenticates as *you*, so it can read sheets owned by an organization that blocks sharing outside its domain (e.g. a `berkeley.edu` sheet you can open but can't share with a bot email).

1. Go to <https://console.cloud.google.com/>, create (or pick) a project.
2. Enable the **Google Sheets API** for the project.
3. Configure the **OAuth consent screen**. To avoid refresh tokens expiring every 7 days, set the app's publishing status to **In production** (an Internal app within your org is ideal).
4. Under **APIs & Services → Credentials → Create Credentials → OAuth client ID**, choose application type **Desktop app**. Download the JSON.
5. Save it as `secrets/oauth_client.json`.
6. Run the bot once **locally** (`python -m duty_bot --dry-run`). A browser opens — log in with the account that can access the sheet and approve read-only access. This caches a token at `secrets/authorized_user.json`, which is reused on every future run (including in Docker). No sheet sharing needed.

The sheet tab is expected to have these columns (extra columns, including the parallel Bowles columns, are ignored):

```text
Duty Date | Stern RAM A | Stern RAM B | Stern ARD | RD
```

Column headers are matched by prefix, so trailing spaces and parenthetical notes in the real sheet (e.g. `Stern RAM A\n(Duty Phone/Transport)`, `RD\n(Stern/Bowles)`) are handled automatically. The `Duty Date` cell holds a value like `July 5`; the weekday and date shown in the post are derived from it (no separate `Day`/`Date Text` columns needed).

### 3. Configure `.env`

```bash
cp .env.example .env
```

Fill in `GOOGLE_SHEET_ID` (from the sheet URL), `SLACK_WEBHOOK_URL`, and `DUTY_YEAR` (the year to assume for sheet dates like "July 5" that omit it). Never commit `.env`.

### 4. Fill `config/staff_directory.yml`

```bash
cp config/staff_directory.yml.example config/staff_directory.yml
```

Map each staff name (exactly as written in the sheet) to their Slack mention. To get a member ID in Slack: open the person's profile → **...** → **Copy member ID**.

```yaml
staff:
  "Simran Kaur": "<@U234567890>"
```

If a name is missing from this file, the bot posts the raw name and logs a warning.

## Running locally

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Preview without posting
python -m duty_bot --dry-run

# Preview a specific date
python -m duty_bot --date 2026-07-05 --dry-run

# Post for today
python -m duty_bot

# Repost even if already posted today
python -m duty_bot --force
```

The bot remembers the last posted date in `data/last_posted.json` and skips duplicate posts unless `--force` is given. Dry runs never post or update state.

## Running with Docker

```bash
docker compose build

# Preview
docker compose run --rm duty-bot --dry-run --date 2026-07-05

# Post for today
docker compose run --rm duty-bot
```

## Scheduling with cron

Post every day at 9:00 AM:

```cron
0 9 * * * cd /opt/stern-duty-bot && docker compose run --rm duty-bot >> logs/cron.log 2>&1
```

Create the log directory first: `mkdir -p logs`. The duplicate-post protection makes it safe if cron ever fires twice.

## Testing

```bash
pip install pytest
python -m pytest
```

Use `--dry-run` (optionally with `--date YYYY-MM-DD`) to check the message against the real sheet without posting anything.
