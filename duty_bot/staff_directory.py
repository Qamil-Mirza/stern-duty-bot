import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def load_staff_directory(path):
    """Load the name -> Slack mention mapping from the YAML file."""
    path = Path(path)
    if not path.exists():
        logger.warning("Staff directory not found at %s; using raw names.", path)
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    return data.get("staff", {})


def resolve_mention(directory, name):
    """Return the Slack mention for a name, or the raw name with a warning."""
    mention = directory.get(name)
    if mention:
        return mention
    logger.warning("No Slack mention found for %r; using raw name.", name)
    return name
