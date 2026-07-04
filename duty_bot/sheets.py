import gspread

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# The live sheet's headers carry trailing spaces, embedded newlines, and
# parenthetical notes (e.g. "Stern RAM A\n(Duty Phone/Transport)"). Map those
# onto the clean names the rest of the code expects by matching their prefix.
CANONICAL_COLUMNS = ["Duty Date", "Stern RAM A", "Stern RAM B", "Stern ARD", "RD"]


def _canonicalize(header):
    """Return the canonical column name for a raw header, or None."""
    collapsed = " ".join(str(header).split())
    for canonical in CANONICAL_COLUMNS:
        if collapsed == canonical or collapsed.startswith((canonical + " ", canonical + "(")):
            return canonical
    return None


def _normalize_row(row):
    normalized = {}
    for raw_key, value in row.items():
        canonical = _canonicalize(raw_key)
        if canonical is not None:
            normalized.setdefault(canonical, value)
    return normalized


def _build_client(config):
    """Authorize a gspread client using OAuth user credentials.

    The bot acts as a real account that can already open the sheet, which is
    necessary when the sheet's Workspace blocks sharing outside its domain. The
    first run performs a browser login and caches a token for later runs.
    """
    return gspread.oauth(
        scopes=SCOPES,
        credentials_filename=config.oauth_client_path,
        authorized_user_filename=config.oauth_token_path,
    )


def fetch_rows(config):
    """Read all rows from the duty rotation tab as a list of dicts."""
    client = _build_client(config)
    worksheet = client.open_by_key(config.sheet_id).worksheet(config.sheet_tab_name)
    return [_normalize_row(row) for row in worksheet.get_all_records()]
