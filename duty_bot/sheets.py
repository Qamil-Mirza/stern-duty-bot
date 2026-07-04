import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def fetch_rows(config):
    """Read all rows from the duty rotation tab as a list of dicts."""
    credentials = Credentials.from_service_account_file(
        config.service_account_path, scopes=SCOPES
    )
    client = gspread.authorize(credentials)
    worksheet = client.open_by_key(config.sheet_id).worksheet(config.sheet_tab_name)
    return worksheet.get_all_records()
