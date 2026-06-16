---
name: exam-add
description: Append a new exam question or flashcard to the exam-maker project. Use when the user asks to add/create a new question, multiple-choice item, or flashcard, or pastes raw study material to save. Strictly append-only — never modifies existing items.
---

# exam-add

Append a new question or flashcard to the exam-maker project under
`data/questions/active/` or `data/flashcards/active/`.

## When to use

Trigger when the user says any of:

- "Add a question about X"
- "Save this question: …"
- "Create a flashcard for Y"
- "New flashcard: front = …, back = …"
- Pastes a raw question block (scenario + options + answer) and asks to save it
- Pastes a definition / term pair and asks to save it as a card

If the user wants to *edit* an existing item or change formatting across many
items, **do not use this skill** — that is forbidden by the project's
append-only rule. Tell the user the item must be edited by hand, and where the
file lives (`data/questions/active/q-NNNN.md` or
`data/flashcards/active/fc-NNNN.md`).

## Project paths

Project root: the directory containing `add_question.py` and `add_flashcard.py`
(typically the cwd or `/home/nam/exam-maker`).

The CLIs live at `<root>/add_question.py` and `<root>/add_flashcard.py`. Always
invoke them with `python3` (not the venv path — the CLIs only use stdlib).

## How to append a question

1. **Collect** these fields. If the user only gave partial info, ask short
   follow-ups (one message, batched) instead of guessing:

   - `scenario` (optional) — context paragraph(s) before the question
   - `question` (required) — the question line itself
   - `options` (required) — list of 2 to 7 answer strings
   - `correct` (required) — list of **1-based** option indices, e.g. `[1, 3]`.
     For a single-answer question this is a one-element list, e.g. `[3]`.
   - `explanation` (optional) — why the answer is correct / why others are wrong

2. **Build a JSON object** with those keys.

3. **Pipe it into the CLI** from the project root:

   ```bash
   echo '<JSON>' | python3 add_question.py
   ```

   For multi-line content use a heredoc to keep newlines intact:

   ```bash
   python3 add_question.py <<'JSON'
   {
     "scenario": "...",
     "question": "...",
     "options": ["A", "B", "C", "D"],
     "correct": [3],
     "explanation": "..."
   }
   JSON
   ```

4. The CLI prints the path of the new file (e.g.
   `data/questions/active/q-0042.md`) on success, or `error: <reason>` on
   stderr with exit code 2 on validation failure. Surface the new path to the
   user.

## How to append a flashcard

1. **Collect** these fields:

   - `category` (optional) — short topic label (e.g. "Networking", "IAM")
   - `front` (required) — the prompt / term
   - `back` (required) — the answer / definition

2. **Pipe JSON** to the CLI:

   ```bash
   python3 add_flashcard.py <<'JSON'
   {
     "category": "Networking",
     "front": "VPC",
     "back": "Virtual Private Cloud — isolated network within AWS."
   }
   JSON
   ```

3. The CLI prints the new file path on success.

## Hard rules

- **Append only.** Never edit an existing `.md` under `data/`. Never re-emit
  prior items. Never call `add_question.py` / `add_flashcard.py` with content
  copied from an existing file (it would create a duplicate, not an edit).
- **No file moves.** Backlog moves are done by the GUI apps, not this skill.
- **Don't bulk-import.** If the user pastes a long document with many items,
  ask whether to add them one by one or whether they want to re-run
  `import_data.py` against a fresh `questions.txt` / `flashcards.txt`.
- **No format drift.** The CLI is the single source of formatting; do not
  hand-write `.md` files directly.
- **Confirm ambiguous correct answers.** If the user pastes options without
  marking which is correct, ask — never guess.

## Batch additions

If the user gives several items in one message, loop the CLI once per item.
After all succeed, report the count and list the new file paths.

## Failure handling

If the CLI returns non-zero:

- Show the user the stderr message.
- Fix the JSON (e.g. add the missing `question`, fix `correct` indices to be
  within range) and retry.
- Never `--break-system-packages`, never edit existing files to work around a
  validation error.
