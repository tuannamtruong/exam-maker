#!/usr/bin/env python3
"""Diff an edited flashcards CSV against the active .md files and apply changes.

Reads flashcards_table.csv (as produced by gen_flashcards_csv.py, possibly
re-saved by Excel with a different delimiter / no BOM / no sep= line), matches
rows to active fc-NNNN.md by the `id` column, and reports/applies only the
cards whose category, front, or back actually changed.

Dry run by default; pass --apply to write the changed .md files.
Never adds, deletes, or renames files. Unknown ids and missing ids are flagged.
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACTIVE = ROOT / "data" / "flashcards" / "active"
CSV_PATH = ROOT / "flashcards_table.csv"

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
        "category": fm.get("category", ""),
        "front": "\n".join(sections["Front"]).strip(),
        "back": "\n".join(sections["Back"]).strip(),
    }


def write_md(path: Path, category: str, front: str, back: str) -> None:
    parts = [
        "---", f"category: {category.strip()}", "---", "",
        "# Front", front.strip(), "",
        "# Back", back.strip(), "",
    ]
    path.write_text("\n".join(parts), encoding="utf-8")


# cp1252 leaves these byte values undefined; Python decodes them to the matching
# C1 control codepoint, so to reverse the mojibake we must map them straight back.
_CP1252_UNDEFINED = {"\x81": 0x81, "\x8d": 0x8d, "\x8f": 0x8f,
                     "\x90": 0x90, "\x9d": 0x9d}


def _to_cp1252_bytes(s: str) -> bytes:
    out = bytearray()
    for ch in s:
        if ch in _CP1252_UNDEFINED:
            out.append(_CP1252_UNDEFINED[ch])
        else:
            out.extend(ch.encode("cp1252"))
    return bytes(out)


def fix_mojibake(s: str) -> str:
    """Undo the UTF-8-read-as-cp1252-then-re-saved double-encoding that Excel
    introduces (e.g. '’' -> 'â€™'). No-op for plain ASCII; if the string can't
    be round-tripped through cp1252/utf-8 it is left untouched."""
    try:
        repaired = _to_cp1252_bytes(s).decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s
    return repaired


def read_csv_rows(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8-sig")  # strips BOM if present
    lines = raw.splitlines(keepends=True)
    # Drop a leading Excel `sep=...` hint line if present.
    if lines and lines[0].lower().startswith("sep="):
        lines = lines[1:]
    text = "".join(lines)
    # Detect delimiter from the header line (comma vs semicolon vs tab).
    header = text.splitlines()[0] if text else ""
    delim = max([",", ";", "\t"], key=header.count)
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    rows = []
    for r in reader:
        rows.append({k: (fix_mojibake(v) if isinstance(v, str) else v)
                     for k, v in r.items()})
    return rows


def main() -> int:
    apply = "--apply" in sys.argv
    rows = read_csv_rows(CSV_PATH)

    md_ids = {p.stem for p in ACTIVE.glob("fc-*.md")}
    csv_ids = {(r.get("id") or "").strip() for r in rows}

    missing = sorted(md_ids - csv_ids)   # in .md but absent from CSV
    unknown = sorted(csv_ids - md_ids)   # in CSV but no matching .md

    changes: list[tuple[str, dict, dict]] = []
    for r in rows:
        fid = (r.get("id") or "").strip()
        if fid not in md_ids:
            continue
        path = ACTIVE / f"{fid}.md"
        cur = parse_md(path)
        new = {
            "category": (r.get("category") or "").strip(),
            "front": (r.get("front") or "").strip(),
            "back": (r.get("back") or "").strip(),
        }
        diffs = {k: (cur[k], new[k]) for k in ("category", "front", "back")
                 if cur[k] != new[k]}
        if diffs:
            changes.append((fid, diffs, new))

    print(f"CSV rows: {len(rows)}   active .md: {len(md_ids)}   "
          f"changed: {len(changes)}")
    if unknown:
        print(f"\n[!] ids in CSV with no matching .md (ignored): {unknown}")
    if missing:
        print(f"\n[!] active .md ids missing from CSV (left untouched): {missing}")

    for fid, diffs, _new in changes:
        print(f"\n=== {fid} ===")
        for field, (old, new) in diffs.items():
            print(f"  {field}:")
            print(f"    - {old!r}")
            print(f"    + {new!r}")

    if not changes:
        print("\nNo content changes detected.")
        return 0

    if apply:
        for fid, _diffs, new in changes:
            write_md(ACTIVE / f"{fid}.md", new["category"], new["front"], new["back"])
        print(f"\nApplied {len(changes)} change(s).")
    else:
        print("\nDRY RUN — re-run with --apply to write these changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
