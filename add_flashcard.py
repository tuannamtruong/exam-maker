"""Append a new flashcard to data/flashcards/active/. Append-only — never modifies existing files.

Reads JSON from stdin:
    {
      "category": "optional",
      "front":    "required",
      "back":     "required"
    }

Prints the path of the newly created markdown file.

Example:
    echo '{"category":"Networking","front":"VPC","back":"Virtual Private Cloud"}' \\
        | python3 add_flashcard.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACTIVE_DIR = ROOT / "data" / "flashcards" / "active"


def fail(msg: str) -> "None":
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


def next_index(out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    nums = []
    for p in out_dir.glob("fc-*.md"):
        m = re.match(r"fc-(\d+)$", p.stem)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


def render(category: str, front: str, back: str) -> str:
    return "\n".join([
        "---", f"category: {category.strip()}", "---", "",
        "# Front", front.strip(), "",
        "# Back", back.strip(), "",
    ])


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        fail(f"invalid JSON on stdin: {e}")

    if not isinstance(data, dict):
        fail("expected a JSON object on stdin")

    front = (data.get("front") or "").strip()
    back = (data.get("back") or "").strip()
    category = (data.get("category") or "").strip()

    if not front:
        fail("'front' is required")
    if not back:
        fail("'back' is required")

    idx = next_index(ACTIVE_DIR)
    path = ACTIVE_DIR / f"fc-{idx:04d}.md"
    if path.exists():
        fail(f"refusing to overwrite existing file: {path}")

    path.write_text(render(category, front, back), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
