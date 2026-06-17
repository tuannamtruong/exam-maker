#!/usr/bin/env python3
"""Extract plain-text paragraphs from a .docx file using only the stdlib.

A .docx is a zip archive; the body text lives in ``word/document.xml`` as a
sequence of ``<w:p>`` paragraphs each holding ``<w:t>`` text runs. This avoids
the python-docx dependency, which is handy when prepping source material for the
exam-maker add CLIs (see .claude/skills/exam-add/SKILL.md).

Usage:
    python3 scripts/docx_to_text.py path/to/file.docx        # one line per paragraph
    python3 scripts/docx_to_text.py path/to/file.docx --numbered

As a library:
    from scripts.docx_to_text import extract_paragraphs
    lines = extract_paragraphs("file.docx")
"""
from __future__ import annotations

import re
import sys
import zipfile

_ENTITIES = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&apos;": "'",
}


def extract_paragraphs(path: str) -> list[str]:
    """Return the text of each paragraph in the document, in order."""
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")

    paragraphs = []
    for para in re.split(r"</w:p>", xml):
        runs = re.findall(r"<w:t[^>]*>(.*?)</w:t>", para, re.S)
        text = "".join(runs)
        for entity, char in _ENTITIES.items():
            text = text.replace(entity, char)
        paragraphs.append(text)
    return paragraphs


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    numbered = "--numbered" in argv[1:]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2

    for i, line in enumerate(extract_paragraphs(args[0])):
        print(f"{i:4} {line}" if numbered else line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
