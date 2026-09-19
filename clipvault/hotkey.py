import tkinter as tk
from Xlib import X, XK, display

from clipvault.database import Database
from clipvault.gui import (
    THEMES,
    load_theme_name,
    row_content,
    row_timestamp,
    row_pinned,
    format_timestamp,
    make_preview,
    copy_to_x11_clipboard,
)

WIDTH = 620
HEIGHT = 620
MAX_ITEMS = 50


class ClipboardPopup:
    """Quick Super+V clipboard picker using ClipVault's existing visual style."""

    def __init__(self):
        self.db = Database()
        self.xdisplay = display.Display()
        self.root_window = self.xdisplay.screen().root

        self.v_keycode = self.xdisplay.keysym_to_keycode(
            XK.string_to_keysym("v")
        )

        self.popup = None
        self.search_var = None
        self.search_entry = None
        self.canvas = None
        self.list_frame = None
        self.cards = []
        self.entries = []
        self.selected_index = None
        self.theme_name = load_theme_name()
        self.colors = THEMES[self.theme_name]

        self._grab_hotkey()

        self.tk = tk.Tk()
        self.tk.withdraw()
        self.tk.after(30, self._poll_x11)

    def _grab_hotkey(self):
        modifiers = (
            0,
            X.Mod2Mask,
            X.LockMask,
            X.Mod2Mask | X.LockMask,
        )

        for extra in modifiers:
            self.root_window.grab_key(
                self.v_keycode,
                X.Mod4Mask | extra,
                True,
                X.GrabModeAsync,
                X.GrabModeAsync,
            )

        self.xdisplay.flush()

    def _ungrab_hotkey(self):
        modifiers = (
            0,
            X.Mod2Mask,
            X.LockMask,
            X.Mod2Mask | X.LockMask,
        )

        for extra in modifiers:
            self.root_window.ungrab_key(
                self.v_keycode,
                X.Mod4Mask | extra,
            )

        self.xdisplay.flush()

    def _poll_x11(self):
        while self.xdisplay.pending_events():
            event = self.xdisplay.next_event()

            if event.type == X.KeyPress:
                if (
                    event.detail == self.v_keycode
                    and event.state & X.Mod4Mask
                ):
                    self._toggle_popup()

        self.tk.after(30, self._poll_x11)

    def _toggle_popup(self):
        if self.popup is None:
            self._open_popup()
        else:
            self._close_popup()

    def _open_popup(self):
        self.popup = tk.Toplevel(self.tk)
        self.popup.overrideredirect(True)
        self.popup.attributes("-topmost", True)
        self.popup.configure(bg=self.colors["bg"])

        screen_w = self.popup.winfo_screenwidth()
        screen_h = self.popup.winfo_screenheight()
        x = (screen_w - WIDTH) // 2
        y = (screen_h - HEIGHT) // 3

        self.popup.geometry(f"{WIDTH}x{HEIGHT}+{x}+{y}")

        self._build_popup()
        self._refresh()
        self.search_entry.focus_set()

        self.popup.bind("<Escape>", lambda _: self._close_popup())
        self.popup.bind("<Return>", lambda _: self._copy_selected())
        self.popup.bind("<Up>", lambda _: self._move_selection(-1))
        self.popup.bind("<Down>", lambda _: self._move_selection(1))

        self.popup.after(40, self._focus_search)

    def _build_popup(self):
        c = self.colors

        outer = tk.Frame(
            self.popup,
            bg=c["surface"],
            highlightthickness=1,
            highlightbackground=c["border"],
        )
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=c["surface"])
        header.pack(fill="x", padx=20, pady=(18, 8))

        title_box = tk.Frame(header, bg=c["surface"])
        title_box.pack(side="left")

        tk.Label(
            title_box,
            text="ClipVault",
            font=("Sans", 16, "bold"),
            fg=c["text"],
            bg=c["surface"],
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="Quick clipboard",
            font=("Sans", 9),
            fg=c["text_dim"],
            bg=c["surface"],
        ).pack(anchor="w", pady=(1, 0))

        tk.Label(
            header,
            text="ESC to close",
            font=("Sans", 8),
            fg=c["text_faint"],
            bg=c["surface"],
        ).pack(side="right", anchor="center")

        self.search_frame = tk.Frame(
            outer,
            bg=c["entry_bg"],
            highlightthickness=1,
            highlightbackground=c["border"],
        )
        self.search_frame.pack(fill="x", padx=20, pady=(4, 12))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._search_changed)

        self.search_entry = tk.Entry(
            self.search_frame,
            textvariable=self.search_var,
            font=("Sans", 11),
            fg=c["text"],
            bg=c["entry_bg"],
            insertbackground=c["text"],
            relief="flat",
            bd=0,
        )
        self.search_entry.pack(
            fill="x",
            expand=True,
            padx=12,
            pady=9,
        )

        self.canvas = tk.Canvas(
            outer,
            bg=c["surface"],
            highlightthickness=0,
            bd=0,
        )
        scrollbar = tk.Scrollbar(
            outer,
            orient="vertical",
            command=self.canvas.yview,
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True, padx=(20, 0))
        scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=(0, 10))

        self.list_frame = tk.Frame(
            self.canvas,
            bg=c["surface"],
        )
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.list_frame,
            anchor="nw",
        )

        self.list_frame.bind(
            "<Configure>",
            lambda _: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ),
        )
        self.canvas.bind(
            "<Configure>",
            lambda event: self.canvas.itemconfigure(
                self.canvas_window,
                width=event.width,
            ),
        )

        for widget in (self.canvas, self.list_frame):
            widget.bind("<MouseWheel>", self._wheel, add="+")
            widget.bind("<Button-4>", self._wheel, add="+")
            widget.bind("<Button-5>", self._wheel, add="+")

        footer = tk.Frame(outer, bg=c["surface"])
        footer.pack(fill="x", padx=20, pady=(4, 14))

        self.status = tk.Label(
            footer,
            text="",
            font=("Sans", 8),
            fg=c["text_faint"],
            bg=c["surface"],
        )
        self.status.pack(side="left")

        tk.Label(
            footer,
            text="↑ ↓  Navigate    Enter  Copy",
            font=("Sans", 8),
            fg=c["text_faint"],
            bg=c["surface"],
        ).pack(side="right")

    def _focus_search(self):
        if self.search_entry:
            self.search_entry.focus_set()

    def _search_changed(self, *_):
        self._refresh()

    def _refresh(self):
        if not self.popup:
            return

        query = self.search_var.get().strip()

        if query:
            rows = self.db.search(query, MAX_ITEMS)
        else:
            rows = self.db.get_recent(MAX_ITEMS)

        self.entries = list(rows)
        self.selected_index = 0 if self.entries else None

        for child in self.list_frame.winfo_children():
            child.destroy()

        self.cards = []

        if not self.entries:
            self._empty_state()
            self.status.configure(text="No clipboard items")
            return

        pinned = [r for r in self.entries if row_pinned(r)]
        recent = [r for r in self.entries if not row_pinned(r)]

        if pinned:
            self._section("PINNED")
            for row in pinned:
                self._card(row)

        if recent:
            if pinned:
                self._section("RECENT")
            for row in recent:
                self._card(row)

        self.status.configure(
            text=f"{len(self.entries)} item"
            + ("" if len(self.entries) == 1 else "s")
        )

        self._apply_selection()

    def _section(self, text):
        tk.Label(
            self.list_frame,
            text=text,
            font=("Sans", 8, "bold"),
            fg=self.colors["text_faint"],
            bg=self.colors["surface"],
            anchor="w",
        ).pack(fill="x", pady=(5, 5))

    def _card(self, row):
        c = self.colors

        frame = tk.Frame(
            self.list_frame,
            bg=c["surface"],
            highlightthickness=1,
            highlightbackground=c["border"],
            cursor="hand2",
        )
        frame.pack(fill="x", pady=(0, 8))

        top = tk.Frame(frame, bg=c["surface"])
        top.pack(fill="x", padx=13, pady=(10, 4))

        content = row_content(row)
        content_type = self._type_label(content)

        left = tk.Frame(top, bg=c["surface"])
        left.pack(side="left", fill="x", expand=True)

        if row_pinned(row):
            badge_text = "📌  PINNED"
        elif content_type:
            badge_text = content_type
        else:
            badge_text = ""

        if badge_text:
            tk.Label(
                left,
                text=badge_text,
                font=("Sans", 7, "bold"),
                fg=c["accent"],
                bg=c["surface"],
            ).pack(anchor="w")

        tk.Label(
            left,
            text=format_timestamp(row_timestamp(row)),
            font=("Sans", 8),
            fg=c["text_faint"],
            bg=c["surface"],
        ).pack(anchor="w", pady=(2, 0))

        preview = make_preview(content)

        body = tk.Label(
            frame,
            text=preview,
            font=("Sans", 10),
            fg=c["text"],
            bg=c["surface"],
            anchor="nw",
            justify="left",
            wraplength=530,
        )
        body.pack(fill="x", padx=13, pady=(2, 12))

        card_index = len(self.cards)
        self.cards.append((row, frame))

        for widget in (frame, top, left, body):
            widget.bind(
                "<Button-1>",
                lambda _, i=card_index: self._select_and_copy(i),
            )
            widget.bind(
                "<Enter>",
                lambda _, i=card_index: self._hover(i, True),
            )
            widget.bind(
                "<Leave>",
                lambda _, i=card_index: self._hover(i, False),
            )

    def _empty_state(self):
        c = self.colors

        box = tk.Frame(
            self.list_frame,
            bg=c["surface"],
        )
        box.pack(fill="both", expand=True, pady=100)

        tk.Label(
            box,
            text="No clipboard history",
            font=("Sans", 12, "bold"),
            fg=c["text"],
            bg=c["surface"],
        ).pack()

        tk.Label(
            box,
            text="Copy something and it will appear here.",
            font=("Sans", 9),
            fg=c["text_dim"],
            bg=c["surface"],
        ).pack(pady=(5, 0))

    def _type_label(self, content):
        value = content.strip()
        if not value:
            return None
        first = value.splitlines()[0]

        if "://" in first and first.split("://", 1)[0].replace("+", "").replace("-", "").replace(".", "").isalnum():
            return "URL"

        if value.startswith(("{", "[")) and value.endswith(("}", "]")):
            return "JSON"

        if first.startswith(
            ("sudo ", "git ", "cd ", "ls ", "docker ", "npm ",
             "pip ", "python ", "curl ", "ssh ", "systemctl ")
        ):
            return "CMD"

        if any(token in value for token in ("def ", "class ", "function ", "=>", "#!/")):
            return "CODE"

        return None

    def _hover(self, index, entering):
        if index >= len(self.cards):
            return
        if index == self.selected_index:
            return

        frame = self.cards[index][1]
        color = (
            self.colors["surface_hover"]
            if entering
            else self.colors["surface"]
        )
        self._set_card_color(frame, color)

    def _set_card_color(self, frame, color):
        frame.configure(bg=color)

        def walk(widget):
            for child in widget.winfo_children():
                try:
                    child.configure(bg=color)
                except tk.TclError:
                    pass
                walk(child)

        walk(frame)

    def _apply_selection(self):
        for index, (_, frame) in enumerate(self.cards):
            if index == self.selected_index:
                self._set_card_color(
                    frame,
                    self.colors["surface_selected"],
                )
                frame.configure(
                    highlightbackground=self.colors["accent"]
                )
            else:
                self._set_card_color(
                    frame,
                    self.colors["surface"],
                )
                frame.configure(
                    highlightbackground=self.colors["border"]
                )

        if self.selected_index is not None:
            self._scroll_to_selected()

    def _move_selection(self, delta):
        if not self.entries:
            return "break"

        if self.selected_index is None:
            self.selected_index = 0
        else:
            self.selected_index = (
                self.selected_index + delta
            ) % len(self.entries)

        self._apply_selection()
        return "break"

    def _scroll_to_selected(self):
        if self.selected_index is None or not self.cards:
            return

        frame = self.cards[self.selected_index][1]
        self.popup.update_idletasks()

        top = frame.winfo_y()
        bottom = top + frame.winfo_height()

        visible_top = self.canvas.canvasy(0)
        visible_bottom = visible_top + self.canvas.winfo_height()

        if top < visible_top:
            self.canvas.yview_moveto(
                max(0, top / max(1, self.list_frame.winfo_height()))
            )
        elif bottom > visible_bottom:
            target = (
                bottom - self.canvas.winfo_height()
            ) / max(1, self.list_frame.winfo_height())
            self.canvas.yview_moveto(max(0, min(1, target)))

    def _select_and_copy(self, index):
        self.selected_index = index
        self._copy_selected()

    def _copy_selected(self):
        if self.selected_index is None:
            return "break"

        if self.selected_index >= len(self.entries):
            return "break"

        content = row_content(
            self.entries[self.selected_index]
        )

        if copy_to_x11_clipboard(content):
            self._close_popup()

        return "break"

    def _wheel(self, event):
        if event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1

        self.canvas.yview_scroll(delta, "units")

    def _close_popup(self):
        if self.popup:
            self.popup.destroy()
            self.popup = None

        self.search_var = None
        self.search_entry = None
        self.canvas = None
        self.list_frame = None
        self.cards = []
        self.entries = []
        self.selected_index = None

    def run(self):
        try:
            self.tk.mainloop()
        finally:
            self._ungrab_hotkey()
            self.db.close()
            self.xdisplay.close()


def main():
    ClipboardPopup().run()


if __name__ == "__main__":
    main()
