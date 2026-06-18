# exam-maker

Local exam-prep apps. Two separate Tkinter (customtkinter) GUIs over markdown files.

- **Questions app** (`questions_app.py`) — multiple choice, 2–7 options, multi-correct supported. Orange/amber palette.
- **Flashcards app** (`flashcards_app.py`) — flip-card. Teal/sky palette.
- **Importer** (`import_data.py`) — one-shot conversion of `questions.txt` / `flashcards.txt` into per-item `.md` files.
- **Flashcards web app** (`webapp/`) — simplified, read-only PWA port of the flashcards app for Android (flip / nav / shuffle / search / jump, local hide-list "backlog"; no add/edit). `scripts/gen_webapp.py` builds `webapp/cards.json` from the active `.md` files; `./run.sh webapp` regenerates it and serves the folder over the LAN. See `webapp/README.md`.

## File layout

```
exam-maker/
├── CLAUDE.md
├── run.sh                      # launcher / dispatcher
├── questions_app.py            # GUI
├── flashcards_app.py           # GUI
├── add_question.py             # CLI: stdin JSON -> append new question .md
├── add_flashcard.py            # CLI: stdin JSON -> append new flashcard .md
├── import_data.py              # one-shot importer
├── scripts/
│   ├── stats.py                # active / backlog counts
│   └── docx_to_text.py         # .docx -> .txt helper for importer input
├── .claude/skills/exam-add/
│   └── SKILL.md                # agent skill for "add a question/flashcard..."
└── data/
    ├── questions/
    │   ├── active/             # q-NNNN.md (in rotation)
    │   └── backlog/            # q-NNNN.md (hidden, revertable)
    └── flashcards/
        ├── active/             # fc-NNNN.md
        └── backlog/            # fc-NNNN.md
```

## Commands

```bash
./run.sh questions              # open questions app
./run.sh flashcards             # open flashcards app
./run.sh import                 # re-run .txt -> .md importer
./run.sh webapp                 # build webapp data + serve PWA over the LAN
./run.sh stats                  # counts of active / backlog
./run.sh add-question  < q.json # append a question (see schema below)
./run.sh add-flashcard < c.json # append a flashcard
```

First invocation creates `.venv/` and installs `customtkinter`. Subsequent runs reuse it.

System packages required (one-time): `python3-tk`, `python3.12-venv`.

## Backlog model

"Backlog" means *hidden from rotation, not deleted*. Implemented as a sibling folder. Each app has a "Show backlog" switch; while viewing the backlog, the **Move to Backlog** button becomes **Restore to Active**. File moves are done with `shutil.move`. Filename collisions are auto-suffixed with `-1`, `-2`, …

## Hotkeys

Bound to the main window so the Add / Jump / Edit dialogs (separate Toplevels)
are unaffected while typing in them. WASD mirrors the arrow keys in both apps.
The questions app has a **Hotkeys** button that shows this list in-app.

**Questions app**

| Key            | Action                          |
| -------------- | ------------------------------- |
| `←` / `a`      | Previous question               |
| `→` / `d`      | Next question                   |
| `↑` / `w`      | Scroll content up               |
| `↓` / `s`      | Scroll content down             |
| `Space` / `Enter` | Submit                       |
| `1`–`7`        | Toggle that option              |
| `g`            | Jump to a question              |
| `f` / `/` / `Ctrl+F` | Search questions by text  |
| `e`            | Edit the current question       |
| `b`            | Move to / restore from backlog  |
| `Ctrl+N`       | Add a new question              |
| `Ctrl` `+`/`-`/`0` | Font larger / smaller / reset |

**Flashcards app**

| Key            | Action                          |
| -------------- | ------------------------------- |
| `Space`        | Flip card                       |
| `←` / `a`      | Previous card                   |
| `→` / `d`      | Next card                       |
| `g`            | Jump to a card                  |
| `f` / `/` / `Ctrl+F` | Search cards by text      |
| `e`            | Edit the current card           |
| `b`            | Move to / restore from backlog  |
| `Ctrl+N`       | Add a new flashcard             |
| `Ctrl` `+`/`-`/`0` | Font larger / smaller / reset |

## Data format — questions

`data/questions/active/q-NNNN.md`:

```markdown
---
correct: 1,3
---

# Scenario
optional context paragraph(s)

# Question
the question line (often ends with ?)

# Options
1. first option
2. second option
3. third option
4. fourth option

# Explanation
optional prose explaining the correct answer(s)
```

- `correct` is a comma-separated list of **1-based** option indices. May contain one or several.
- `# Scenario` and `# Explanation` are optional.
- `# Question` is also optional. A **scenario-only** item (a `# Scenario` plus
  `# Options`, with no `# Question`) is normal and valid — the scenario itself
  poses the question. This is common in imported material where the prompt is
  the scenario. Do **not** invent or synthesize a question line when the source
  has none; just leave `# Question` out. At least one of `# Scenario` or
  `# Question` must be present.
- Option count must be 2–7.

## Data format — flashcards

`data/flashcards/active/fc-NNNN.md`:

```markdown
---
category: Application
---

# Front
AppConfig

# Back
A capability of AWS Systems Manager (SSM). Manage, store, and quickly deploy
application configurations independently of your code.
```

## Append-only rule

**Existing items must never be modified or rewritten by automation.** Only:

- *append* new items (next `q-NNNN.md` / `fc-NNNN.md` via the add CLIs)
- *move* items between `active/` and `backlog/` (done by the apps)

If the user wants to fix wording or correct-answer marking on an existing item,
they edit the `.md` by hand, or use the in-app **Edit** dialog (the `e` key /
"Edit" button), which rewrites that single current item in place via `write_md`.
This rule forbids *automation* silently rewriting items — the agent skill, bulk
re-renders, format migrations. It does not forbid the user editing one item
deliberately. Don't bulk-rewrite, don't re-render, don't migrate the format
silently.

## Adding items via the agent skill

See `.claude/skills/exam-add/SKILL.md`. The skill takes natural-language input
and pipes JSON into `add_question.py` or `add_flashcard.py`. It must not touch
existing files.
