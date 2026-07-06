import argparse
import datetime
import logging
import os
import sys
from zoneinfo import ZoneInfo

from duty_bot.config import load_config
from duty_bot.parser import find_duty_row, missing_fields
from duty_bot.sheets import fetch_rows
from duty_bot.slack import format_message, post_message, send_alert
from duty_bot.staff_directory import load_staff_directory, resolve_mention
from duty_bot.state import load_last_posted, save_last_posted

STAFF_DIRECTORY_PATH = "config/staff_directory.yml"
STATE_PATH = "data/last_posted.json"

logger = logging.getLogger("duty_bot")


def main(argv=None):
    arg_parser = argparse.ArgumentParser(
        prog="duty_bot", description="Post the Stern duty rotation to Slack."
    )
    arg_parser.add_argument("--date", help="Run for this date (YYYY-MM-DD) instead of today.")
    arg_parser.add_argument(
        "--dry-run", action="store_true", help="Print the message without posting."
    )
    arg_parser.add_argument(
        "--force", action="store_true", help="Post even if already posted for this date."
    )
    args = arg_parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = load_config()

    try:
        return _run(config, args)
    except Exception as error:
        message = f"⚠️ Stern duty bot: unexpected error — {error}"
        logger.error(message)
        send_alert(config.slack_alert_webhook_url, message)
        return 1


def _run(config, args):
    if args.date:
        target_date = datetime.date.fromisoformat(args.date)
    else:
        target_date = datetime.datetime.now(ZoneInfo(config.timezone)).date()

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

    if not args.force and not args.dry_run:
        if load_last_posted(STATE_PATH) == target_date.isoformat():
            logger.info("Already posted for %s; skipping (use --force to repost).", target_date)
            return 0

    try:
        rows = fetch_rows(config)
    except Exception as error:
        message = f"⚠️ Stern duty bot: failed to read Google Sheet — {error}"
        logger.error(message)
        send_alert(config.slack_alert_webhook_url, message)
        return 1

    row = find_duty_row(rows, target_date, config.duty_year)
    if row is None:
        logger.info("No duty row found for today.")
        return 0

    missing = missing_fields(row)
    if missing:
        message = (
            f"⚠️ Stern duty bot: duty row for {target_date} missing required "
            f"fields: {', '.join(missing)}"
        )
        logger.error(message)
        send_alert(config.slack_alert_webhook_url, message)
        return 1

    directory = load_staff_directory(STAFF_DIRECTORY_PATH)
    text = format_message(
        day=target_date.strftime("%A"),
        date_text=f"{target_date.strftime('%B')} {target_date.day}",
        rd=resolve_mention(directory, str(row["RD"]).strip()),
        ard=resolve_mention(directory, str(row["Stern ARD"]).strip()),
        ram_a=resolve_mention(directory, str(row["Stern RAM A"]).strip()),
        ram_b=resolve_mention(directory, str(row["Stern RAM B"]).strip()),
    )

    if args.dry_run:
        print(text)
        return 0

    if not config.slack_webhook_url:
        message = "⚠️ Stern duty bot: SLACK_WEBHOOK_URL is not set."
        logger.error(message)
        send_alert(config.slack_alert_webhook_url, message)
        return 1

    try:
        post_message(config.slack_webhook_url, text)
    except RuntimeError as error:
        message = f"⚠️ Stern duty bot: failed to post to Slack — {error}"
        logger.error(message)
        send_alert(config.slack_alert_webhook_url, message)
        return 1

    save_last_posted(STATE_PATH, target_date.isoformat())
    logger.info("Posted duty rotation for %s.", target_date)
    return 0


if __name__ == "__main__":
    sys.exit(main())
