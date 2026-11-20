#!/usr/bin/env python3
"""Sync changelog entries into the README, User Guide, and About page."""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"
README = ROOT / "README.md"
USER_GUIDE = ROOT / "src" / "TemCompanion" / "docs" / "User Guide.md"
ABOUT = ROOT / "src" / "TemCompanion" / "docs" / "about.md"

START_MARKER = "<!-- CHANGELOG_SNIPPET_START -->"
END_MARKER = "<!-- CHANGELOG_SNIPPET_END -->"


def extract_latest_versions(changelog_text: str, max_versions: int = 3) -> str:
    parts = re.split(r"^### ", changelog_text, flags=re.MULTILINE)
    if len(parts) <= 1:
        raise ValueError("No version sections found in CHANGELOG.md")

    entries: list[str] = []
    for raw in parts[1:]:
        entry = "### " + raw.strip()
        entries.append(entry)
        if len(entries) >= max_versions:
            break

    return "\n\n".join(entries).strip() + "\n"


def replace_between_markers(text: str, replacement: str) -> str:
    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        flags=re.DOTALL,
    )
    new_block = f"{START_MARKER}\n\n{replacement}\n{END_MARKER}"
    if not pattern.search(text):
        raise ValueError("Markers not found in target file")
    return pattern.sub(new_block, text, count=1)


def main() -> int:
    changelog_text = CHANGELOG.read_text(encoding="utf-8")
    for target, max_versions in ((README, 1000), (USER_GUIDE, 1000), (ABOUT, 3)):
        latest = extract_latest_versions(changelog_text, max_versions=max_versions)
        original = target.read_text(encoding="utf-8")
        updated = replace_between_markers(original, latest)
        target.write_text(updated, encoding="utf-8")

    print("Synced changelog entries into README, User Guide, and About page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
