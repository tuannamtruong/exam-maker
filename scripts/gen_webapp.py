#!/usr/bin/env python3
"""Generate the web-app card payload (and icons) from the flashcard .md files.

Reads every ``data/flashcards/active/fc-*.md`` and writes ``webapp/cards.json``
— the single data file the PWA loads. Run this whenever you add cards on this
machine, then re-serve the ``webapp/`` folder so the phone picks up the update.

    python3 scripts/gen_webapp.py

This script never modifies the source .md files (append-only rule); it only
reads them and (re)writes files under ``webapp/``.
"""
from __future__ import annotations

import json
import re
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACTIVE_DIR = ROOT / "data" / "flashcards" / "active"
WEBAPP_DIR = ROOT / "webapp"

SECTION_RE = re.compile(r"^#\s+(Front|Back)\s*$")


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
        m = SECTION_RE.match(line)
        if m:
            current = m.group(1)
            continue
        if current is not None:
            sections[current].append(line)

    return {
        "id": path.stem,
        "category": fm.get("category", ""),
        "front": "\n".join(sections["Front"]).strip(),
        "back": "\n".join(sections["Back"]).strip(),
    }


def write_solid_png(path: Path, size: int, rgb: tuple[int, int, int]) -> None:
    """Write a minimal solid-colour PNG using only the stdlib (no Pillow)."""
    r, g, b = rgb
    row = b"\x00" + bytes((r, g, b)) * size           # filter byte + RGB pixels
    raw = row * size
    comp = zlib.compress(raw, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)  # 8-bit RGB
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", comp)
           + chunk(b"IEND", b""))
    path.write_bytes(png)


def main() -> None:
    WEBAPP_DIR.mkdir(parents=True, exist_ok=True)
    cards = [parse_md(p) for p in sorted(ACTIVE_DIR.glob("fc-*.md"))]
    (WEBAPP_DIR / "cards.json").write_text(
        json.dumps(cards, ensure_ascii=False, indent=0), encoding="utf-8"
    )

    teal = (13, 148, 136)  # teal-600, matches the app palette
    write_solid_png(WEBAPP_DIR / "icon-192.png", 192, teal)
    write_solid_png(WEBAPP_DIR / "icon-512.png", 512, teal)

    print(f"Wrote {len(cards)} cards -> {WEBAPP_DIR / 'cards.json'}")


if __name__ == "__main__":
    main()
