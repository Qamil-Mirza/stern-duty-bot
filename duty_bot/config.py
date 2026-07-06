import datetime
import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Config:
    sheet_id: str
    sheet_tab_name: str
    oauth_client_path: str
    oauth_token_path: str
    timezone: str
    duty_year: int
    slack_webhook_url: str
    slack_alert_webhook_url: str


def load_config():
    load_dotenv()
    return Config(
        sheet_id=os.getenv("GOOGLE_SHEET_ID", ""),
        sheet_tab_name=os.getenv("GOOGLE_SHEET_TAB_NAME", "Staff Duty Rotation"),
        oauth_client_path=os.getenv(
            "GOOGLE_OAUTH_CLIENT_JSON", "secrets/oauth_client.json"
        ),
        oauth_token_path=os.getenv(
            "GOOGLE_OAUTH_TOKEN_JSON", "secrets/authorized_user.json"
        ),
        timezone=os.getenv("TIMEZONE", "America/Los_Angeles"),
        duty_year=int(os.getenv("DUTY_YEAR", str(datetime.date.today().year))),
        slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL", ""),
        slack_alert_webhook_url=os.getenv("SLACK_ALERT_WEBHOOK_URL", ""),
    )
