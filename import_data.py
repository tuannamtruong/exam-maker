"""One-shot importer: questions.txt + flashcards.txt -> per-item markdown files.

Run from the project root:
    python3 import_data.py
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
Q_SRC = ROOT / "questions.txt"
F_SRC = ROOT / "flashcards.txt"
Q_OUT = ROOT / "data" / "questions" / "active"
F_OUT = ROOT / "data" / "flashcards" / "active"

BULLET_RE = re.compile(r"^[\s]*[•\-\*]\s+(.*)$")


def write_md(path: Path, frontmatter: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---"]
    for k, v in frontmatter.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append(body.rstrip() + "\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def next_index(out_dir: Path, prefix: str) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = [p.stem for p in out_dir.glob(f"{prefix}-*.md")]
    nums = []
    for stem in existing:
        m = re.match(rf"{re.escape(prefix)}-(\d+)$", stem)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


# ---------- questions ----------

def split_question_blocks(text: str) -> list[str]:
    """Split the source file into question blocks.

    Heuristic: a blank line that sits between an "is incorrect because" paragraph
    and the next scenario starts a new block. If no such separators exist we
    return the whole file as a single block.
    """
    # Normalize line endings and collapse runs of blank lines to a single blank.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{2,}", "\n\n", text).strip()
    if not text:
        return []
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    # A block usually contains at least one bullet option; group consecutive
    # paragraphs together until we see another paragraph that starts a scenario
    # AND we've already seen options in the current group.
    blocks: list[list[str]] = []
    current: list[str] = []
    saw_options = False
    for para in parts:
        has_bullet = any(BULLET_RE.match(line) for line in para.splitlines())
        if current and has_bullet is False and saw_options and _looks_like_scenario(para):
            blocks.append(current)
            current = [para]
            saw_options = False
        else:
            current.append(para)
            if has_bullet:
                saw_options = True
    if current:
        blocks.append(current)
    return ["\n\n".join(b) for b in blocks]


def _looks_like_scenario(para: str) -> bool:
    # A scenario paragraph doesn't contain "is incorrect because" and isn't a bullet list.
    if "is incorrect because" in para.lower():
        return False
    return True


def parse_question(block: str) -> dict:
    lines = [ln.rstrip() for ln in block.splitlines() if ln.strip()]
    options: list[str] = []
    pre_lines: list[str] = []
    post_lines: list[str] = []
    in_options = False
    options_done = False
    for ln in lines:
        m = BULLET_RE.match(ln)
        if m:
            if options_done:
                # bullet after explanation began -- treat as part of explanation
                post_lines.append(ln)
                continue
            in_options = True
            options.append(m.group(1).strip())
        else:
            if in_options:
                in_options = False
                options_done = True
                post_lines.append(ln)
            elif options_done:
                post_lines.append(ln)
            else:
                pre_lines.append(ln)

    # Split pre_lines into scenario + question (the trailing ?-line is the question).
    question_line = ""
    scenario_lines = list(pre_lines)
    for i in range(len(pre_lines) - 1, -1, -1):
        if pre_lines[i].endswith("?"):
            question_line = pre_lines[i]
            scenario_lines = pre_lines[:i]
            break
    scenario = " ".join(scenario_lines).strip()
    explanation = "\n\n".join(post_lines).strip()

    # Detect correct options: any option NOT referenced as "is incorrect" wins.
    correct: list[int] = []
    expl_norm = re.sub(r"\s+", " ", explanation).lower()
    for idx, opt in enumerate(options, start=1):
        head = re.sub(r"\s+", " ", opt).lower()
        # Trim trailing period for matching.
        head = head.rstrip(". ")
        needle = f"{head} is incorrect"
        if needle in expl_norm:
            continue
        correct.append(idx)
    # If everything matched as incorrect (or nothing did), leave correct empty
    # so the user can fix it by hand.
    if len(correct) == len(options):
        correct = []

    return {
        "scenario": scenario,
        "question": question_line,
        "options": options,
        "correct": correct,
        "explanation": explanation,
    }


def render_question(q: dict) -> tuple[dict, str]:
    fm = {"correct": ",".join(str(i) for i in q["correct"])}
    parts = []
    if q["scenario"]:
        parts.append("# Scenario\n" + q["scenario"])
    if q["question"]:
        parts.append("# Question\n" + q["question"])
    if q["options"]:
        opt_lines = [f"{i}. {opt}" for i, opt in enumerate(q["options"], 1)]
        parts.append("# Options\n" + "\n".join(opt_lines))
    if q["explanation"]:
        parts.append("# Explanation\n" + q["explanation"])
    return fm, "\n\n".join(parts)


def import_questions() -> int:
    if not Q_SRC.exists():
        print(f"skip: {Q_SRC} not found")
        return 0
    text = Q_SRC.read_text(encoding="utf-8", errors="replace")
    blocks = split_question_blocks(text)
    n = 0
    for block in blocks:
        q = parse_question(block)
        if not q["options"]:
            continue
        idx = next_index(Q_OUT, "q")
        fm, body = render_question(q)
        write_md(Q_OUT / f"q-{idx:04d}.md", fm, body)
        n += 1
    return n


# ---------- flashcards ----------

def parse_flashcards(text: str) -> list[dict]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    cards: list[dict] = []
    category = ""
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = BULLET_RE.match(line)
        if m:
            body = m.group(1).strip()
            front, back = _split_card(body)
            cards.append({"category": category, "front": front, "back": back})
            continue
        stripped = line.strip()
        if stripped.endswith(":") and len(stripped) < 80 and ":" not in stripped[:-1]:
            category = stripped.rstrip(":").strip()
            continue
        # Non-bullet, non-heading line: still treat as a card if it carries a colon.
        if ":" in stripped:
            front, back = _split_card(stripped)
            cards.append({"category": category, "front": front, "back": back})
    return cards


def _split_card(body: str) -> tuple[str, str]:
    # Prefer split on first colon if the part before it is short (looks like a term).
    if ":" in body:
        head, tail = body.split(":", 1)
        if 0 < len(head) <= 80:
            return head.strip(), tail.strip()
    m = re.match(r"^(.{1,80}?)\s+(?:is|are)\s+(.*)$", body)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return body.strip(), ""


def render_flashcard(c: dict) -> tuple[dict, str]:
    fm = {"category": c.get("category", "")}
    parts = [
        "# Front\n" + (c.get("front") or ""),
        "# Back\n" + (c.get("back") or ""),
    ]
    return fm, "\n\n".join(parts)


def import_flashcards() -> int:
    if not F_SRC.exists():
        print(f"skip: {F_SRC} not found")
        return 0
    text = F_SRC.read_text(encoding="utf-8", errors="replace")
    cards = parse_flashcards(text)
    n = 0
    for c in cards:
        if not c.get("front"):
            continue
        idx = next_index(F_OUT, "fc")
        fm, body = render_flashcard(c)
        write_md(F_OUT / f"fc-{idx:04d}.md", fm, body)
        n += 1
    return n


if __name__ == "__main__":
    q = import_questions()
    f = import_flashcards()
    print(f"imported {q} question(s) into {Q_OUT}")
    print(f"imported {f} flashcard(s) into {F_OUT}")
