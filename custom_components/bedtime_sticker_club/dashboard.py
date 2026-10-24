"""Build the bundled Lovelace view from active family profiles."""

from pathlib import Path
import os
import tempfile

import yaml

from .const import TITLE


def dashboard_config(profiles):
    """Return a sections dashboard with one child card per active profile."""
    return {
        "title": TITLE,
        "views": [
            {
                "title": "Sticker Club",
                "path": "tonight",
                "icon": "mdi:star-face",
                "type": "sections",
                "max_columns": 3,
                "background": "#fff4da",
                "header": {
                    "layout": "responsive",
                    "badges_position": "bottom",
                    "card": {"type": "custom:bedtime-sticker-header"},
                },
                "sections": [
                    {
                        "type": "grid",
                        "cards": [{
                            "type": "custom:bedtime-sticker-child-card",
                            "child_id": profile["id"],
                            "routine": "auto",
                            "size": "inherit",
                            "calendar": "collapsible",
                            "grid_options": {"columns": "full"},
                        }],
                    }
                    for profile in profiles
                    if profile["active"]
                ],
            },
            {
                "title": "Parent Controls",
                "path": "parents",
                "icon": "mdi:cog-outline",
                "subview": True,
                "cards": [{"type": "custom:bedtime-sticker-parent-controls"}],
            },
        ],
    }


def write_dashboard(path: str | Path, profiles) -> None:
    """Atomically write the integration-managed dashboard in the config dir."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = yaml.safe_dump(dashboard_config(profiles), allow_unicode=True, sort_keys=False)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent,
            suffix=".yaml", delete=False,
        ) as temp:
            temp_path = Path(temp.name)
            temp.write(content)
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(temp_path, destination)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
