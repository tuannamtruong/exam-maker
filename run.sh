#!/usr/bin/env bash
# Launcher.
#
# Usage:
#   ./run.sh questions             open the questions app
#   ./run.sh flashcards            open the flashcards app
#   ./run.sh import                re-run the .txt -> .md importer
#   ./run.sh stats                 show active / backlog counts
#   ./run.sh add-question          read JSON from stdin, append a question
#   ./run.sh add-flashcard         read JSON from stdin, append a flashcard
set -euo pipefail

cd "$(dirname "$0")"

VENV=".venv"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"

usage() {
    sed -n '2,11p' "$0"
    exit 1
}

[[ $# -ge 1 ]] || usage

# venv bootstrap (no-op once created)
if [[ ! -x "$PY" ]]; then
    echo "==> creating venv at $VENV"
    if ! python3 -m venv "$VENV" 2>/dev/null; then
        echo "ERROR: 'python3 -m venv' failed."
        echo "Run: sudo apt install python3.12-venv python3-tk"
        exit 1
    fi
fi

ensure_ctk() {
    if ! "$PY" -c "import customtkinter" 2>/dev/null; then
        echo "==> installing customtkinter"
        "$PIP" install --quiet --upgrade pip
        "$PIP" install --quiet customtkinter
    fi
}

ensure_tk() {
    if ! "$PY" -c "import tkinter" 2>/dev/null; then
        echo "ERROR: tkinter is missing. Run: sudo apt install python3-tk"
        exit 1
    fi
}

cmd="$1"; shift
case "$cmd" in
    questions)
        ensure_tk; ensure_ctk
        exec "$PY" questions_app.py "$@"
        ;;
    flashcards)
        ensure_tk; ensure_ctk
        exec "$PY" flashcards_app.py "$@"
        ;;
    import)
        exec "$PY" import_data.py "$@"
        ;;
    stats)
        exec "$PY" scripts/stats.py "$@"
        ;;
    add-question)
        exec "$PY" add_question.py "$@"
        ;;
    add-flashcard)
        exec "$PY" add_flashcard.py "$@"
        ;;
    *)
        usage
        ;;
esac
