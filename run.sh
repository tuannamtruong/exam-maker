#!/usr/bin/env bash
# Launcher.
#
# Usage:
#   ./run.sh questions             open the questions app
#   ./run.sh flashcards            open the flashcards app
#   ./run.sh import                re-run the .txt -> .md importer
#   ./run.sh webapp                build webapp data + serve it over the LAN
#   ./run.sh stats                 show active / backlog counts
#   ./run.sh add-question          read JSON from stdin, append a question
#   ./run.sh add-flashcard         read JSON from stdin, append a flashcard
set -euo pipefail

cd "$(dirname "$0")"

VENV=".venv"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"

usage() {
    sed -n '2,12p' "$0"
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
        exec "$PY" import/import_data.py "$@"
        ;;
    webapp)
        # Regenerate the card payload, then serve webapp/ over the LAN so the
        # phone (same Wi-Fi) can open it and "Add to Home Screen".
        python3 scripts/gen_webapp.py
        port="${1:-8000}"
        ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
        echo
        echo "Serving webapp/ on port $port. On your phone (same Wi-Fi) open:"
        [[ -n "$ip" ]] && echo "    http://$ip:$port/" || echo "    http://<this-machine-ip>:$port/"
        echo "Then use the browser menu -> Add to Home Screen. Ctrl-C to stop."
        echo
        exec python3 -m http.server "$port" --directory webapp
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
