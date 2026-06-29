#!/usr/bin/env python3
"""Parse a rendered q-NNNN.md back into add_question.py JSON.

Companion to preview.py. preview.py goes JSON -> md (the preview shown in the
VS Code diff); this goes md -> JSON, so hand-edits made in the right pane of
`code --diff /tmp/original.md /tmp/adjusted.md` can be folded back into the JSON
that gets piped to add_question.py.

Usage:
    python3 md_to_json.py [path]        # path defaults to /tmp/adjusted.md
    python3 md_to_json.py < file.md     # or read md from stdin

Prints the JSON to stdout. Round-trips with preview.py: feeding this output back
through preview.py reproduces the same .md (modulo blank lines the renderer
normalizes, e.g. a stray leading blank in a section left behind after a hand
edit).
"""
import json
import re
import sys


def md_to_dict(md: str) -> dict:
    head, _, body = md.partition("---\n")[2].partition("---\n")
    fm, body = head, body
    m = re.search(r"correct:\s*(.+)", fm)
    correct = [int(x) for x in m.group(1).split(",")] if m else []

    def section(name):
        s = re.search(r"# %s\n(.*?)(?=\n# |\Z)" % re.escape(name), body, re.S)
        return s.group(1).strip("\n") if s else None

    opts_raw = section("Options") or ""
    options = [re.sub(r"^\d+\.\s", "", line) for line in opts_raw.split("\n") if line.strip()]

    data = {
        "scenario": section("Scenario"),
        "question": section("Question"),
        "options": options,
        "correct": correct,
        "explanation": section("Explanation"),
    }
    # drop optional fields that are absent so the JSON matches what was built
    return {k: v for k, v in data.items() if v is not None}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/adjusted.md"
    md = sys.stdin.read() if path == "-" else open(path).read()
    json.dump(md_to_dict(md), sys.stdout)


if __name__ == "__main__":
    main()
