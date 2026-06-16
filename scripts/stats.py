"""Print active / backlog counts for questions and flashcards."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def count(dirpath: Path, pattern: str) -> int:
    return sum(1 for _ in dirpath.glob(pattern)) if dirpath.exists() else 0


def main() -> None:
    q_active = count(ROOT / "data" / "questions" / "active", "q-*.md")
    q_backlog = count(ROOT / "data" / "questions" / "backlog", "q-*.md")
    f_active = count(ROOT / "data" / "flashcards" / "active", "fc-*.md")
    f_backlog = count(ROOT / "data" / "flashcards" / "backlog", "fc-*.md")

    print(f"{'':12}{'active':>8}{'backlog':>10}{'total':>8}")
    print(f"{'-'*38}")
    print(f"{'questions':12}{q_active:>8}{q_backlog:>10}{q_active + q_backlog:>8}")
    print(f"{'flashcards':12}{f_active:>8}{f_backlog:>10}{f_active + f_backlog:>8}")


if __name__ == "__main__":
    main()
