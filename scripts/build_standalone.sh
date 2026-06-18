#!/usr/bin/env bash
# Refresh the card data and rebuild the single-file standalone web app.
#
#   scripts/build_standalone.sh
#
# 1. regenerates webapp/cards.json from data/flashcards/active/*.md
# 2. inlines it (+ css + js) into webapp/standalone.html
#
# Copy the resulting webapp/standalone.html to the phone — it's fully
# self-contained (no server, works offline). Re-run this after adding cards.
set -euo pipefail

cd "$(dirname "$0")/.."

python3 scripts/gen_webapp.py
python3 scripts/gen_standalone.py
