"""Multiple-choice exam practice app (customtkinter, orange/amber palette).

Run:
    pip install customtkinter
    python3 questions_app.py
"""
from __future__ import annotations

import json
import random
import re
import shutil
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

ROOT = Path(__file__).resolve().parent
ACTIVE_DIR = ROOT / "data" / "questions" / "active"
BACKLOG_DIR = ROOT / "data" / "questions" / "backlog"

STATE_FILE = ROOT / ".app_state.json"
STATE_KEY = "questions_font_scale"
DIALOG_STATE_KEY = "questions_dialog_font_scale"


def load_font_scale(key: str = STATE_KEY) -> float:
    try:
        scale = json.loads(STATE_FILE.read_text()).get(key, 1.0)
        return max(0.7, min(2.5, float(scale)))
    except (OSError, ValueError, TypeError):
        return 1.0


def save_font_scale(scale: float, key: str = STATE_KEY) -> None:
    try:
        state = json.loads(STATE_FILE.read_text())
        if not isinstance(state, dict):
            state = {}
    except (OSError, ValueError):
        state = {}
    state[key] = scale
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except OSError:
        pass

SECTION_RE = re.compile(r"^#\s+(Scenario|Question|Options|Explanation)\s*$")
OPTION_RE = re.compile(r"^\s*(\d+)\.\s+(.*)$")

P = {
    "bg":         "#FFF7ED",  # orange-50
    "surface":    "#FFFFFF",
    "primary":    "#EA580C",  # orange-600
    "primary_hv": "#C2410C",  # orange-700
    "accent":     "#F59E0B",  # amber-500
    "accent_hv":  "#D97706",  # amber-600
    "ok":         "#16A34A",  # green-600
    "ok_bg":      "#DCFCE7",  # green-100
    "bad":        "#DC2626",  # red-600
    "bad_bg":     "#FEE2E2",  # red-100
    "miss_bg":    "#FEF3C7",  # amber-100
    "text":       "#1F2937",  # gray-800
    "muted":      "#6B7280",  # gray-500
    "border":     "#FED7AA",  # orange-200
    "soft":       "#FFEDD5",  # orange-100
}


# ---------- markdown I/O (unchanged behavior) ----------

def parse_md(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    fm: dict[str, str] = {}
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                line = line.strip()
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()
            body = text[end + 4 :]

    sections: dict[str, list[str]] = {"Scenario": [], "Question": [], "Options": [], "Explanation": []}
    current = None
    for line in body.splitlines():
        m = SECTION_RE.match(line)
        if m:
            current = m.group(1)
            continue
        if current is not None:
            sections[current].append(line)

    options: list[str] = []
    for line in sections["Options"]:
        m = OPTION_RE.match(line)
        if m:
            options.append(m.group(2).strip())

    correct_raw = fm.get("correct", "").strip()
    correct: list[int] = []
    if correct_raw:
        for piece in correct_raw.split(","):
            piece = piece.strip()
            if piece.isdigit():
                correct.append(int(piece))

    return {
        "path": path,
        "scenario": "\n".join(sections["Scenario"]).strip(),
        "question": "\n".join(sections["Question"]).strip(),
        "options": options,
        "explanation": "\n".join(sections["Explanation"]).strip(),
        "correct": correct,
    }


def write_md(path: Path, scenario: str, question: str, options: list[str], correct: list[int], explanation: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    parts = ["---", f"correct: {','.join(str(i) for i in correct)}", "---", ""]
    if scenario:
        parts += ["# Scenario", scenario.strip(), ""]
    if question:
        parts += ["# Question", question.strip(), ""]
    if options:
        parts += ["# Options"] + [f"{i}. {opt.strip()}" for i, opt in enumerate(options, 1)] + [""]
    if explanation:
        parts += ["# Explanation", explanation.strip(), ""]
    path.write_text("\n".join(parts), encoding="utf-8")


def next_index(out_dir: Path) -> int:
    nums = []
    for p in out_dir.glob("q-*.md"):
        m = re.match(r"q-(\d+)$", p.stem)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


def unique_target(target_dir: Path, name: str) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    base = Path(name).stem
    ext = Path(name).suffix or ".md"
    candidate = target_dir / f"{base}{ext}"
    i = 1
    while candidate.exists():
        candidate = target_dir / f"{base}-{i}{ext}"
        i += 1
    return candidate


# ---------- UI helpers ----------

def card(parent, **kwargs) -> ctk.CTkFrame:
    return ctk.CTkFrame(
        parent,
        fg_color=P["surface"],
        corner_radius=12,
        border_width=1,
        border_color=P["border"],
        **kwargs,
    )


def section_label(parent, text: str, font: ctk.CTkFont | None = None) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent,
        text=text.upper(),
        text_color=P["primary"],
        font=font or ctk.CTkFont(size=11, weight="bold"),
        anchor="w",
    )


def readonly_textbox(parent, height: int, font: ctk.CTkFont | None = None) -> ctk.CTkTextbox:
    tb = ctk.CTkTextbox(
        parent,
        height=height,
        wrap="word",
        fg_color=P["surface"],
        text_color=P["text"],
        border_width=0,
        font=font or ctk.CTkFont(size=13),
    )
    tb.configure(state="disabled")
    return tb


def set_text(tb: ctk.CTkTextbox, content: str) -> None:
    tb.configure(state="normal")
    tb.delete("1.0", "end")
    tb.insert("1.0", content)
    tb.configure(state="disabled")


# ---------- main app ----------

class QuestionsApp:
    def __init__(self) -> None:
        ctk.set_appearance_mode("light")

        self.root = ctk.CTk()
        self.root.title("Exam Practice — Questions")
        self.root.geometry("980x820")
        self.root.configure(fg_color=P["bg"])

        self.show_backlog = ctk.BooleanVar(value=False)
        self.shuffled = ctk.BooleanVar(value=False)
        self.items: list[Path] = []
        self.index = 0
        self.current: dict | None = None
        self.checkboxes: list[ctk.CTkCheckBox] = []
        self.check_vars: list[ctk.BooleanVar] = []
        self.option_labels: list[ctk.CTkLabel] = []
        self.submitted = False
        self._option_wrap = 700
        self._explanation_wrap = 700
        self._scenario_wrap = 700

        self.font_scale = load_font_scale()
        self._fonts: list[tuple[ctk.CTkFont, int, str]] = []
        self.title_font = self._font(18, "bold")
        self.section_font = self._font(11, "bold")
        self.body_font = self._font(13)
        self.option_font = self._font(13)
        self.button_font = self._font(14, "bold")
        self.switch_font = self._font(13)

        self._build_ui()
        self.reload(reset_index=True)

        self.root.bind_all("<Control-n>", lambda _e: self.add_dialog())
        self.root.bind_all("<Command-n>", lambda _e: self.add_dialog())
        self.root.bind_all("<Control-plus>", lambda _e: self._bump_font(0.1))
        self.root.bind_all("<Control-equal>", lambda _e: self._bump_font(0.1))
        self.root.bind_all("<Control-minus>", lambda _e: self._bump_font(-0.1))
        self.root.bind_all("<Control-0>", lambda _e: self._reset_font())

        # Hotkeys (bound to the main window so the Add / Jump dialogs — separate
        # Toplevels — are unaffected while typing in them). WASD mirrors arrows.
        #   Left  / a      : previous question
        #   Right / d      : next question
        #   Up    / w      : scroll the content up
        #   Down  / s      : scroll the content down
        #   space / Return : submit
        #   1–7            : toggle that option
        #   b              : move to / restore from backlog
        #   g              : jump to a specific question
        #   f / / / Ctrl+f : search questions by text
        #   e              : edit the current question
        for key in ("<Left>", "<KeyPress-a>", "<KeyPress-A>"):
            self.root.bind(key, lambda _e: self.prev())
        for key in ("<Right>", "<KeyPress-d>", "<KeyPress-D>"):
            self.root.bind(key, lambda _e: self.next())
        for key in ("<Up>", "<KeyPress-w>", "<KeyPress-W>"):
            self.root.bind(key, lambda _e: self._scroll(-3))
        for key in ("<Down>", "<KeyPress-s>", "<KeyPress-S>"):
            self.root.bind(key, lambda _e: self._scroll(3))
        for key in ("<space>", "<Return>"):
            self.root.bind(key, lambda _e: self.submit())
        for key in ("<KeyPress-b>", "<KeyPress-B>"):
            self.root.bind(key, lambda _e: self.toggle_backlog())
        for key in ("<KeyPress-g>", "<KeyPress-G>"):
            self.root.bind(key, lambda _e: self.jump_dialog())
        for key in ("<KeyPress-f>", "<KeyPress-F>", "<slash>", "<Control-f>"):
            self.root.bind(key, lambda _e: self.search_dialog())
        for key in ("<KeyPress-e>", "<KeyPress-E>"):
            self.root.bind(key, lambda _e: self.edit_dialog())
        for n in range(1, 8):
            self.root.bind(str(n), lambda _e, i=n: self._toggle_option(i))
        self.root.bind("<F11>", lambda _e: self._toggle_fullscreen())
        self.root.bind("<Escape>", lambda _e: self._exit_fullscreen())

    def _toggle_fullscreen(self) -> None:
        self.root.attributes("-fullscreen", not self.root.attributes("-fullscreen"))

    def _exit_fullscreen(self) -> None:
        self.root.attributes("-fullscreen", False)

    def _font(self, size: int, weight: str = "normal") -> ctk.CTkFont:
        f = ctk.CTkFont(size=max(8, int(round(size * self.font_scale))), weight=weight)
        self._fonts.append((f, size, weight))
        return f

    def _apply_font_scale(self) -> None:
        for f, base, _weight in self._fonts:
            f.configure(size=max(8, int(round(base * self.font_scale))))

    def _bump_font(self, delta: float) -> None:
        new = round(self.font_scale + delta, 2)
        new = max(0.7, min(2.5, new))
        if new == self.font_scale:
            return
        self.font_scale = new
        self._apply_font_scale()
        save_font_scale(self.font_scale)

    def _reset_font(self) -> None:
        if self.font_scale == 1.0:
            return
        self.font_scale = 1.0
        self._apply_font_scale()
        save_font_scale(self.font_scale)

    def _build_ui(self) -> None:
        # Top bar
        top = ctk.CTkFrame(self.root, fg_color=P["bg"], height=56)
        top.pack(fill="x", padx=16, pady=(12, 4))
        top.pack_propagate(False)

        self.title_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            top,
            textvariable=self.title_var,
            text_color=P["text"],
            font=self.title_font,
        ).pack(side="left")

        ctk.CTkButton(
            top, text="+ Add", width=130, corner_radius=8,
            fg_color=P["primary"], hover_color=P["primary_hv"],
            text_color="white",
            font=self.switch_font,
            command=self.add_dialog,
        ).pack(side="right")

        ctk.CTkButton(
            top, text="Search", width=90, corner_radius=8,
            fg_color=P["soft"], hover_color=P["border"],
            text_color=P["primary"],
            font=self.switch_font,
            command=self.search_dialog,
        ).pack(side="right", padx=8)

        ctk.CTkSwitch(
            top, text="Shuffle", variable=self.shuffled,
            progress_color=P["primary"],
            font=self.switch_font,
            command=lambda: self.reload(reset_index=True),
        ).pack(side="right", padx=8)

        ctk.CTkSwitch(
            top, text="Show backlog", variable=self.show_backlog,
            progress_color=P["primary"],
            font=self.switch_font,
            command=lambda: self.reload(reset_index=True),
        ).pack(side="right", padx=8)

        ctk.CTkButton(
            top, text="A+", width=36, corner_radius=8,
            fg_color=P["soft"], hover_color=P["border"],
            text_color=P["primary"], font=self.switch_font,
            command=lambda: self._bump_font(0.1),
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            top, text="A−", width=36, corner_radius=8,
            fg_color=P["soft"], hover_color=P["border"],
            text_color=P["primary"], font=self.switch_font,
            command=lambda: self._bump_font(-0.1),
        ).pack(side="right", padx=(0, 4))

        # Scrollable content (vertical only)
        self.scroll = ctk.CTkScrollableFrame(self.root, fg_color=P["bg"])
        self.scroll.pack(fill="both", expand=True, padx=16, pady=8)
        scroll = self.scroll

        # Scenario card — a wrapping label that grows to fit its text, so the
        # whole window scrolls if the scenario is long (no fixed height).
        sc = card(scroll)
        sc.pack(fill="x", pady=6)
        section_label(sc, "Scenario", font=self.section_font).pack(anchor="w", padx=16, pady=(12, 4))
        self.scenario_label = ctk.CTkLabel(
            sc, text="", font=self.body_font, text_color=P["text"],
            justify="left", anchor="w", wraplength=self._scenario_wrap,
        )
        self.scenario_label.pack(fill="x", padx=16, pady=(0, 12))
        sc.bind("<Configure>", self._on_scenario_resize)

        # Question card
        qc = card(scroll)
        qc.pack(fill="x", pady=6)
        section_label(qc, "Question", font=self.section_font).pack(anchor="w", padx=16, pady=(12, 4))
        self.question_text = readonly_textbox(qc, height=64, font=self.body_font)
        self.question_text.pack(fill="x", padx=16, pady=(0, 12))

        # Options card
        oc = card(scroll)
        oc.pack(fill="x", pady=6)
        section_label(oc, "Options", font=self.section_font).pack(anchor="w", padx=16, pady=(12, 4))
        self.options_frame = ctk.CTkFrame(oc, fg_color="transparent")
        self.options_frame.pack(fill="x", padx=16, pady=(0, 12))
        self.options_frame.bind("<Configure>", self._on_options_resize)

        # Action buttons row
        actions = ctk.CTkFrame(scroll, fg_color="transparent")
        actions.pack(fill="x", pady=10)

        self.submit_btn = ctk.CTkButton(
            actions, text="Submit", width=130, height=40, corner_radius=10,
            fg_color=P["accent"], hover_color=P["accent_hv"],
            text_color="white",
            font=self.button_font,
            command=self.submit,
        )
        self.submit_btn.pack(side="left")

        ctk.CTkButton(
            actions, text="< Previous", width=110, height=40, corner_radius=10,
            fg_color=P["soft"], hover_color=P["border"],
            text_color=P["primary"],
            font=self.switch_font,
            command=self.prev,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            actions, text="Next >", width=110, height=40, corner_radius=10,
            fg_color=P["soft"], hover_color=P["border"],
            text_color=P["primary"],
            font=self.switch_font,
            command=self.next,
        ).pack(side="left", padx=0)

        ctk.CTkButton(
            actions, text="Jump", width=90, height=40, corner_radius=10,
            fg_color=P["soft"], hover_color=P["border"],
            text_color=P["primary"],
            font=self.switch_font,
            command=self.jump_dialog,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            actions, text="Edit", width=90, height=40, corner_radius=10,
            fg_color=P["soft"], hover_color=P["border"],
            text_color=P["primary"],
            font=self.switch_font,
            command=self.edit_dialog,
        ).pack(side="left", padx=0)

        ctk.CTkButton(
            actions, text="Hotkeys", width=90, height=40, corner_radius=10,
            fg_color=P["soft"], hover_color=P["border"],
            text_color=P["primary"],
            font=self.switch_font,
            command=self.show_hotkeys,
        ).pack(side="left", padx=8)

        self.move_btn = ctk.CTkButton(
            actions, text="Move to Backlog", width=160, height=40, corner_radius=10,
            fg_color="transparent", hover_color=P["soft"],
            text_color=P["primary"],
            border_color=P["primary"], border_width=1,
            font=self.switch_font,
            command=self.toggle_backlog,
        )
        self.move_btn.pack(side="right")

        # Explanation card — a wrapping label that grows to fit its text, so the
        # whole window scrolls if the explanation is long (no inner scrollbar).
        ec = card(scroll)
        ec.pack(fill="x", pady=6)
        section_label(ec, "Explanation", font=self.section_font).pack(anchor="w", padx=16, pady=(12, 4))
        self.explanation_label = ctk.CTkLabel(
            ec, text="", font=self.body_font, text_color=P["text"],
            justify="left", anchor="w", wraplength=self._explanation_wrap,
        )
        self.explanation_label.pack(fill="x", padx=16, pady=(0, 12))
        ec.bind("<Configure>", self._on_explanation_resize)

    # ---- data ----

    def current_dir(self) -> Path:
        return BACKLOG_DIR if self.show_backlog.get() else ACTIVE_DIR

    def reload(self, reset_index: bool = False) -> None:
        d = self.current_dir()
        d.mkdir(parents=True, exist_ok=True)
        files = sorted(d.glob("q-*.md"))
        if self.shuffled.get():
            random.shuffle(files)
        self.items = files
        if reset_index or self.index >= len(self.items):
            self.index = 0
        self.move_btn.configure(text="Restore to Active" if self.show_backlog.get() else "Move to Backlog")
        self.render()

    def render(self) -> None:
        # Keep keyboard focus on the window (not a clicked checkbox/button) so
        # <space> only triggers Submit, never a focused widget as well.
        self.root.focus_set()
        for w in self.options_frame.winfo_children():
            w.destroy()
        self.checkboxes = []
        self.check_vars = []
        self.option_labels = []
        self.submitted = False
        self.submit_btn.configure(state="normal", fg_color=P["accent"])

        mode = "backlog" if self.show_backlog.get() else "active"
        if not self.items:
            self.title_var.set(f"({mode}) — no questions")
            self.current = None
            self.scenario_label.configure(text="")
            set_text(self.question_text, "")
            self.explanation_label.configure(text="")
            return

        path = self.items[self.index]
        self.current = parse_md(path)
        self.title_var.set(f"{path.name}      {self.index + 1} of {len(self.items)}")
        self.scenario_label.configure(text=self.current["scenario"])
        set_text(self.question_text, self.current["question"])
        self.explanation_label.configure(text="")

        for i, opt in enumerate(self.current["options"], 1):
            var = ctk.BooleanVar(value=False)
            row = ctk.CTkFrame(self.options_frame, fg_color="transparent")
            row.pack(anchor="w", fill="x", pady=4)
            cb = ctk.CTkCheckBox(
                row,
                text="",
                variable=var,
                width=24,
                fg_color=P["primary"],
                hover_color=P["primary_hv"],
                checkbox_width=20, checkbox_height=20,
                corner_radius=4,
                command=lambda: self.root.focus_set(),
            )
            cb.pack(side="left", anchor="n", pady=(1, 0))
            lbl = ctk.CTkLabel(
                row,
                text=f"{i}.  {opt}",
                font=self.option_font,
                text_color=P["text"],
                justify="left",
                anchor="w",
                wraplength=self._option_wrap,
            )
            lbl.pack(side="left", fill="x", expand=True, padx=(6, 0))
            # clicking the text toggles the option too
            lbl.bind("<Button-1>", lambda _e, v=var: (v.set(not v.get()), self.root.focus_set()))
            self.checkboxes.append(cb)
            self.check_vars.append(var)
            self.option_labels.append(lbl)

    # ---- actions ----

    def submit(self) -> None:
        if not self.current or self.submitted:
            return
        self.submitted = True
        self.submit_btn.configure(state="disabled", fg_color=P["muted"])
        correct_set = set(self.current["correct"])
        for i, var in enumerate(self.check_vars, 1):
            picked = var.get()
            is_correct = i in correct_set
            text = self.current["options"][i - 1]
            lbl = self.option_labels[i - 1]
            if is_correct and picked:
                lbl.configure(text=f"✓  {i}.  {text}   (correct)", text_color=P["ok"])
            elif is_correct and not picked:
                lbl.configure(text=f"●  {i}.  {text}   (was correct)", text_color=P["accent_hv"])
            elif picked and not is_correct:
                lbl.configure(text=f"✗  {i}.  {text}   (wrong)", text_color=P["bad"])
            else:
                lbl.configure(text_color=P["muted"])
        self.explanation_label.configure(text=self.current["explanation"])

    def _toggle_option(self, i: int) -> None:
        if self.submitted or i < 1 or i > len(self.check_vars):
            return
        var = self.check_vars[i - 1]
        var.set(not var.get())

    def _scroll(self, units: int) -> None:
        try:
            self.scroll._parent_canvas.yview_scroll(units, "units")
        except Exception:
            pass

    def _on_options_resize(self, event) -> None:
        wrap = max(200, event.width - 40)
        if wrap == self._option_wrap:
            return
        self._option_wrap = wrap
        for lbl in self.option_labels:
            lbl.configure(wraplength=wrap)

    def _on_explanation_resize(self, event) -> None:
        wrap = max(200, event.width - 32)
        if wrap == self._explanation_wrap:
            return
        self._explanation_wrap = wrap
        self.explanation_label.configure(wraplength=wrap)

    def _on_scenario_resize(self, event) -> None:
        wrap = max(200, event.width - 32)
        if wrap == self._scenario_wrap:
            return
        self._scenario_wrap = wrap
        self.scenario_label.configure(wraplength=wrap)

    def jump_dialog(self) -> None:
        if not self.items:
            return
        JumpDialog(self.root, len(self.items), self.index + 1, "question", self._jump_to)

    def _jump_to(self, n: int) -> None:
        if not self.items:
            return
        self.index = max(0, min(len(self.items) - 1, n - 1))
        self.render()

    def search_dialog(self) -> None:
        if not self.items:
            return
        SearchDialog(self.root, self.items, self._jump_to_path)

    def _jump_to_path(self, path: Path) -> None:
        for i, p in enumerate(self.items):
            if p == path:
                self.index = i
                self.render()
                return

    def next(self) -> None:
        if not self.items:
            return
        self.index = (self.index + 1) % len(self.items)
        self.render()

    def prev(self) -> None:
        if not self.items:
            return
        self.index = (self.index - 1) % len(self.items)
        self.render()

    def toggle_backlog(self) -> None:
        if not self.current:
            return
        src = self.current["path"]
        dst_dir = ACTIVE_DIR if self.show_backlog.get() else BACKLOG_DIR
        dst = unique_target(dst_dir, src.name)
        shutil.move(str(src), str(dst))
        prev_index = self.index
        self.reload()
        if self.items:
            self.index = min(prev_index, len(self.items) - 1)
            self.render()

    # ---- add dialog ----

    def add_dialog(self) -> None:
        AddQuestionDialog(self.root, on_save=self._save_new)

    def edit_dialog(self) -> None:
        if not self.current:
            return
        AddQuestionDialog(self.root, on_save=self._save_edit, initial=self.current)

    def show_hotkeys(self) -> None:
        rows = [
            ("← / A", "Previous question"),
            ("→ / D", "Next question"),
            ("↑ / W", "Scroll up"),
            ("↓ / S", "Scroll down"),
            ("Space / Enter", "Submit"),
            ("1 – 7", "Toggle that option"),
            ("G", "Jump to a question"),
            ("F / / / Ctrl+F", "Search questions by text"),
            ("E", "Edit current question"),
            ("B", "Move to / restore from backlog"),
            ("Ctrl + N", "Add a new question"),
            ("Ctrl + +/-/0", "Font larger / smaller / reset"),
            ("F11 / Esc", "Toggle / exit fullscreen"),
        ]

        top = ctk.CTkToplevel(self.root)
        top.title("Hotkeys")
        top.configure(fg_color=P["bg"])
        top.transient(self.root)
        top.after(50, top.grab_set)
        top.bind("<Escape>", lambda _e: top.destroy())

        frame = ctk.CTkFrame(top, fg_color="transparent")
        frame.pack(padx=24, pady=20)
        frame.grid_columnconfigure(0, weight=0)
        frame.grid_columnconfigure(1, weight=1)

        key_font = ctk.CTkFont(family="monospace", size=13)
        for r, (key, action) in enumerate(rows):
            ctk.CTkLabel(frame, text=key, text_color=P["primary"], font=key_font,
                         anchor="w").grid(row=r, column=0, sticky="w", padx=(0, 24), pady=3)
            ctk.CTkLabel(frame, text=action, text_color=P["text"],
                         anchor="w").grid(row=r, column=1, sticky="w", pady=3)

    def _save_edit(self, scenario: str, question: str, options: list[str], correct: list[int], explanation: str) -> None:
        if not self.current:
            return
        # In-place edit of the single current item; the file set is unchanged,
        # so just rewrite and re-render the same index.
        write_md(self.current["path"], scenario, question, options, correct, explanation)
        self.render()

    def _save_new(self, scenario: str, question: str, options: list[str], correct: list[int], explanation: str) -> None:
        ACTIVE_DIR.mkdir(parents=True, exist_ok=True)
        idx = next_index(ACTIVE_DIR)
        path = ACTIVE_DIR / f"q-{idx:04d}.md"
        write_md(path, scenario, question, options, correct, explanation)
        if not self.show_backlog.get():
            self.reload()
            for i, p in enumerate(self.items):
                if p == path:
                    self.index = i
                    self.render()
                    break

    def run(self) -> None:
        self.root.mainloop()


class AddQuestionDialog:
    def __init__(self, parent, on_save, initial: dict | None = None) -> None:
        self.on_save = on_save
        self.top = ctk.CTkToplevel(parent)
        self.top.title("Edit Question" if initial else "Add Question")
        self.top.geometry("720x780")
        self.top.configure(fg_color=P["bg"])
        self.top.transient(parent)
        self.top.after(50, self.top.grab_set)

        self.font_scale = load_font_scale(DIALOG_STATE_KEY)
        self._fonts: list[tuple[ctk.CTkFont, int, str]] = []
        input_font = self._font(16)

        # Action bar — pinned to the bottom of the window (outside the scroll
        # area) so it stays put and full-size when the input fonts grow.
        btns = ctk.CTkFrame(self.top, fg_color="transparent")
        btns.pack(side="bottom", fill="x", padx=16, pady=(0, 12))
        ctk.CTkButton(btns, text="Cancel", corner_radius=8, fg_color=P["soft"],
                      hover_color=P["border"], text_color=P["primary"],
                      command=self.top.destroy).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Save", corner_radius=8, fg_color=P["primary"],
                      hover_color=P["primary_hv"], text_color="white",
                      command=self._save).pack(side="right")

        frm = ctk.CTkScrollableFrame(self.top, fg_color=P["bg"])
        frm.pack(fill="both", expand=True, padx=16, pady=12)

        fontbar = ctk.CTkFrame(frm, fg_color="transparent")
        fontbar.pack(fill="x", pady=(0, 4))
        ctk.CTkButton(fontbar, text="A+", width=36, corner_radius=8,
                      fg_color=P["soft"], hover_color=P["border"],
                      text_color=P["primary"],
                      command=lambda: self._bump_font(0.1)).pack(side="right", padx=(6, 0))
        ctk.CTkButton(fontbar, text="A−", width=36, corner_radius=8,
                      fg_color=P["soft"], hover_color=P["border"],
                      text_color=P["primary"],
                      command=lambda: self._bump_font(-0.1)).pack(side="right")

        section_label(frm, "Scenario").pack(anchor="w", pady=(0, 4))
        self.scenario = ctk.CTkTextbox(frm, height=110, wrap="word", fg_color=P["surface"],
                                       border_width=1, border_color=P["border"],
                                       text_color=P["text"], font=input_font)
        self.scenario.pack(fill="x", pady=(0, 8))

        section_label(frm, "Question").pack(anchor="w", pady=(0, 4))
        self.question = ctk.CTkTextbox(frm, height=60, wrap="word", fg_color=P["surface"],
                                       border_width=1, border_color=P["border"],
                                       text_color=P["text"], font=input_font)
        self.question.pack(fill="x", pady=(0, 8))

        section_label(frm, "Options (one per line, 2 to 7)").pack(anchor="w", pady=(0, 4))
        self.options = ctk.CTkTextbox(frm, height=150, wrap="word", fg_color=P["surface"],
                                      border_width=1, border_color=P["border"],
                                      text_color=P["text"], font=input_font)
        self.options.pack(fill="x", pady=(0, 8))

        section_label(frm, "Correct option numbers, comma-separated (e.g. 1,3)").pack(anchor="w", pady=(0, 4))
        self.correct = ctk.CTkEntry(frm, fg_color=P["surface"],
                                    border_color=P["border"], text_color=P["text"],
                                    font=input_font)
        self.correct.pack(fill="x", pady=(0, 8))

        section_label(frm, "Explanation").pack(anchor="w", pady=(0, 4))
        self.explanation = ctk.CTkTextbox(frm, height=160, wrap="word", fg_color=P["surface"],
                                          border_width=1, border_color=P["border"],
                                          text_color=P["text"], font=input_font)
        self.explanation.pack(fill="x", pady=(0, 8))

        if initial:
            self.scenario.insert("1.0", initial.get("scenario", ""))
            self.question.insert("1.0", initial.get("question", ""))
            self.options.insert("1.0", "\n".join(initial.get("options", [])))
            self.correct.insert(0, ",".join(str(i) for i in initial.get("correct", [])))
            self.explanation.insert("1.0", initial.get("explanation", ""))

        # Ctrl+S saves, Esc cancels (bound on the Toplevel so they fire from any
        # focused field). Ctrl +/-/0 scale the input fields like the main window.
        self.top.bind("<Control-s>", lambda _e: self._save())
        self.top.bind("<Escape>", lambda _e: self.top.destroy())
        self.top.bind("<Control-w>", lambda _e: self.top.destroy())
        self.top.bind("<Control-plus>", lambda _e: self._bump_font(0.1))
        self.top.bind("<Control-equal>", lambda _e: self._bump_font(0.1))
        self.top.bind("<Control-minus>", lambda _e: self._bump_font(-0.1))
        self.top.bind("<Control-0>", lambda _e: self._reset_font())

    def _font(self, size: int, weight: str = "normal") -> ctk.CTkFont:
        f = ctk.CTkFont(size=max(8, int(round(size * self.font_scale))), weight=weight)
        self._fonts.append((f, size, weight))
        return f

    def _apply_font_scale(self) -> None:
        for f, base, _weight in self._fonts:
            f.configure(size=max(8, int(round(base * self.font_scale))))

    def _bump_font(self, delta: float) -> None:
        new = max(0.7, min(2.5, round(self.font_scale + delta, 2)))
        if new == self.font_scale:
            return
        self.font_scale = new
        self._apply_font_scale()
        save_font_scale(self.font_scale, DIALOG_STATE_KEY)

    def _reset_font(self) -> None:
        if self.font_scale == 1.0:
            return
        self.font_scale = 1.0
        self._apply_font_scale()
        save_font_scale(self.font_scale, DIALOG_STATE_KEY)

    def _save(self) -> None:
        scenario = self.scenario.get("1.0", "end").strip()
        question = self.question.get("1.0", "end").strip()
        opts_text = self.options.get("1.0", "end").strip()
        options = [ln.strip() for ln in opts_text.splitlines() if ln.strip()]
        explanation = self.explanation.get("1.0", "end").strip()
        correct_raw = self.correct.get().strip()

        if not (2 <= len(options) <= 7):
            messagebox.showerror("Validation", "Need 2 to 7 options.", parent=self.top)
            return
        if not scenario and not question:
            messagebox.showerror("Validation", "Provide a Scenario or a Question (at least one).", parent=self.top)
            return
        try:
            correct = sorted({int(p.strip()) for p in correct_raw.split(",") if p.strip()})
        except ValueError:
            messagebox.showerror("Validation", "Correct must be comma-separated numbers.", parent=self.top)
            return
        if not correct or any(i < 1 or i > len(options) for i in correct):
            messagebox.showerror("Validation", "Correct option numbers must be within range.", parent=self.top)
            return

        self.on_save(scenario, question, options, correct, explanation)
        self.top.destroy()


class SearchDialog:
    """Live text search over the current question set.

    Matches against scenario, question, options and explanation. Clicking a
    result (or pressing Enter to open the first match) jumps to that question.
    """

    def __init__(self, parent, items: list[Path], on_go) -> None:
        self.on_go = on_go
        self.records: list[tuple[Path, list[tuple[str, str]]]] = []
        for p in items:
            try:
                d = parse_md(p)
            except OSError:
                continue
            fields = [
                ("Scenario", d["scenario"]),
                ("Question", d["question"]),
                ("Options", "   •   ".join(d["options"])),
                ("Explanation", d["explanation"]),
            ]
            self.records.append((p, fields))

        self.top = ctk.CTkToplevel(parent)
        self.top.title("Search questions")
        self.top.geometry("680x560")
        self.top.configure(fg_color=P["bg"])
        self.top.transient(parent)
        self.top.after(50, self.top.grab_set)

        self.entry = ctk.CTkEntry(
            self.top,
            placeholder_text="Search text in scenario, question, options, explanation…",
            fg_color=P["surface"], border_color=P["border"], text_color=P["text"],
        )
        self.entry.pack(fill="x", padx=16, pady=(16, 8))
        self.entry.focus_set()
        self.entry.bind("<KeyRelease>", lambda _e: self._refresh())
        self.entry.bind("<Return>", lambda _e: self._open_first())
        self.entry.bind("<Escape>", lambda _e: self.top.destroy())

        self.count_var = ctk.StringVar(value="")
        ctk.CTkLabel(self.top, textvariable=self.count_var, text_color=P["muted"],
                     anchor="w").pack(fill="x", padx=16)

        self.results = ctk.CTkScrollableFrame(self.top, fg_color=P["bg"])
        self.results.pack(fill="both", expand=True, padx=16, pady=(4, 16))

        self._matches: list[Path] = []
        self._refresh()

    @staticmethod
    def _snippet(fields: list[tuple[str, str]], query: str) -> tuple[str, str] | None:
        for name, text in fields:
            pos = text.lower().find(query)
            if pos == -1:
                continue
            start = max(0, pos - 30)
            end = min(len(text), pos + len(query) + 50)
            snippet = text[start:end].replace("\n", " ").strip()
            if start > 0:
                snippet = "…" + snippet
            if end < len(text):
                snippet = snippet + "…"
            return name, snippet
        return None

    def _refresh(self) -> None:
        for w in self.results.winfo_children():
            w.destroy()
        self._matches = []
        query = self.entry.get().strip().lower()
        if not query:
            self.count_var.set(f"{len(self.records)} questions — type to search")
            return
        for p, fields in self.records:
            hit = self._snippet(fields, query)
            if hit is None:
                continue
            self._matches.append(p)
            name, snippet = hit
            ctk.CTkButton(
                self.results, anchor="w", corner_radius=8, height=44,
                fg_color=P["surface"], hover_color=P["soft"],
                text_color=P["text"], border_width=1, border_color=P["border"],
                text=f"{p.name}   ·   {name}: {snippet}",
                command=lambda pp=p: self._go(pp),
            ).pack(fill="x", pady=3)
        n = len(self._matches)
        self.count_var.set(f"{n} match{'es' if n != 1 else ''}")

    def _open_first(self) -> None:
        if self._matches:
            self._go(self._matches[0])

    def _go(self, path: Path) -> None:
        self.top.destroy()
        self.on_go(path)


class JumpDialog:
    def __init__(self, parent, count: int, current: int, noun: str, on_go) -> None:
        self.on_go = on_go
        self.top = ctk.CTkToplevel(parent)
        self.top.title(f"Jump to {noun}")
        self.top.geometry("320x160")
        self.top.configure(fg_color=P["bg"])
        self.top.transient(parent)
        self.top.after(50, self.top.grab_set)

        ctk.CTkLabel(self.top, text=f"Go to {noun} #  (1 – {count})",
                     text_color=P["text"]).pack(padx=16, pady=(20, 6))
        self.entry = ctk.CTkEntry(self.top, justify="center", fg_color=P["surface"],
                                  border_color=P["border"], text_color=P["text"])
        self.entry.insert(0, str(current))
        self.entry.pack(padx=16, pady=4)
        self.entry.select_range(0, "end")
        self.entry.focus_set()
        self.entry.bind("<Return>", lambda _e: self._go())
        self.entry.bind("<Escape>", lambda _e: self.top.destroy())

        btns = ctk.CTkFrame(self.top, fg_color="transparent")
        btns.pack(pady=12)
        ctk.CTkButton(btns, text="Cancel", width=80, corner_radius=8, fg_color=P["soft"],
                      hover_color=P["border"], text_color=P["primary"],
                      command=self.top.destroy).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Go", width=80, corner_radius=8, fg_color=P["primary"],
                      hover_color=P["primary_hv"], text_color="white",
                      command=self._go).pack(side="right")

    def _go(self) -> None:
        raw = self.entry.get().strip()
        if raw.isdigit():
            self.on_go(int(raw))
        self.top.destroy()


def main() -> None:
    ACTIVE_DIR.mkdir(parents=True, exist_ok=True)
    BACKLOG_DIR.mkdir(parents=True, exist_ok=True)
    QuestionsApp().run()


if __name__ == "__main__":
    main()
