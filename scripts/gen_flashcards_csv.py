#!/usr/bin/env python3
"""Export active flashcards to an editable CSV table.

Columns: id, category, front, back  (one row per active fc-NNNN.md).

Edit `front` / `back` (and optionally `category`) in a spreadsheet, save back
as CSV, then have the agent diff it against the .md files and apply changes.
The `id` column is the key and must not be altered.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACTIVE = ROOT / "data" / "flashcards" / "active"
OUT = ROOT / "flashcards_table.csv"

SECTION_PREFIX = "# "


def parse_md(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    fm: dict[str, str] = {}
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                line = line.strip()
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()
            body = text[end + 4:]

    sections: dict[str, list[str]] = {"Front": [], "Back": []}
    current = None
    for line in body.splitlines():
        if line.startswith(SECTION_PREFIX):
            current = line[len(SECTION_PREFIX):].strip()
            continue
        if current in sections:
            sections[current].append(line)

    return {
        "id": path.stem,
        "category": fm.get("category", ""),
        "front": "\n".join(sections["Front"]).strip(),
        "back": "\n".join(sections["Back"]).strip(),
    }


def main() -> int:
    cards = [parse_md(p) for p in sorted(ACTIVE.glob("fc-*.md"))]
    # utf-8-sig adds a BOM and the leading `sep=,` line tells Excel (Windows)
    # to split on commas on double-click instead of the regional list separator.
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        f.write("sep=,\r\n")
        w = csv.DictWriter(f, fieldnames=["id", "category", "front", "back"])
        w.writeheader()
        for c in cards:
            w.writerow(c)
    print(f"Wrote {len(cards)} flashcards to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
