"""Validate the HACS payload and its public script/entity contracts."""

import argparse
import ast
import json
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/bedtime_sticker_club"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="Release tag, e.g. v1.0.0")
    args = parser.parse_args()

    hacs = json.loads((ROOT / "hacs.json").read_text())
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    assert hacs["name"] == manifest["name"] == "Bedtime Sticker Club"
    assert hacs["homeassistant"] == "2026.10.0"
    assert manifest["domain"] == COMPONENT.name
    assert set(manifest) >= {
        "domain", "name", "version", "documentation", "issue_tracker", "codeowners"
    }
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
    assert manifest["dependencies"] == ["lovelace"]
    if args.tag:
        assert args.tag == f"v{manifest['version']}", "Tag and manifest version differ"

    for path in COMPONENT.rglob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
    assert (COMPONENT / "brand/icon.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    assert manifest["config_flow"] is True
    for filename in ("config_flow.py", "coordinator.py", "sensor.py", "time.py", "services.yaml", "strings.json", "translations/en.json", "frontend/bedtime-sticker-club.js"):
        assert (COMPONENT / filename).is_file(), filename
    strings = json.loads((COMPONENT / "strings.json").read_text())
    assert strings == json.loads((COMPONENT / "translations/en.json").read_text())
    dashboard = yaml.safe_load((COMPONENT / "dashboard.yaml").read_text())
    assert set(yaml.safe_load((COMPONENT / "services.yaml").read_text())) == {
        "set_task", "choose_sticker", "set_avatar"
    }
    assert set(card["type"] for view in dashboard["views"]
               for section in view.get("sections", [])
               for card in section.get("cards", [])) <= {"custom:bedtime-sticker-family"}
    assert "button_card_templates" not in dashboard
    assert [view["path"] for view in dashboard["views"]] == ["tonight", "parents"]
    assert dashboard["views"][0]["sections"][0]["cards"][0]["type"] == "custom:bedtime-sticker-family"
    assert "type: custom:bedtime-sticker-parent-controls" in (COMPONENT / "dashboard.yaml").read_text()
    print(f"HACS payload validated: {manifest['domain']} {manifest['version']}")


if __name__ == "__main__":
    main()
