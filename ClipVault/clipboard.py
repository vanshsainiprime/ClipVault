from Xlib import X, display
from Xlib.ext import xfixes


class ClipboardWatcher:
    """Event-driven X11 clipboard watcher."""

    def __init__(self, callback):
        self.callback = callback
        self.running = False
        self.last_content = None

        self.display = display.Display()
        self.screen = self.display.screen()
        self.root = self.screen.root

        self.clipboard = self.display.intern_atom("CLIPBOARD")
        self.utf8_string = self.display.intern_atom("UTF8_STRING")
        self.string = self.display.intern_atom("STRING")

        self.property = self.display.intern_atom(
            "CLIPVAULT_PROPERTY"
        )

        if self.display.query_extension("XFIXES") is None:
            raise RuntimeError(
                "XFixes extension is not available."
            )

        self.display.xfixes_query_version()

        self.window = self.root.create_window(
            0,
            0,
            1,
            1,
            0,
            self.screen.root_depth,
            X.InputOutput,
            X.CopyFromParent,
        )

        mask = xfixes.XFixesSetSelectionOwnerNotifyMask

        self.display.xfixes_select_selection_input(
            self.root,
            self.clipboard,
            mask,
        )

        self.display.sync()

    def _request_text(self, target):
        """Request clipboard data from its current owner."""

        self.window.convert_selection(
            self.clipboard,
            target,
            self.property,
            X.CurrentTime,
        )

        self.display.sync()

        while True:
            event = self.display.next_event()

            if event.type != X.SelectionNotify:
                continue

            if event.property == X.NONE:
                return None

            data = self.window.get_full_property(
                self.property,
                X.AnyPropertyType,
            )

            if data is None:
                return None

            value = data.value

            if isinstance(value, bytes):
                return value.decode(
                    "utf-8",
                    errors="replace",
                )

            return str(value)

    def _get_clipboard(self):
        """Read text from the current clipboard owner."""

        content = self._request_text(
            self.utf8_string
        )

        if content is not None:
            return content

        return self._request_text(
            self.string
        )

    def start(self):
        """Start watching clipboard changes."""

        self.running = True

        print("ClipVault clipboard watcher started.")
        print("Waiting for new clipboard content...\n")

        while self.running:
            event = self.display.next_event()

            # XFixes SetSelectionOwner notification.
            if (
                event.type,
                event.sub_code,
            ) != (
                self.display.extension_event.SetSelectionOwnerNotify
            ):
                continue

            if event.selection != self.clipboard:
                continue

            # Ignore "no owner".
            if event.owner == X.NONE:
                continue

            content = self._get_clipboard()

            if not content:
                continue

            if content == self.last_content:
                continue

            self.last_content = content

            self.callback(content)

    def stop(self):
        """Stop watching the clipboard."""

        self.running = False

        try:
            self.window.destroy()
            self.display.flush()
            self.display.close()
        except Exception:
            pass