"""Build an installable archive containing custom_components/<domain>/."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/bedtime_sticker_club"


def main():
    output = ROOT / "dist/bedtime_sticker_club.zip"
    output.parent.mkdir(exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(COMPONENT.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                archive.write(path, path.relative_to(ROOT))
    print(output)


if __name__ == "__main__":
    main()
