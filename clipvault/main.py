import argparse
import subprocess

from clipvault.clipboard import ClipboardWatcher
from clipvault.database import Database


def preview(text, length=80):
    """Create a readable one-line clipboard preview."""

    text = text.replace("\n", " ↵ ")
    text = text.replace("\t", " → ")

    if len(text) > length:
        return text[:length] + "..."

    return text


def list_items(db):
    """Display recent clipboard history."""

    items = db.get_recent(30)

    if not items:
        print("Clipboard history is empty.")
        return

    print("\nClipVault History\n")

    for item in items:
        pin = "📌 " if item["pinned"] else "   "

        print(
            f"{pin}{item['id']:4}  "
            f"{preview(item['content'])}"
        )

    print()


def search_items(db, query):
    """Search clipboard history."""

    items = db.search(query)

    if not items:
        print(f'No results for "{query}".')
        return

    print(f'\nSearch results for "{query}"\n')

    for item in items:
        pin = "📌 " if item["pinned"] else "   "

        print(
            f"{pin}{item['id']:4}  "
            f"{preview(item['content'])}"
        )

    print()


def copy_item(db, item_id):
    """Copy a history entry back to the clipboard."""

    item = db.get_by_id(item_id)

    if item is None:
        print(f"Entry {item_id} not found.")
        return

    result = subprocess.run(
        [
            "xclip",
            "-selection",
            "clipboard",
            "-i",
        ],
        input=item["content"],
        text=True,
        check=False,
    )

    if result.returncode == 0:
        print(f"Copied entry {item_id} to clipboard.")
    else:
        print("Failed to copy entry to clipboard.")


def delete_item(db, item_id):
    """Delete a clipboard entry."""

    if db.delete(item_id):
        print(f"Deleted entry {item_id}.")
    else:
        print(f"Entry {item_id} not found.")


def pin_item(db, item_id):
    """Pin a clipboard entry."""

    if db.pin(item_id):
        print(f"Pinned entry {item_id}.")
    else:
        print(f"Entry {item_id} not found.")


def unpin_item(db, item_id):
    """Unpin a clipboard entry."""

    if db.unpin(item_id):
        print(f"Unpinned entry {item_id}.")
    else:
        print(f"Entry {item_id} not found.")


def clear_history(db):
    """Clear all unpinned clipboard entries."""

    deleted = db.clear()

    word = "entry" if deleted == 1 else "entries"

    print(
        f"Cleared {deleted} unpinned clipboard {word}."
    )


def show_count(db):
    """Display the number of stored entries."""

    print(f"Clipboard entries: {db.count()}")


def watch_clipboard(db):
    """Start clipboard monitoring."""

    def save_clipboard(content):
        if db.add(content):
            print(f"Saved: {preview(content)}")

    watcher = ClipboardWatcher(
        callback=save_clipboard
    )

    print("ClipVault clipboard watcher started.")
    print("Press Ctrl+C to stop.\n")

    try:
        watcher.start()
    except KeyboardInterrupt:
        print("\nClipVault stopped.")
    finally:
        watcher.stop()


def daemon(db):
    """Run ClipVault as a background clipboard monitor."""

    def save_clipboard(content):
        if db.add(content):
            print(f"Saved: {preview(content)}")

    watcher = ClipboardWatcher(
        callback=save_clipboard
    )

    print("ClipVault daemon started.")
    print("Monitoring clipboard...\n")

    try:
        watcher.start()
    except KeyboardInterrupt:
        print("\nClipVault daemon stopped.")
    finally:
        watcher.stop()


def open_gui():
    """Open the ClipVault desktop application."""

    from clipvault.gui import ClipVaultGUI

    app = ClipVaultGUI()
    app.run()


def build_parser():
    """Build the command-line argument parser."""

    parser = argparse.ArgumentParser(
        prog="clipvault",
        description=(
            "Private, offline clipboard "
            "history manager for Linux."
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command"
    )

    subparsers.add_parser(
        "list",
        help="Show clipboard history",
    )

    search_parser = subparsers.add_parser(
        "search",
        help="Search clipboard history",
    )

    search_parser.add_argument(
        "query",
        help="Text to search for",
    )

    copy_parser = subparsers.add_parser(
        "copy",
        help="Copy a history entry",
    )

    copy_parser.add_argument(
        "id",
        type=int,
        help="History entry ID",
    )

    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete a history entry",
    )

    delete_parser.add_argument(
        "id",
        type=int,
        help="History entry ID",
    )

    pin_parser = subparsers.add_parser(
        "pin",
        help="Pin a history entry",
    )

    pin_parser.add_argument(
        "id",
        type=int,
        help="History entry ID",
    )

    unpin_parser = subparsers.add_parser(
        "unpin",
        help="Unpin a history entry",
    )

    unpin_parser.add_argument(
        "id",
        type=int,
        help="History entry ID",
    )

    subparsers.add_parser(
        "clear",
        help="Clear all unpinned history",
    )

    subparsers.add_parser(
        "count",
        help="Show number of stored entries",
    )

    subparsers.add_parser(
        "watch",
        help="Monitor clipboard",
    )

    subparsers.add_parser(
        "daemon",
        help="Run ClipVault in the background",
    )

    subparsers.add_parser(
        "gui",
        help="Open ClipVault desktop application",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    # GUI does not need a database connection here.
    if args.command == "gui":
        open_gui()
        return

    db = Database()

    try:
        if args.command == "list":
            list_items(db)

        elif args.command == "search":
            search_items(db, args.query)

        elif args.command == "copy":
            copy_item(db, args.id)

        elif args.command == "delete":
            delete_item(db, args.id)

        elif args.command == "pin":
            pin_item(db, args.id)

        elif args.command == "unpin":
            unpin_item(db, args.id)

        elif args.command == "clear":
            clear_history(db)

        elif args.command == "count":
            show_count(db)

        elif args.command == "watch":
            watch_clipboard(db)

        elif args.command == "daemon":
            daemon(db)

    finally:
        db.close()


if __name__ == "__main__":
    main()