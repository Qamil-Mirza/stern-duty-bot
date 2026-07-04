import datetime
import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Config:
    sheet_id: str
    sheet_tab_name: str
    service_account_path: str
    timezone: str
    duty_year: int
    slack_webhook_url: str


def load_config():
    load_dotenv()
    return Config(
        sheet_id=os.getenv("GOOGLE_SHEET_ID", ""),
        sheet_tab_name=os.getenv("GOOGLE_SHEET_TAB_NAME", "Staff Duty Rotation"),
        service_account_path=os.getenv(
            "GOOGLE_SERVICE_ACCOUNT_JSON", "secrets/google-service-account.json"
        ),
        timezone=os.getenv("TIMEZONE", "America/Los_Angeles"),
        duty_year=int(os.getenv("DUTY_YEAR", str(datetime.date.today().year))),
        slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL", ""),
    )
