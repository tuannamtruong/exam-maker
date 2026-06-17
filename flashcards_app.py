"""Flashcard practice app (customtkinter, teal/blue palette).

Run:
    pip install customtkinter
    python3 flashcards_app.py
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
ACTIVE_DIR = ROOT / "data" / "flashcards" / "active"
BACKLOG_DIR = ROOT / "data" / "flashcards" / "backlog"

STATE_FILE = ROOT / ".app_state.json"
STATE_KEY = "flashcards_font_scale"


def load_font_scale() -> float:
    try:
        scale = json.loads(STATE_FILE.read_text()).get(STATE_KEY, 1.0)
        return max(0.7, min(2.5, float(scale)))
    except (OSError, ValueError, TypeError):
        return 1.0


def save_font_scale(scale: float) -> None:
    try:
        state = json.loads(STATE_FILE.read_text())
        if not isinstance(state, dict):
            state = {}
    except (OSError, ValueError):
        state = {}
    state[STATE_KEY] = scale
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except OSError:
        pass

SECTION_RE = re.compile(r"^#\s+(Front|Back)\s*$")

P = {
    "bg":         "#ECFEFF",  # cyan-50
    "surface":    "#FFFFFF",
    "primary":    "#0D9488",  # teal-600
    "primary_hv": "#0F766E",  # teal-700
    "accent":     "#0EA5E9",  # sky-500
    "accent_hv":  "#0284C7",  # sky-600
    "text":       "#0F172A",  # slate-900
    "muted":      "#475569",  # slate-600
    "border":     "#99F6E4",  # teal-200
    "soft":       "#CFFAFE",  # cyan-100
    "card_front": "#F0FDFA",  # teal-50 (front face)
    "card_back":  "#E0F2FE",  # sky-100 (back face — visual flip cue)
}


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

    sections: dict[str, list[str]] = {"Front": [], "Back": []}
    current = None
    for line in body.splitlines():
        m = SECTION_RE.match(line)
        if m:
            current = m.group(1)
            continue
        if current is not None:
            sections[current].append(line)

    return {
        "path": path,
        "category": fm.get("category", ""),
        "front": "\n".join(sections["Front"]).strip(),
        "back": "\n".join(sections["Back"]).strip(),
    }


def write_md(path: Path, category: str, front: str, back: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    parts = [
        "---", f"category: {category.strip()}", "---", "",
        "# Front", front.strip(), "",
        "# Back", back.strip(), "",
    ]
    path.write_text("\n".join(parts), encoding="utf-8")


def next_index(out_dir: Path) -> int:
    nums = []
    for p in out_dir.glob("fc-*.md"):
        m = re.match(r"fc-(\d+)$", p.stem)
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


class FlashcardsApp:
    def __init__(self) -> None:
        ctk.set_appearance_mode("light")

        self.root = ctk.CTk()
        self.root.title("Exam Practice — Flashcards")
        self.root.geometry("820x640")
        self.root.configure(fg_color=P["bg"])

        self.show_backlog = ctk.BooleanVar(value=False)
        self.shuffled = ctk.BooleanVar(value=False)
        self.items: list[Path] = []
        self.index = 0
        self.current: dict | None = None
        self.flipped = False

        self.font_scale = load_font_scale()
        self._fonts: list[tuple[ctk.CTkFont, int, str]] = []
        self.title_font = self._font(18, "bold")
        self.category_font = self._font(12, "bold")
        self.face_font = self._font(11, "bold")
        self.front_font = self._font(28, "bold")
        self.back_font = self._font(22)
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

        # Navigation / flip hotkeys (bound to the main window so the Add
        # dialog — a separate Toplevel — is unaffected while typing).
        self.root.bind("<space>", lambda _e: self.flip())
        for key in ("<Left>", "<KeyPress-a>", "<KeyPress-A>"):
            self.root.bind(key, lambda _e: self.prev())
        for key in ("<Right>", "<KeyPress-d>", "<KeyPress-D>"):
            self.root.bind(key, lambda _e: self.next())
        for key in ("<KeyPress-b>", "<KeyPress-B>"):
            self.root.bind(key, lambda _e: self.toggle_backlog())
        for key in ("<KeyPress-g>", "<KeyPress-G>"):
            self.root.bind(key, lambda _e: self.jump_dialog())
        for key in ("<KeyPress-e>", "<KeyPress-E>"):
            self.root.bind(key, lambda _e: self.edit_dialog())

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

        # Category strip
        self.category_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            self.root,
            textvariable=self.category_var,
            text_color=P["muted"],
            font=self.category_font,
        ).pack(anchor="w", padx=20, pady=(0, 4))

        # Card surface
        self.card = ctk.CTkFrame(
            self.root,
            fg_color=P["card_front"],
            corner_radius=16,
            border_width=1,
            border_color=P["border"],
        )
        self.card.pack(fill="both", expand=True, padx=20, pady=12)

        self.face_var = ctk.StringVar(value="FRONT — click to flip")
        ctk.CTkLabel(
            self.card,
            textvariable=self.face_var,
            text_color=P["primary"],
            font=self.face_font,
        ).pack(anchor="ne", padx=14, pady=10)

        # A Label (not a Textbox) so the content centres both horizontally and
        # vertically within the card. wraplength is kept in sync with the card
        # width via <Configure> below.
        self.card_text = ctk.CTkLabel(
            self.card,
            text="",
            text_color=P["text"],
            font=self.front_font,
            justify="center",
            wraplength=680,
        )
        self.card_text.pack(fill="both", expand=True, padx=36, pady=(0, 28))

        # click on the card area flips; resize keeps wrapping width current
        for w in (self.card, self.card_text):
            w.bind("<Button-1>", lambda _e: self.flip())
        self.card.bind("<Configure>", self._update_wraplength)

        # Buttons
        btns = ctk.CTkFrame(self.root, fg_color=P["bg"])
        btns.pack(fill="x", padx=16, pady=(4, 14))

        ctk.CTkButton(
            btns, text="Flip", width=120, height=40, corner_radius=10,
            fg_color=P["accent"], hover_color=P["accent_hv"],
            text_color="white",
            font=self.button_font,
            command=self.flip,
        ).pack(side="left")

        ctk.CTkButton(
            btns, text="< Previous", width=110, height=40, corner_radius=10,
            fg_color=P["soft"], hover_color=P["border"],
            text_color=P["primary"],
            font=self.switch_font,
            command=self.prev,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btns, text="Next >", width=110, height=40, corner_radius=10,
            fg_color=P["soft"], hover_color=P["border"],
            text_color=P["primary"],
            font=self.switch_font,
            command=self.next,
        ).pack(side="left")

        ctk.CTkButton(
            btns, text="Jump", width=100, height=40, corner_radius=10,
            fg_color=P["soft"], hover_color=P["border"],
            text_color=P["primary"],
            font=self.switch_font,
            command=self.jump_dialog,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btns, text="Edit", width=100, height=40, corner_radius=10,
            fg_color=P["soft"], hover_color=P["border"],
            text_color=P["primary"],
            font=self.switch_font,
            command=self.edit_dialog,
        ).pack(side="left")

        self.move_btn = ctk.CTkButton(
            btns, text="Move to Backlog", width=160, height=40, corner_radius=10,
            fg_color="transparent", hover_color=P["soft"],
            text_color=P["primary"],
            border_color=P["primary"], border_width=1,
            font=self.switch_font,
            command=self.toggle_backlog,
        )
        self.move_btn.pack(side="right")

    def current_dir(self) -> Path:
        return BACKLOG_DIR if self.show_backlog.get() else ACTIVE_DIR

    def reload(self, reset_index: bool = False) -> None:
        d = self.current_dir()
        d.mkdir(parents=True, exist_ok=True)
        files = sorted(d.glob("fc-*.md"))
        if self.shuffled.get():
            random.shuffle(files)
        self.items = files
        if reset_index or self.index >= len(self.items):
            self.index = 0
        self.move_btn.configure(text="Restore to Active" if self.show_backlog.get() else "Move to Backlog")
        self.render()

    def render(self) -> None:
        # Keep keyboard focus on the window (not on a clicked button) so that
        # <space> only triggers our flip bind, never a focused button as well.
        self.root.focus_set()
        self.flipped = False
        self.card.configure(fg_color=P["card_front"])
        mode = "backlog" if self.show_backlog.get() else "active"
        if not self.items:
            self.title_var.set(f"({mode}) — no cards")
            self.category_var.set("")
            self.current = None
            self._set_card("")
            self.face_var.set("")
            return
        path = self.items[self.index]
        self.current = parse_md(path)
        self.title_var.set(f"{path.name}      {self.index + 1} of {len(self.items)}")
        cat = self.current["category"]
        self.category_var.set(f"CATEGORY · {cat.upper()}" if cat else "")
        self._set_card(self.current["front"])
        self.face_var.set("FRONT — click to flip")

    def _set_card(self, content: str) -> None:
        self.card_text.configure(text=content)

    def _update_wraplength(self, event) -> None:
        self.card_text.configure(wraplength=max(200, event.width - 80))

    def flip(self) -> None:
        if not self.current:
            return
        # A mouse click on the Flip button leaves it focused; reclaim focus so a
        # subsequent <space> flips once (bind only) rather than twice.
        self.root.focus_set()
        self.flipped = not self.flipped
        if self.flipped:
            self.card.configure(fg_color=P["card_back"])
            self._set_card(self.current["back"])
            self.face_var.set("BACK — click to flip")
            self.card_text.configure(font=self.back_font)
        else:
            self.card.configure(fg_color=P["card_front"])
            self._set_card(self.current["front"])
            self.face_var.set("FRONT — click to flip")
            self.card_text.configure(font=self.front_font)

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

    def jump_dialog(self) -> None:
        if not self.items:
            return
        JumpDialog(self.root, len(self.items), self.index + 1, "card", self._jump_to)

    def _jump_to(self, n: int) -> None:
        if not self.items:
            return
        self.index = max(0, min(len(self.items) - 1, n - 1))
        self.render()

    def add_dialog(self) -> None:
        AddFlashcardDialog(self.root, on_save=self._save_new)

    def edit_dialog(self) -> None:
        if not self.current:
            return
        AddFlashcardDialog(self.root, on_save=self._save_edit, initial=self.current)

    def _save_edit(self, category: str, front: str, back: str) -> None:
        if not self.current:
            return
        # In-place edit of the single current card; the file set is unchanged.
        write_md(self.current["path"], category, front, back)
        self.render()

    def _save_new(self, category: str, front: str, back: str) -> None:
        ACTIVE_DIR.mkdir(parents=True, exist_ok=True)
        idx = next_index(ACTIVE_DIR)
        path = ACTIVE_DIR / f"fc-{idx:04d}.md"
        write_md(path, category, front, back)
        if not self.show_backlog.get():
            self.reload()
            for i, p in enumerate(self.items):
                if p == path:
                    self.index = i
                    self.render()
                    break

    def run(self) -> None:
        self.root.mainloop()


class AddFlashcardDialog:
    def __init__(self, parent, on_save, initial: dict | None = None) -> None:
        self.on_save = on_save
        self.top = ctk.CTkToplevel(parent)
        self.top.title("Edit Flashcard" if initial else "Add Flashcard")
        self.top.geometry("620x560")
        self.top.configure(fg_color=P["bg"])
        self.top.transient(parent)
        self.top.after(50, self.top.grab_set)

        frm = ctk.CTkFrame(self.top, fg_color=P["bg"])
        frm.pack(fill="both", expand=True, padx=16, pady=12)

        def label(text):
            return ctk.CTkLabel(frm, text=text.upper(),
                                text_color=P["primary"],
                                font=ctk.CTkFont(size=11, weight="bold"),
                                anchor="w")

        label("Category").pack(anchor="w", pady=(0, 4))
        self.category = ctk.CTkEntry(frm, fg_color=P["surface"],
                                     border_color=P["border"], text_color=P["text"])
        self.category.pack(fill="x", pady=(0, 8))

        label("Front").pack(anchor="w", pady=(0, 4))
        self.front = ctk.CTkTextbox(frm, height=80, wrap="word", fg_color=P["surface"],
                                    border_width=1, border_color=P["border"],
                                    text_color=P["text"])
        self.front.pack(fill="x", pady=(0, 8))

        label("Back").pack(anchor="w", pady=(0, 4))
        self.back = ctk.CTkTextbox(frm, height=240, wrap="word", fg_color=P["surface"],
                                   border_width=1, border_color=P["border"],
                                   text_color=P["text"])
        self.back.pack(fill="both", expand=True, pady=(0, 8))

        if initial:
            self.category.insert(0, initial.get("category", ""))
            self.front.insert("1.0", initial.get("front", ""))
            self.back.insert("1.0", initial.get("back", ""))

        btns = ctk.CTkFrame(frm, fg_color="transparent")
        btns.pack(fill="x", pady=8)
        ctk.CTkButton(btns, text="Cancel", corner_radius=8, fg_color=P["soft"],
                      hover_color=P["border"], text_color=P["primary"],
                      command=self.top.destroy).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Save", corner_radius=8, fg_color=P["primary"],
                      hover_color=P["primary_hv"], text_color="white",
                      command=self._save).pack(side="right")

        # Ctrl+S saves, Esc cancels (bound on the Toplevel so they fire from any
        # focused field).
        self.top.bind("<Control-s>", lambda _e: self._save())
        self.top.bind("<Escape>", lambda _e: self.top.destroy())
        self.top.bind("<Control-w>", lambda _e: self.top.destroy())

    def _save(self) -> None:
        category = self.category.get().strip()
        front = self.front.get("1.0", "end").strip()
        back = self.back.get("1.0", "end").strip()
        if not front:
            messagebox.showerror("Validation", "Front is required.", parent=self.top)
            return
        self.on_save(category, front, back)
        self.top.destroy()


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
    FlashcardsApp().run()


if __name__ == "__main__":
    main()
