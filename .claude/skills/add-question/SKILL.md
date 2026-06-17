---
name: add-question
description: Add ONE multiple-choice question to exam-maker from raw pasted practice-exam text (Tutorials Dojo / AWS style — scenario, question, unnumbered options, prose explanation). Use when the user pastes a single question block and asks to save/add it. Strips boilerplate, maps each wrong-option explanation to its option number, puts the correct-answer rationale on top, and ALWAYS shows a preview for approval before appending. Single item only — not bulk import.
---

# add-question

Turn one block of pasted practice-exam prose into a project `q-NNNN.md` and
append it — **only after the user approves a preview**. The raw source (Tutorials
Dojo / AWS style) has unnumbered options and a wall of explanation prose; this
skill cleans it into the project format. Compare the finished items
`data/questions/active/q-0038.md` (multi-answer) and `q-0050.md` (single-answer)
— that is the target shape.

Paths below are relative to the project root (`/home/nam/exam-maker`, the dir
holding `add_question.py`).

## When to use

The user pastes a single question — scenario, a question line, a list of
options, and an explanation — and asks to add/save it. For one item only.

**Do not use** for: editing an existing item (forbidden — append-only; tell them
to use the app's Edit dialog), or a long document with many questions (that is
`./run.sh import`, not this skill).

## The transformation (what to produce)

From the raw paste, build these fields:

- **scenario** — the context paragraph(s). Keep verbatim.
- **question** — the question line (e.g. "Which … (Select TWO.)"). If the source
  has *no* question line and the scenario poses the question, leave it out — do
  **not** invent one.
- **options** — the answer choices, in source order, as plain strings (no `1.`
  numbering — the renderer numbers them).
- **correct** — 1-based indices. Derive from the source's
  `"Hence, the correct answer(s) is/are: <text>"` line by matching that text back
  to the options. For "Select TWO" there are several.
- **explanation** — assembled in this exact order:
  1. **Correct-answer rationale on top** — the prose explaining *why the right
     answer is right* (the paragraphs before "Hence, the correct answer…"),
     condensed to a tight paragraph. Then a blank line.
  2. **One numbered line per wrong option**, `N. <reason>`, where `N` is that
     option's number. The source writes these as
     *"The option that says: `<full option text>` is incorrect because `<reason>`."*
     Match the quoted option text to its number and keep only `<reason>`.

### Boilerplate to strip

- `Hence, the correct answer is:` / `Hence, the correct answers are:` and the
  copy of the option text that follows it.
- `The option that says:` … `is incorrect because` wrappers — keep just the
  reason, prefixed with the option number.
- Reference URLs, "Check out this cheat sheet …", and `--` question separators.

## Run (agent path)

After building the fields, write them as JSON (`scenario`, `question`,
`options`, `correct`, `explanation`) and **preview with the driver — it renders
the exact `.md` but writes nothing:**

```bash
python3 .claude/skills/add-question/preview.py < question.json
```

The driver imports `add_question.render`, so the preview is **byte-for-byte what
gets written**. It validates the same way `add_question.py` does and exits `2`
with `error: …` on a bad field (e.g. a `correct` index out of range), so you
catch problems before showing the user:

```bash
echo '{"question":"Q?","options":["a","b"],"correct":[9]}' | python3 .claude/skills/add-question/preview.py
# error: 'correct' indices must be between 1 and 2
```

**Show the user the preview AND a short "Changes from your source" list** — e.g.
"removed the `Hence, the correct answer is:` block", "mapped the three
`The option that says…` paragraphs to options 2/3/4", "moved the AWS Config
rationale to the top". This is the mandatory approval gate.

## Append (only after approval)

Pipe the **same JSON** to the real CLI from the project root. Use a heredoc to
keep newlines in multi-line fields intact:

```bash
python3 add_question.py < question.json
```

It prints the new file path (e.g. `data/questions/active/q-0051.md`). Surface it
to the user. On validation failure it prints `error: …` to stderr and exits `2`
— fix the JSON and retry; never edit existing files to work around it.

## Hard rules

- **Preview before write, every time.** Never call `add_question.py` until the
  user has seen the preview and approved. "Any changes vs the original → show me
  first."
- **One question per invocation.** Many questions → `./run.sh import`.
- **Append only.** Never modify an existing `q-NNNN.md`.
- **Don't invent a question line** when the source has none (scenario-only is
  valid).
- **Confirm an ambiguous correct answer.** If you can't match "Hence, the correct
  answer…" to an option with confidence, ask — never guess.

## Gotchas

- `add_question.py` prints an **absolute** path on success. Don't re-prepend the
  project root when referencing it.
- The source lists options as plain consecutive paragraphs with **no numbers**;
  numbering only appears in the explanation prose ("The option that says…").
  Your job is to assign the numbers, matching explanation text to option text.
- Wrong-option explanations in the source are **out of order** and interleaved
  with the correct-answer rationale — sort them by option number for the output.
- Keep option text verbatim; the renderer `.strip()`s each one but does not
  reword. Only the explanation is condensed.
- `preview.py` finds the project root as `parents[3]` of its own path. It only
  works while it lives at `.claude/skills/add-question/preview.py`.

## The driver

`.claude/skills/add-question/preview.py` — dry-run renderer. Reads the
`add_question.py` JSON schema on stdin, prints the rendered `q-NNNN.md` to
stdout, writes nothing. It delegates formatting + validation to `add_question`
so there is no second copy of the rendering logic to drift.
