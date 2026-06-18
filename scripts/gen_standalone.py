#!/usr/bin/env python3
"""Build a single self-contained ``webapp/standalone.html`` for manual install.

Inlines ``styles.css``, ``app.js`` and the generated ``cards.json`` into one
HTML file with no external references, so it can simply be copied to a phone and
opened from local storage (Downloads) — no server, no network, works offline by
nature. "Add to Home Screen" then makes a normal launcher shortcut.

Differences from the served PWA: no service worker (not needed — nothing is
fetched) and no manifest-based install. Everything else (flip / nav / shuffle /
search / jump / local backlog) is identical, since the same ``app.js`` runs.

    python3 scripts/gen_standalone.py        # writes webapp/standalone.html

Run ``scripts/gen_webapp.py`` first (or ``./run.sh webapp``) so ``cards.json``
is up to date; this script reads that file. It never touches the source .md
files (append-only rule) — it only reads under ``webapp/`` and writes
``standalone.html``.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEBAPP_DIR = ROOT / "webapp"


def build() -> str:
    css = (WEBAPP_DIR / "styles.css").read_text(encoding="utf-8")
    js = (WEBAPP_DIR / "app.js").read_text(encoding="utf-8")
    cards_json = (WEBAPP_DIR / "cards.json").read_text(encoding="utf-8").strip()

    # Make app.js self-contained: read embedded data instead of fetch(),
    # and drop the service-worker registration (no SW on file://).
    js = re.sub(
        r"const res = await fetch\(\"cards\.json\".*?allCards = await res\.json\(\);",
        "allCards = window.__CARDS__;",
        js,
        flags=re.DOTALL,
    )
    js = re.sub(
        r'\n\s*if \("serviceWorker" in navigator\) \{.*?\}\n',
        "\n",
        js,
        flags=re.DOTALL,
    )
    # The fetch was inside a try/catch; the catch is now dead but harmless.

    # Body markup, lifted from index.html (kept in sync by hand — it's static).
    body = """  <header class="topbar">
    <span id="title" class="title">Flashcards</span>
    <div class="toggles">
      <label class="switch"><input type="checkbox" id="shuffle" /><span>Shuffle</span></label>
      <label class="switch"><input type="checkbox" id="backlog" /><span>Backlog</span></label>
    </div>
  </header>

  <div id="category" class="category"></div>

  <main class="card" id="card">
    <div class="face" id="face">FRONT — tap to flip</div>
    <div class="content" id="content"></div>
  </main>

  <nav class="controls">
    <button id="prev" class="btn soft" aria-label="Previous">&lsaquo;</button>
    <button id="flip" class="btn primary">Flip</button>
    <button id="next" class="btn soft" aria-label="Next">&rsaquo;</button>
    <button id="jump" class="btn soft small">Jump</button>
    <button id="search" class="btn soft small">Search</button>
    <button id="move" class="btn outline small">Hide</button>
  </nav>

  <div id="searchModal" class="modal hidden">
    <div class="sheet">
      <input id="searchInput" type="text" placeholder="Search category, front, back…" autocomplete="off" />
      <div id="searchCount" class="muted"></div>
      <div id="searchResults" class="results"></div>
      <button id="searchClose" class="btn soft small close">Close</button>
    </div>
  </div>

  <div id="jumpModal" class="modal hidden">
    <div class="sheet narrow">
      <div id="jumpLabel" class="muted"></div>
      <input id="jumpInput" type="number" inputmode="numeric" />
      <div class="row">
        <button id="jumpGo" class="btn primary">Go</button>
        <button id="jumpClose" class="btn soft">Cancel</button>
      </div>
    </div>
  </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <meta name="theme-color" content="#0D9488" />
  <title>Flashcards</title>
  <style>
{css}
  </style>
</head>
<body>
{body}

  <script>
window.__CARDS__ = {cards_json};
  </script>
  <script>
{js}
  </script>
</body>
</html>
"""


def main() -> None:
    out = WEBAPP_DIR / "standalone.html"
    out.write_text(build(), encoding="utf-8")
    kb = out.stat().st_size / 1024
    print(f"Wrote {out}  ({kb:.0f} KB) — copy this single file to the phone")


if __name__ == "__main__":
    main()
