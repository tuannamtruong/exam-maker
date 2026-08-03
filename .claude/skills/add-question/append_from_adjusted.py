#!/usr/bin/env python3
"""Append a question straight from the approved preview (`/tmp/adjusted.md`).

This is the mandatory final step of the add-question skill. `adjusted.md` is the
single source of truth after the user's diff-pane hand-edits, so appending from
it — rather than from a possibly-stale `/tmp/question.json` — guarantees the
user's edits always win. It re-parses the .md, then pipes the resulting JSON to
the real `add_question.py`, reusing that CLI's validation and rendering verbatim.

Usage:
    python3 append_from_adjusted.py [path]   # path defaults to /tmp/adjusted.md

Prints the new file path (from add_question.py) on success; on a validation
failure it forwards add_question.py's `error: …` to stderr and exits 2.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]  # .claude/skills/add-question/ -> project root

sys.path.insert(0, str(HERE.parent))
from md_to_json import md_to_dict  # noqa: E402


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/adjusted.md"
    md = open(path).read()
    data = md_to_dict(md)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "add_question.py")],
        input=json.dumps(data),
        text=True,
        cwd=str(ROOT),
    )
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
