import logging

import requests

logger = logging.getLogger("duty_bot")


def format_message(day, date_text, rd, ard, ram_a, ram_b):
    return (
        f"Duty Rotation {day}, {date_text}\n"
        "\n"
        f"RD: {rd}\n"
        f"ARD: {ard}\n"
        f"RAM A (phone/transport): {ram_a}\n"
        f"RAM B (rounds/backup): {ram_b}"
    )


def post_message(webhook_url, text):
    """Post to the Slack incoming webhook. Raises RuntimeError on failure."""
    response = requests.post(webhook_url, json={"text": text}, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(
            f"Slack post failed: status={response.status_code} body={response.text}"
        )


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
