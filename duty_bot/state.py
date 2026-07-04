import json
from pathlib import Path


def load_last_posted(path):
    """Return the last posted date string, or None if never posted."""
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text()).get("last_posted_date")


def save_last_posted(path, date_str):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"last_posted_date": date_str}, indent=2) + "\n")
