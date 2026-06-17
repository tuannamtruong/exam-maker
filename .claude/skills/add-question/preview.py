#!/usr/bin/env python3
"""Dry-run renderer for a new exam question — the approval step of the
``add-question`` skill.

Reads the SAME JSON schema as ``add_question.py`` from stdin and prints the
rendered ``q-NNNN.md`` body to stdout **without writing any file**. The agent
uses this to show the user an exact preview before the question is appended,
satisfying the "show me first for manual approval" rule.

Formatting and validation are delegated to ``add_question`` so the preview is
byte-for-byte identical to what ``add_question.py`` will write on approval —
there is no second copy of the rendering logic to drift.

Usage (from the project root):
    python3 .claude/skills/add-question/preview.py < question.json
    cat question.json | python3 .claude/skills/add-question/preview.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# This file lives at <root>/.claude/skills/add-question/preview.py, so the
# project root (which holds add_question.py) is three directories up.
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

try:
    from add_question import render
except ImportError:
    print(f"error: could not import add_question from {ROOT}", file=sys.stderr)
    sys.exit(2)


def fail(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        fail(f"invalid JSON on stdin: {e}")

    if not isinstance(data, dict):
        fail("expected a JSON object on stdin")

    question = (data.get("question") or "").strip()
    scenario = (data.get("scenario") or "").strip()
    explanation = (data.get("explanation") or "").strip()
    options = data.get("options") or []
    correct = data.get("correct") or []

    # Same validation as add_question.main() so a preview fails exactly where
    # the real append would, and the agent catches it before showing the user.
    if not question and not scenario:
        fail("provide a 'question', a 'scenario', or both")
    if not isinstance(options, list) or not all(isinstance(o, str) for o in options):
        fail("'options' must be a list of strings")
    if not (2 <= len(options) <= 7):
        fail("'options' must contain 2 to 7 items")
    if not isinstance(correct, list) or not all(isinstance(i, int) for i in correct):
        fail("'correct' must be a list of integers (1-based indices)")
    if not correct:
        fail("'correct' cannot be empty")
    if any(i < 1 or i > len(options) for i in correct):
        fail(f"'correct' indices must be between 1 and {len(options)}")
    correct = sorted(set(correct))

    sys.stdout.write(render(scenario, question, options, correct, explanation))


if __name__ == "__main__":
    main()
