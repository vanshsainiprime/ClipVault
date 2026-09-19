"""
ClipVault GUI — a professional, minimal desktop interface for browsing and
managing clipboard history stored by the ClipVault daemon.

This file only READS from the existing Database and calls its mutation
methods (pin/unpin/delete/clear). It never starts a clipboard watcher.

NOTE: Written without direct access to your real clipvault/database.py.
It assumes the method names given in the project spec:

    get_recent(limit=None) -> list of rows
    search(query, limit=None) -> list of rows
    get_by_id(id) -> row
    delete(id)
    pin(id)
    unpin(id)
    clear()
    count() -> int

Each "row" is read defensively (works whether it's a dict, sqlite3.Row,
or a simple object) via _field(). If your real Database uses different
field names (e.g. "created_at" instead of "timestamp", or "text" instead
of "content"), extend the candidate lists in _field() calls below — those
are the only places that assume a schema.
"""

import re
import subprocess
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from datetime import datetime

from clipvault.database import Database


CONFIG_DIR = Path.home() / ".config" / "clipvault"
THEME_FILE = CONFIG_DIR / "theme"

MIN_WIDTH = 480
MIN_HEIGHT = 560
DEFAULT_WIDTH = 560
DEFAULT_HEIGHT = 720

PREVIEW_CHAR_LIMIT = 220
PREVIEW_LINE_LIMIT = 4

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

THEMES = {
    "dark": {
        "bg": "#1a1b1e",
        "surface": "#232428",
        "surface_hover": "#2b2d32",
        "surface_selected": "#2f3a4a",
        "border": "#33353a",
        "text": "#e7e8ea",
        "text_dim": "#9a9ca3",
        "text_faint": "#6b6d73",
        "accent": "#5b9dff",
        "accent_text": "#0d1117",
        "danger": "#e5636b",
        "success": "#5fbf77",
        "entry_bg": "#26272b",
    },
    "light": {
        "bg": "#f5f5f4",
        "surface": "#ffffff",
        "surface_hover": "#f0f0ef",
        "surface_selected": "#e4edff",
        "border": "#e2e2e0",
        "text": "#1d1d1f",
        "text_dim": "#68686b",
        "text_faint": "#9a9a9c",
        "accent": "#2563eb",
        "accent_text": "#ffffff",
        "danger": "#c8323b",
        "success": "#1f8a4c",
        "entry_bg": "#f0f0ef",
    },
}


def load_theme_name() -> str:
    try:
        name = THEME_FILE.read_text().strip()
        if name in THEMES:
            return name
    except FileNotFoundError:
        pass
    return "dark"


def save_theme_name(name: str) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        THEME_FILE.write_text(name)
    except OSError:
        pass  # non-fatal; theme just won't persist


# ---------------------------------------------------------------------------
# Helpers for reading rows defensively, content typing, and formatting
# ---------------------------------------------------------------------------

def _field(row, *candidates, default=None):
    """Fetch the first matching field from a row, regardless of whether the
    row is a dict, sqlite3.Row, or a plain object with attributes."""
    for name in candidates:
        try:
            if isinstance(row, dict) and name in row:
                return row[name]
            if hasattr(row, "keys") and name in row.keys():
                return row[name]
            if hasattr(row, name):
                return getattr(row, name)
        except (KeyError, IndexError, TypeError):
            continue
    return default


def row_id(row):
    return _field(row, "id", "rowid")


def row_content(row):
    return _field(row, "content", "text", "value", default="")


def row_timestamp(row):
    return _field(row, "timestamp", "created_at", "created", "time")


def row_pinned(row):
    return bool(_field(row, "pinned", "is_pinned", "pin", default=False))


_URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://\S+$")
_PATH_RE = re.compile(r"^(/|~/|\.{1,2}/)[^\s]+$")
_CMD_PREFIXES = (
    "sudo ", "git ", "cd ", "ls ", "docker ", "npm ", "pip ", "python ",
    "curl ", "ssh ", "cat ", "grep ", "make ", "chmod ", "systemctl ",
)


def detect_type(content: str) -> str:
    """Lightweight local heuristic classification, presentation only."""
    stripped = content.strip()
    if not stripped:
        return "text"
    first_line = stripped.splitlines()[0]

    if _URL_RE.match(first_line):
        return "url"
    if _PATH_RE.match(first_line) and " " not in first_line:
        return "path"
    if (stripped.startswith("{") and stripped.endswith("}")) or (
        stripped.startswith("[") and stripped.endswith("]")
    ):
        return "json"
    if first_line.startswith(_CMD_PREFIXES) or first_line.startswith("$ "):
        return "command"
    if any(tok in stripped for tok in ("def ", "class ", "function ", "=>", "#!/", "import ")):
        return "code"
    return "text"


TYPE_LABELS = {
    "url": "URL",
    "path": "PATH",
    "json": "JSON",
    "command": "CMD",
    "code": "CODE",
    "text": None,  # no badge for plain text, keeps UI quiet
}


def format_timestamp(ts) -> str:
    if ts is None:
        return ""
    dt = None
    if isinstance(ts, datetime):
        dt = ts
    elif isinstance(ts, (int, float)):
        try:
            dt = datetime.fromtimestamp(ts)
        except (ValueError, OSError):
            pass
    elif isinstance(ts, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(ts, fmt)
                break
            except ValueError:
                continue
    if dt is None:
        return str(ts)

    now = datetime.now()
    delta = now - dt
    if delta.days == 0 and now.date() == dt.date():
        if delta.seconds < 60:
            return "just now"
        if delta.seconds < 3600:
            mins = delta.seconds // 60
            return f"{mins}m ago"
        return dt.strftime("%-I:%M %p")
    if delta.days == 1:
        return dt.strftime("Yesterday %-I:%M %p")
    if delta.days < 7:
        return dt.strftime("%a %-I:%M %p")
    return dt.strftime("%b %-d, %Y")


def make_preview(content: str) -> str:
    """Truncate for display only. Storage is untouched."""
    lines = content.splitlines() or [""]
    shown_lines = lines[:PREVIEW_LINE_LIMIT]
    preview = "\n".join(shown_lines)
    truncated_lines = len(lines) > PREVIEW_LINE_LIMIT
    truncated_chars = len(preview) > PREVIEW_CHAR_LIMIT
    if truncated_chars:
        preview = preview[:PREVIEW_CHAR_LIMIT].rstrip()
    if truncated_chars or truncated_lines:
        preview += "…"
    return preview


def copy_to_x11_clipboard(content: str) -> bool:
    """Copy via xclip, matching the rest of the project's X11 approach."""
    try:
        proc = subprocess.Popen(
            ["xclip", "-selection", "clipboard"],
            stdin=subprocess.PIPE,
        )
        proc.communicate(input=content.encode("utf-8"), timeout=2)
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


# ---------------------------------------------------------------------------
# Scrollable frame with mouse-wheel support bound to every descendant
# ---------------------------------------------------------------------------

class ScrollableFrame(tk.Frame):
    """A vertically scrollable frame. Mouse wheel works anywhere over its
    content, not just over one specific blank strip."""

    def __init__(self, parent, colors, **kwargs):
        super().__init__(parent, bg=colors["bg"], **kwargs)
        self.colors = colors

        self.canvas = tk.Canvas(
            self, bg=colors["bg"], highlightthickness=0, bd=0
        )
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=colors["bg"])

        self.inner_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self._wheel_targets = [self.canvas, self.inner]

    def _on_inner_configure(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.inner_id, width=event.width)

    def _on_mousewheel(self, event):
        if event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(delta, "units")

    def bind_wheel_recursive(self, widget):
        """Call on any widget (card, button, label, etc.) so scrolling works
        no matter what's directly under the cursor."""
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        widget.bind("<Button-4>", self._on_mousewheel, add="+")
        widget.bind("<Button-5>", self._on_mousewheel, add="+")
        for child in widget.winfo_children():
            self.bind_wheel_recursive(child)

    def set_colors(self, colors):
        self.colors = colors
        self.configure(bg=colors["bg"])
        self.canvas.configure(bg=colors["bg"])
        self.inner.configure(bg=colors["bg"])


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class ClipVaultGUI:
    def __init__(self):
        self.db = Database()
        self.theme_name = load_theme_name()
        self.colors = THEMES[self.theme_name]

        self.root = tk.Tk()
        self.root.title("ClipVault")
        self.root.geometry(f"{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}")
        self.root.minsize(MIN_WIDTH, MIN_HEIGHT)
        self._center_window()
        self.root.configure(bg=self.colors["bg"])

        # State
        self.entries = []          # currently displayed rows (search or recent)
        self.card_widgets = []     # ordered list of (row, frame) for keyboard nav
        self.selected_index = None
        self.search_query = ""
        self._last_signature = None  # for change detection on poll
        self._copy_feedback_job = None

        self._build_layout()
        self._refresh(force=True)
        self._bind_shortcuts()
        self._schedule_poll()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # -- window setup ------------------------------------------------------

    def _center_window(self):
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - DEFAULT_WIDTH) // 2
        y = (screen_h - DEFAULT_HEIGHT) // 3
        self.root.geometry(f"{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}+{x}+{y}")

    def _build_layout(self):
        c = self.colors

        self.header = tk.Frame(self.root, bg=c["bg"])
        self.header.pack(fill="x", padx=20, pady=(18, 8))

        title_box = tk.Frame(self.header, bg=c["bg"])
        title_box.pack(side="left")
        self.title_label = tk.Label(
            title_box, text="ClipVault", font=("Sans", 17, "bold"),
            fg=c["text"], bg=c["bg"], anchor="w",
        )
        self.title_label.pack(anchor="w")
        self.subtitle_label = tk.Label(
            title_box, text="Your clipboard, organized.", font=("Sans", 10),
            fg=c["text_dim"], bg=c["bg"], anchor="w",
        )
        self.subtitle_label.pack(anchor="w")

        controls_box = tk.Frame(self.header, bg=c["bg"])
        controls_box.pack(side="right")
        self.theme_btn = self._make_icon_button(
            controls_box, "🌙" if self.theme_name == "light" else "☀",
            self._toggle_theme, tooltip="Toggle theme",
        )
        self.theme_btn.pack(side="right")

        # Search
        self.search_frame = tk.Frame(self.root, bg=c["entry_bg"], highlightthickness=1)
        self.search_frame.configure(highlightbackground=c["border"], highlightcolor=c["accent"])
        self.search_frame.pack(fill="x", padx=20, pady=(4, 12))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)
        self.search_entry = tk.Entry(
            self.search_frame, textvariable=self.search_var,
            font=("Sans", 12), fg=c["text"], bg=c["entry_bg"],
            insertbackground=c["text"], relief="flat", bd=0,
        )
        self.search_entry.pack(side="left", fill="x", expand=True, ipady=9, padx=(12, 4))
        self._set_placeholder()
        self.search_entry.bind("<FocusIn>", self._clear_placeholder)
        self.search_entry.bind("<FocusOut>", self._maybe_restore_placeholder)

        self.clear_search_btn = tk.Label(
            self.search_frame, text="✕", font=("Sans", 11), fg=c["text_faint"],
            bg=c["entry_bg"], cursor="hand2", padx=12,
        )
        self.clear_search_btn.bind("<Button-1>", lambda e: self._clear_search())
        # only shown when there's text; packed/unpacked dynamically

        # List area
        self.list_container = ScrollableFrame(self.root, c)
        self.list_container.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        # Footer / status bar
        self.footer = tk.Frame(self.root, bg=c["bg"])
        self.footer.pack(fill="x", padx=20, pady=(0, 14))
        self.status_label = tk.Label(
            self.footer, text="", font=("Sans", 9), fg=c["text_faint"], bg=c["bg"],
        )
        self.status_label.pack(side="left")
        self.clear_all_btn = tk.Label(
            self.footer, text="Clear all", font=("Sans", 9), fg=c["text_faint"],
            bg=c["bg"], cursor="hand2",
        )
        self.clear_all_btn.pack(side="right")
        self.clear_all_btn.bind("<Button-1>", lambda e: self._confirm_clear_all())
        self._bind_hover_color(self.clear_all_btn, c["text_faint"], c["danger"])

    def _make_icon_button(self, parent, text, command, tooltip=None):
        c = self.colors
        btn = tk.Label(
            parent, text=text, font=("Sans", 13), fg=c["text_dim"], bg=c["bg"],
            cursor="hand2", padx=8, pady=4,
        )
        btn.bind("<Button-1>", lambda e: command())
        self._bind_hover_color(btn, c["text_dim"], c["text"])
        return btn

    def _bind_hover_color(self, widget, normal, hover):
        widget.bind("<Enter>", lambda e: widget.configure(fg=hover))
        widget.bind("<Leave>", lambda e: widget.configure(fg=normal))

    # -- placeholder handling ------------------------------------------------

    PLACEHOLDER = "Search clipboard history..."

    def _set_placeholder(self):
        c = self.colors
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, self.PLACEHOLDER)
        self.search_entry.configure(fg=c["text_faint"])
        self._placeholder_active = True

    def _clear_placeholder(self, _event=None):
        if getattr(self, "_placeholder_active", False):
            self.search_entry.delete(0, tk.END)
            self.search_entry.configure(fg=self.colors["text"])
            self._placeholder_active = False

    def _maybe_restore_placeholder(self, _event=None):
        if not self.search_entry.get().strip():
            self._set_placeholder()

    # -- search --------------------------------------------------------------

    def _on_search_changed(self, *_args):
        if getattr(self, "_placeholder_active", False):
            return
        query = self.search_var.get()
        self.search_query = query
        if query.strip():
            self.clear_search_btn.pack(side="right", padx=(0, 8))
        else:
            self.clear_search_btn.pack_forget()
        self._refresh(force=True)

    def _clear_search(self):
        self._placeholder_active = False
        self.search_var.set("")
        self._set_placeholder()
        self.clear_search_btn.pack_forget()
        self.search_entry.focus_set()
        self._refresh(force=True)

    def _focus_search(self):
        self.search_entry.focus_set()
        self._clear_placeholder()

    # -- data / rendering ------------------------------------------------------

    def _fetch_entries(self):
        query = "" if getattr(self, "_placeholder_active", False) else self.search_query.strip()
        if query:
            return self.db.search(query)
        return self.db.get_recent()

    def _signature(self, rows):
        """Cheap signature to detect real changes, so the poll loop doesn't
        rebuild the UI when nothing changed (avoids flicker)."""
        try:
            return (self.db.count(), tuple(row_id(r) for r in rows), tuple(row_pinned(r) for r in rows))
        except Exception:
            return None

    def _refresh(self, force=False):
        rows = self._fetch_entries()
        sig = self._signature(rows)
        if not force and sig == self._last_signature:
            return
        self._last_signature = sig
        self.entries = rows
        self._render_list()

    def _render_list(self):
        for child in self.list_container.inner.winfo_children():
            child.destroy()
        self.card_widgets = []

        if not self.entries:
            self._render_empty_state()
            self._update_status()
            self.selected_index = None
            return

        pinned = [r for r in self.entries if row_pinned(r)]
        recent = [r for r in self.entries if not row_pinned(r)]

        if pinned:
            self._render_section_label("PINNED")
            for row in pinned:
                self._render_card(row)

        if recent:
            if pinned:
                self._render_section_label("RECENT")
            for row in recent:
                self._render_card(row)

        self.list_container.bind_wheel_recursive(self.list_container.inner)
        self._update_status()

        if self.card_widgets and self.selected_index is None:
            self.selected_index = 0
            self._apply_selection()

    def _render_section_label(self, text):
        c = self.colors
        lbl = tk.Label(
            self.list_container.inner, text=text, font=("Sans", 9, "bold"),
            fg=c["text_faint"], bg=c["bg"], anchor="w",
        )
        lbl.pack(fill="x", pady=(10, 4))

    def _render_empty_state(self):
        c = self.colors
        box = tk.Frame(self.list_container.inner, bg=c["bg"])
        box.pack(fill="both", expand=True, pady=80)
        icon = tk.Label(box, text="⎘", font=("Sans", 28), fg=c["text_faint"], bg=c["bg"])
        icon.pack()
        if self.search_query.strip() and not getattr(self, "_placeholder_active", False):
            title = "No matching entries"
            desc = "Try a different search term."
        else:
            title = "No clipboard history yet"
            desc = "Copy something and it will show up here."
        tk.Label(box, text=title, font=("Sans", 12, "bold"), fg=c["text"], bg=c["bg"]).pack(pady=(10, 2))
        tk.Label(box, text=desc, font=("Sans", 10), fg=c["text_dim"], bg=c["bg"]).pack()

    def _render_card(self, row):
        c = self.colors
        content = row_content(row)
        content_type = detect_type(content)
        preview = make_preview(content)

        card = tk.Frame(self.list_container.inner, bg=c["surface"], highlightthickness=1,
                         highlightbackground=c["border"])
        card.pack(fill="x", pady=4)
        inner_pad = tk.Frame(card, bg=c["surface"])
        inner_pad.pack(fill="x", padx=14, pady=10)

        top_row = tk.Frame(inner_pad, bg=c["surface"])
        top_row.pack(fill="x")

        meta_bits = []
        if row_pinned(row):
            meta_bits.append("📌")
        label = TYPE_LABELS.get(content_type)
        if label:
            meta_bits.append(label)
        ts_text = format_timestamp(row_timestamp(row))
        if ts_text:
            meta_bits.append(ts_text)
        meta_text = "   ".join(meta_bits)
        meta_label = tk.Label(top_row, text=meta_text, font=("Sans", 8, "bold"),
                               fg=c["text_faint"], bg=c["surface"], anchor="w")
        meta_label.pack(side="left")

        actions = tk.Frame(top_row, bg=c["surface"])
        actions.pack(side="right")

        pin_text = "Unpin" if row_pinned(row) else "Pin"
        pin_btn = self._card_action(actions, pin_text, lambda r=row: self._handle_pin_toggle(r))
        copy_btn = self._card_action(actions, "Copy", lambda r=row: self._handle_copy(r))
        del_btn = self._card_action(actions, "Delete", lambda r=row: self._handle_delete(r), danger=True)

        body_label = tk.Label(
            inner_pad, text=preview, font=("Monospace", 10), fg=c["text"], bg=c["surface"],
            anchor="w", justify="left", wraplength=1,  # updated on resize
        )
        body_label.pack(fill="x", pady=(6, 0))

        def update_wrap(event, lbl=body_label):
            lbl.configure(wraplength=max(event.width - 28, 100))

        card.bind("<Configure>", update_wrap)

        # Click-to-select, and click body to copy for convenience
        widgets_for_select = [card, inner_pad, top_row, meta_label, body_label]
        idx = len(self.card_widgets)
        for w in widgets_for_select:
            w.bind("<Button-1>", lambda e, i=idx: self._select_index(i))

        self._bind_hover(card, [inner_pad, top_row, meta_label, body_label], row)

        self.card_widgets.append((row, card, body_label))

    def _card_action(self, parent, text, command, danger=False):
        c = self.colors
        color = c["danger"] if danger else c["text_dim"]
        btn = tk.Label(parent, text=text, font=("Sans", 9), fg=color, bg=c["surface"],
                        cursor="hand2", padx=8)
        btn.pack(side="right")
        btn.bind("<Button-1>", lambda e: command())
        hover_color = c["danger"] if danger else c["accent"]
        self._bind_hover_color(btn, color, hover_color)
        return btn

    def _bind_hover(self, card, children, row):
        c = self.colors

        def on_enter(_e):
            if not self._is_selected_row(row):
                card.configure(bg=c["surface_hover"])
                for w in children:
                    w.configure(bg=c["surface_hover"])

        def on_leave(_e):
            if not self._is_selected_row(row):
                card.configure(bg=c["surface"])
                for w in children:
                    w.configure(bg=c["surface"])

        card.bind("<Enter>", on_enter, add="+")
        card.bind("<Leave>", on_leave, add="+")

    def _is_selected_row(self, row):
        if self.selected_index is None or self.selected_index >= len(self.card_widgets):
            return False
        return row_id(self.card_widgets[self.selected_index][0]) == row_id(row)

    def _update_status(self):
        try:
            total = self.db.count()
        except Exception:
            total = len(self.entries)
        self.status_label.configure(text=f"{total} item{'s' if total != 1 else ''}")

    # -- selection ------------------------------------------------------------

    def _select_index(self, index):
        if not self.card_widgets:
            return
        index = max(0, min(index, len(self.card_widgets) - 1))
        self.selected_index = index
        self._apply_selection()

    def _apply_selection(self):
        c = self.colors
        for i, (row, card, body_label) in enumerate(self.card_widgets):
            selected = i == self.selected_index
            bg = c["surface_selected"] if selected else c["surface"]
            card.configure(bg=bg, highlightbackground=c["accent"] if selected else c["border"])
            for child in card.winfo_children():
                self._set_bg_recursive(child, bg)

    def _set_bg_recursive(self, widget, bg):
        try:
            widget.configure(bg=bg)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._set_bg_recursive(child, bg)

    def _move_selection(self, delta):
        if not self.card_widgets:
            return
        if self.selected_index is None:
            self.selected_index = 0
        else:
            self.selected_index = max(0, min(self.selected_index + delta, len(self.card_widgets) - 1))
        self._apply_selection()
        self._scroll_to_selected()

    def _scroll_to_selected(self):
        if self.selected_index is None:
            return
        _row, card, _lbl = self.card_widgets[self.selected_index]
        self.list_container.canvas.update_idletasks()
        bbox = self.list_container.canvas.bbox("all")
        if not bbox:
            return
        total_height = bbox[3] - bbox[1]
        if total_height <= 0:
            return
        card_y = card.winfo_y()
        fraction = card_y / total_height
        self.list_container.canvas.yview_moveto(max(0.0, min(fraction, 1.0)))

    # -- actions ---------------------------------------------------------------

    def _selected_row(self):
        if self.selected_index is None or not self.card_widgets:
            return None
        return self.card_widgets[self.selected_index][0]

    def _handle_copy(self, row=None):
        row = row or self._selected_row()
        if row is None:
            return
        content = row_content(row)
        ok = copy_to_x11_clipboard(content)
        if ok:
            self._show_copy_feedback()
        else:
            self.status_label.configure(text="Copy failed — is xclip installed?")

    def _show_copy_feedback(self):
        c = self.colors
        self.status_label.configure(text="Copied to clipboard", fg=c["success"])
        if self._copy_feedback_job:
            self.root.after_cancel(self._copy_feedback_job)
        self._copy_feedback_job = self.root.after(1400, self._reset_status_color)

    def _reset_status_color(self):
        self.status_label.configure(fg=self.colors["text_faint"])
        self._update_status()

    def _handle_pin_toggle(self, row):
        rid = row_id(row)
        if rid is None:
            return
        try:
            if row_pinned(row):
                self.db.unpin(rid)
            else:
                self.db.pin(rid)
        except Exception as exc:
            messagebox.showerror("ClipVault", f"Could not update pin: {exc}")
            return
        self._refresh(force=True)

    def _handle_delete(self, row):
        rid = row_id(row)
        if rid is None:
            return
        try:
            self.db.delete(rid)
        except Exception as exc:
            messagebox.showerror("ClipVault", f"Could not delete: {exc}")
            return
        self._refresh(force=True)

    def _handle_delete_selected(self):
        row = self._selected_row()
        if row is not None:
            self._handle_delete(row)

    def _handle_copy_selected_enter(self):
        self._handle_copy(self._selected_row())

    def _confirm_clear_all(self):
        if messagebox.askyesno("Clear all history", "Delete all clipboard history? This cannot be undone."):
            try:
                self.db.clear()
            except Exception as exc:
                messagebox.showerror("ClipVault", f"Could not clear history: {exc}")
                return
            self._refresh(force=True)

    # -- theme ------------------------------------------------------------------

    def _toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.colors = THEMES[self.theme_name]
        save_theme_name(self.theme_name)
        self._apply_theme()

    def _apply_theme(self):
        c = self.colors
        self.root.configure(bg=c["bg"])
        self.header.configure(bg=c["bg"])
        self.title_label.configure(bg=c["bg"], fg=c["text"])
        self.subtitle_label.configure(bg=c["bg"], fg=c["text_dim"])
        self.theme_btn.configure(text="🌙" if self.theme_name == "light" else "☀", bg=c["bg"], fg=c["text_dim"])
        self.search_frame.configure(bg=c["entry_bg"], highlightbackground=c["border"], highlightcolor=c["accent"])
        self.search_entry.configure(bg=c["entry_bg"], insertbackground=c["text"])
        if not getattr(self, "_placeholder_active", False):
            self.search_entry.configure(fg=c["text"])
        self.clear_search_btn.configure(bg=c["entry_bg"], fg=c["text_faint"])
        self.footer.configure(bg=c["bg"])
        self.status_label.configure(bg=c["bg"], fg=c["text_faint"])
        self.clear_all_btn.configure(bg=c["bg"], fg=c["text_faint"])
        self.list_container.set_colors(c)
        self.selected_index = None
        self._render_list()

    # -- keyboard shortcuts -------------------------------------------------------

    def _bind_shortcuts(self):
        self.root.bind("<Control-f>", lambda e: self._focus_search())
        self.root.bind("<Escape>", self._handle_escape)
        self.root.bind("<Return>", lambda e: self._handle_copy_selected_enter())
        self.root.bind("<Down>", lambda e: self._handle_nav(1))
        self.root.bind("<Up>", lambda e: self._handle_nav(-1))
        self.root.bind("<Delete>", self._handle_delete_key)

    def _handle_nav(self, delta):
        # Don't hijack Up/Down while actively typing in the search box.
        focused = self.root.focus_get()
        if focused is self.search_entry:
            return
        self._move_selection(delta)

    def _handle_delete_key(self, _event):
        focused = self.root.focus_get()
        if focused is self.search_entry:
            return
        self._handle_delete_selected()

    def _handle_escape(self, _event):
        if self.search_var.get().strip() and not getattr(self, "_placeholder_active", False):
            self._clear_search()
        else:
            self.root.focus_set()

    # -- polling (change-aware, no naive per-second rebuild) ----------------------

    def _schedule_poll(self):
        self._poll_job = self.root.after(2000, self._poll)

    def _poll(self):
        self._refresh(force=False)
        self._schedule_poll()

    # -- lifecycle ------------------------------------------------------------------

    def _on_close(self):
        if getattr(self, "_poll_job", None):
            self.root.after_cancel(self._poll_job)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ClipVaultGUI().run()