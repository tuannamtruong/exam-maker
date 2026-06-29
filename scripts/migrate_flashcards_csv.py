#!/usr/bin/env python3
"""One-shot migration of the edited flashcards_table.csv into the .md store.

Reads the (mojibake-repaired) CSV via apply_flashcards_csv and performs, per the
agreed plan:
  * EDIT   - id row whose category/front/back differs (and isn't fully blank)
  * DELETE - id row blanked to empty front+back, plus ids removed from the CSV
  * NEW    - id-less rows with content, appended via add_flashcard.py

Dry run by default; pass --apply to execute. DELETE is a hard file delete.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply_flashcards_csv as A  # noqa: E402

ROOT = A.ROOT

# Categories for the 5 id-less rows (CSV left them blank); see chat rationale.
NEW_CATEGORY = {
    "AWS-managed prefix lists": "Terms",
    "Management Events": "Monitor/Logger",
    "Data Events": "Monitor/Logger",
    "RDS event": "Monitor/Logger",
    "CloudWatch Anomaly Detection": "Logging & Monitoring",
}


def main() -> int:
    apply = "--apply" in sys.argv
    rows = A.read_csv_rows(A.CSV_PATH)
    md_ids = {p.stem for p in A.ACTIVE.glob("fc-*.md")}
    csv_ids = {(r.get("id") or "").strip() for r in rows if (r.get("id") or "").strip()}

    edits, deletes, news = [], [], []
    for r in rows:
        fid = (r.get("id") or "").strip()
        f = (r.get("front") or "").strip()
        b = (r.get("back") or "").strip()
        cat = (r.get("category") or "").strip()
        if not fid:
            if f or b:
                news.append((NEW_CATEGORY.get(f, cat), f, b))
            continue
        if fid not in md_ids:
            continue
        if not f and not b:
            deletes.append(fid)
            continue
        cur = A.parse_md(A.ACTIVE / f"{fid}.md")
        if (cur["category"], cur["front"], cur["back"]) != (cat, f, b):
            edits.append((fid, cat, f, b))

    deletes += sorted(md_ids - csv_ids)  # ids dropped from the CSV entirely

    print(f"EDIT  {len(edits)}: {[e[0] for e in edits]}")
    print(f"DELETE {len(deletes)}: {sorted(deletes)}")
    print(f"NEW   {len(news)}: {[(c, f) for c, f, _ in news]}")

    if not apply:
        print("\nDRY RUN — re-run with --apply to execute.")
        return 0

    for fid, cat, f, b in edits:
        A.write_md(A.ACTIVE / f"{fid}.md", cat, f, b)
    for fid in deletes:
        (A.ACTIVE / f"{fid}.md").unlink()
    for cat, f, b in news:
        payload = json.dumps({"category": cat, "front": f, "back": b})
        out = subprocess.run(
            [sys.executable, str(ROOT / "add_flashcard.py")],
            input=payload, text=True, capture_output=True,
        )
        if out.returncode != 0:
            print(f"  [!] add failed for {f!r}: {out.stderr.strip()}")
        else:
            print(f"  added {out.stdout.strip()}  ({cat})")
    print(f"\nDONE: {len(edits)} edited, {len(deletes)} deleted, {len(news)} added.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
