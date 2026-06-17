"""Append a new question to data/questions/active/. Append-only — never modifies existing files.

Reads JSON from stdin:
    {
      "scenario":    "optional context paragraph",
      "question":    "the question line — optional if a scenario is given",
      "options":     ["...", "...", ...],   # 2-7 strings
      "correct":     [1, 3],                # 1-based indices into options
      "explanation": "optional"
    }

A scenario-only item (no separate question line) is valid: the scenario itself
poses the question. At least one of 'scenario' or 'question' must be present.

Prints the path of the newly created markdown file.

Example:
    echo '{"question":"Q?","options":["A","B"],"correct":[1]}' | python3 add_question.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACTIVE_DIR = ROOT / "data" / "questions" / "active"


def fail(msg: str) -> "None":
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


def next_index(out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    nums = []
    for p in out_dir.glob("q-*.md"):
        m = re.match(r"q-(\d+)$", p.stem)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


def render(scenario: str, question: str, options: list[str], correct: list[int], explanation: str) -> str:
    parts = ["---", f"correct: {','.join(str(i) for i in correct)}", "---", ""]
    if scenario:
        parts += ["# Scenario", scenario.strip(), ""]
    if question:
        parts += ["# Question", question.strip(), ""]
    parts += ["# Options"] + [f"{i}. {opt.strip()}" for i, opt in enumerate(options, 1)] + [""]
    if explanation:
        parts += ["# Explanation", explanation.strip(), ""]
    return "\n".join(parts)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        fail(f"invalid JSON on stdin: {e}")

    if not isinstance(data, dict):
        fail("expected a JSON object on stdin")

    question = (data.get("question") or "").strip()
    options = data.get("options") or []
    correct = data.get("correct") or []
    scenario = (data.get("scenario") or "").strip()
    explanation = (data.get("explanation") or "").strip()

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

    idx = next_index(ACTIVE_DIR)
    path = ACTIVE_DIR / f"q-{idx:04d}.md"
    if path.exists():
        fail(f"refusing to overwrite existing file: {path}")

    path.write_text(render(scenario, question, options, correct, explanation), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
