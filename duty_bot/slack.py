import requests


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
