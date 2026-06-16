"""Multiple-choice exam practice app (customtkinter, orange/amber palette).

Run:
    pip install customtkinter
    python3 questions_app.py
"""
from __future__ import annotations

import random
import re
import shutil
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

ROOT = Path(__file__).resolve().parent
ACTIVE_DIR = ROOT / "data" / "questions" / "active"
BACKLOG_DIR = ROOT / "data" / "questions" / "backlog"

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
        self.submitted = False

        self.font_scale = 1.0
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

    def _reset_font(self) -> None:
        if self.font_scale == 1.0:
            return
        self.font_scale = 1.0
        self._apply_font_scale()

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
            top, text="+ Add  (Ctrl+N)", width=130, corner_radius=8,
            fg_color=P["primary"], hover_color=P["primary_hv"],
            text_color="white",
            font=self.switch_font,
            command=self.add_dialog,
        ).pack(side="right")

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

        # Scrollable content
        scroll = ctk.CTkScrollableFrame(self.root, fg_color=P["bg"])
        scroll.pack(fill="both", expand=True, padx=16, pady=8)

        # Scenario card
        sc = card(scroll)
        sc.pack(fill="x", pady=6)
        section_label(sc, "Scenario", font=self.section_font).pack(anchor="w", padx=16, pady=(12, 4))
        self.scenario_text = readonly_textbox(sc, height=120, font=self.body_font)
        self.scenario_text.pack(fill="x", padx=16, pady=(0, 12))

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

        self.move_btn = ctk.CTkButton(
            actions, text="Move to Backlog", width=160, height=40, corner_radius=10,
            fg_color="transparent", hover_color=P["soft"],
            text_color=P["primary"],
            border_color=P["primary"], border_width=1,
            font=self.switch_font,
            command=self.toggle_backlog,
        )
        self.move_btn.pack(side="right")

        # Explanation card
        ec = card(scroll)
        ec.pack(fill="both", expand=True, pady=6)
        section_label(ec, "Explanation", font=self.section_font).pack(anchor="w", padx=16, pady=(12, 4))
        self.explanation_text = readonly_textbox(ec, height=220, font=self.body_font)
        self.explanation_text.pack(fill="both", expand=True, padx=16, pady=(0, 12))

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
        for w in self.options_frame.winfo_children():
            w.destroy()
        self.checkboxes = []
        self.check_vars = []
        self.submitted = False
        self.submit_btn.configure(state="normal", fg_color=P["accent"])

        mode = "backlog" if self.show_backlog.get() else "active"
        if not self.items:
            self.title_var.set(f"({mode}) — no questions")
            self.current = None
            set_text(self.scenario_text, "")
            set_text(self.question_text, "")
            set_text(self.explanation_text, "")
            return

        path = self.items[self.index]
        self.current = parse_md(path)
        self.title_var.set(f"{path.name}      {self.index + 1} of {len(self.items)}")
        set_text(self.scenario_text, self.current["scenario"])
        set_text(self.question_text, self.current["question"])
        set_text(self.explanation_text, "")

        for i, opt in enumerate(self.current["options"], 1):
            var = ctk.BooleanVar(value=False)
            cb = ctk.CTkCheckBox(
                self.options_frame,
                text=f"{i}.  {opt}",
                variable=var,
                fg_color=P["primary"],
                hover_color=P["primary_hv"],
                text_color=P["text"],
                font=self.option_font,
                checkbox_width=20, checkbox_height=20,
                corner_radius=4,
            )
            cb.pack(anchor="w", fill="x", pady=4)
            self.checkboxes.append(cb)
            self.check_vars.append(var)

    # ---- actions ----

    def submit(self) -> None:
        if not self.current or self.submitted:
            return
        self.submitted = True
        self.submit_btn.configure(state="disabled", fg_color=P["muted"])
        correct_set = set(self.current["correct"])
        for i, (cb, var) in enumerate(zip(self.checkboxes, self.check_vars), 1):
            picked = var.get()
            is_correct = i in correct_set
            text = self.current["options"][i - 1]
            if is_correct and picked:
                cb.configure(text=f"✓  {i}.  {text}   (correct)", text_color=P["ok"])
            elif is_correct and not picked:
                cb.configure(text=f"●  {i}.  {text}   (was correct)", text_color=P["accent_hv"])
            elif picked and not is_correct:
                cb.configure(text=f"✗  {i}.  {text}   (wrong)", text_color=P["bad"])
            else:
                cb.configure(text_color=P["muted"])
        set_text(self.explanation_text, self.current["explanation"])

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
    def __init__(self, parent, on_save) -> None:
        self.on_save = on_save
        self.top = ctk.CTkToplevel(parent)
        self.top.title("Add Question")
        self.top.geometry("720x780")
        self.top.configure(fg_color=P["bg"])
        self.top.transient(parent)
        self.top.after(50, self.top.grab_set)

        frm = ctk.CTkScrollableFrame(self.top, fg_color=P["bg"])
        frm.pack(fill="both", expand=True, padx=16, pady=12)

        section_label(frm, "Scenario").pack(anchor="w", pady=(0, 4))
        self.scenario = ctk.CTkTextbox(frm, height=110, wrap="word", fg_color=P["surface"],
                                       border_width=1, border_color=P["border"],
                                       text_color=P["text"])
        self.scenario.pack(fill="x", pady=(0, 8))

        section_label(frm, "Question").pack(anchor="w", pady=(0, 4))
        self.question = ctk.CTkTextbox(frm, height=60, wrap="word", fg_color=P["surface"],
                                       border_width=1, border_color=P["border"],
                                       text_color=P["text"])
        self.question.pack(fill="x", pady=(0, 8))

        section_label(frm, "Options (one per line, 2 to 7)").pack(anchor="w", pady=(0, 4))
        self.options = ctk.CTkTextbox(frm, height=150, wrap="word", fg_color=P["surface"],
                                      border_width=1, border_color=P["border"],
                                      text_color=P["text"])
        self.options.pack(fill="x", pady=(0, 8))

        section_label(frm, "Correct option numbers, comma-separated (e.g. 1,3)").pack(anchor="w", pady=(0, 4))
        self.correct = ctk.CTkEntry(frm, fg_color=P["surface"],
                                    border_color=P["border"], text_color=P["text"])
        self.correct.pack(fill="x", pady=(0, 8))

        section_label(frm, "Explanation").pack(anchor="w", pady=(0, 4))
        self.explanation = ctk.CTkTextbox(frm, height=160, wrap="word", fg_color=P["surface"],
                                          border_width=1, border_color=P["border"],
                                          text_color=P["text"])
        self.explanation.pack(fill="x", pady=(0, 8))

        btns = ctk.CTkFrame(frm, fg_color="transparent")
        btns.pack(fill="x", pady=8)
        ctk.CTkButton(btns, text="Cancel", corner_radius=8, fg_color=P["soft"],
                      hover_color=P["border"], text_color=P["primary"],
                      command=self.top.destroy).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Save", corner_radius=8, fg_color=P["primary"],
                      hover_color=P["primary_hv"], text_color="white",
                      command=self._save).pack(side="right")

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
        if not question:
            messagebox.showerror("Validation", "Question is required.", parent=self.top)
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


def main() -> None:
    ACTIVE_DIR.mkdir(parents=True, exist_ok=True)
    BACKLOG_DIR.mkdir(parents=True, exist_ok=True)
    QuestionsApp().run()


if __name__ == "__main__":
    main()
