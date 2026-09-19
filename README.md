# ClipVault 📋

A simple clipboard history manager for Linux.

ClipVault keeps a local history of things you copy so you don't have to keep copying the same stuff again and again.

It runs locally, uses SQLite for storage, and doesn't need an account or internet connection.

## What it can do

- Save copied text to clipboard history
- Search through old clipboard entries
- Pin important entries
- Copy something back from the history
- Delete individual entries
- Clear unpinned history
- Avoid saving the same thing twice in a row
- Browse everything from a desktop GUI
- Open a quick clipboard popup with `Super + V`
- Use keyboard shortcuts to navigate the history
- Switch between dark and light themes
- Detect common types of content such as URLs, commands, code and file paths
- Run the clipboard watcher in the background

## How it works

ClipVault watches the X11 clipboard.

When you copy something, it gets saved to a local SQLite database.

The GUI and the `Super + V` popup both use the same database.

```text
Copy something
      ↓
X11 clipboard
      ↓
ClipboardWatcher
      ↓
SQLite
      ↓
ClipVault GUI / Super+V
```

The database is stored here:

```text
~/.local/share/clipvault/clipboard.db
```

## Screens / Interface

There are currently two ways to use ClipVault.

### Main GUI

The main window lets you search and manage your clipboard history.

You can:

- Search
- Copy
- Pin / unpin
- Delete
- Clear history
- Browse recent entries

### Super + V

Press:

```text
Super + V
```

and a small clipboard popup appears.

From there you can search your history and press `Enter` to copy an item.

`Esc` closes the popup.

## Requirements

Currently ClipVault is made for **Linux with X11**.

You'll need:

- Python 3.10+
- SQLite
- Tkinter
- xclip
- python-xlib

For Debian/Ubuntu based systems:

```bash
sudo apt install python3 python3-venv python3-tk xclip
```

Wayland isn't supported yet.

## Installation

Clone the repository:

```bash
git clone https://github.com/vanshsainiprime/ClipVault.git
cd ClipVault
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install ClipVault:

```bash
pip install -e .
```



## Running it

Start the GUI:

```bash
clipvault gui
````

Start the clipboard watcher:

```
clipvault watch
```

Run the background daemon:

```
clipvault daemon
```

## CLI

ClipVault also has a small CLI.

### List history

```
clipvault list
```

You can also specify how many entries to show:

```
clipvault list --limit 50
```

### Search

```
clipvault search "github"
```

For example:

```
clipvault search "python"
```

### Copy an entry

```
clipvault copy <ID>
```

Example:

```
clipvault copy 42
```

### Pin an entry

```
clipvault pin <ID>
```

### Unpin an entry

```
clipvault unpin <ID>
```

### Delete an entry

```
clipvault delete <ID>
```

### Clear history

This removes unpinned entries:

```
clipvault clear
```

Pinned entries are kept.

### Count entries

```
clipvault count
```

## Super+V background service

The `Super + V` popup can run as a systemd user service.

Create:

```text
~/.config/systemd/user/clipvault-hotkey.service
```

Add:

```ini
[Unit]
Description=ClipVault Global Super+V Popup
After=graphical-session.target

[Service]
Type=simple
ExecStart=/path/to/clipvault/.venv/bin/python -m clipvault.hotkey
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
```

Then run:

```bash
systemctl --user daemon-reload
systemctl --user enable --now clipvault-hotkey.service
```

Check it with:

```bash
systemctl --user status clipvault-hotkey.service
```

Replace `/path/to/clipvault` with the actual location of your project.

## Database

ClipVault uses SQLite.

The database is created automatically at:

```text
~/.local/share/clipvault/clipboard.db
```

Each entry contains:

- ID
- Content
- Creation time
- Pinned status

The default history limit is 1000 entries.

Pinned entries are kept when the history limit is reached.

## Project structure

```text
ClipVault/
│
├── clipvault/
│   ├── __init__.py
│   ├── clipboard.py
│   ├── database.py
│   ├── gui.py
│   ├── hotkey.py
│   ├── main.py
│   └── models.py
│
├── tests/
│
├── .gitignore
├── LICENSE
├── README.md
└── pyproject.toml
```

### Main files

`clipboard.py`

Handles X11 clipboard monitoring.

`database.py`

Handles the SQLite database and clipboard history.

`gui.py`

Contains the main desktop interface.

`hotkey.py`

Handles the global `Super + V` popup.

`main.py`

Contains the CLI commands and application entry point.

`models.py`

Contains the project's data models.

## Privacy

ClipVault is meant to stay completely local.

There is:

- No account
- No cloud sync
- No remote server
- No analytics
- No telemetry
- No internet requirement

Your clipboard history stays on your machine.

One thing to keep in mind: clipboard managers can save sensitive things too. If you copy passwords, API keys, tokens or private messages, ClipVault can save those as well.

## Development

Clone the repo and create the environment:

```bash
git clone https://github.com/vanshsainiprime/ClipVault.git
cd ClipVault

python3 -m venv .venv
source .venv/bin/activate

pip install -e .
```

Run the GUI:

```bash
clipvault gui
```

Run the clipboard watcher:

```bash
clipvault watch
```

Run tests:

```bash
pytest
```

## Tech used

- Python
- SQLite
- Tkinter
- python-xlib
- XFixes
- xclip
- systemd

## Why I made this

I wanted a clipboard manager that was simple, local and didn't need a bunch of extra stuff running in the background.

So I made ClipVault.

The basic idea is pretty much:

```text
Copy → Save → Search → Copy again
```

That's it.

## License

MIT License.

See [LICENSE](LICENSE) for the full license.

If you find a bug or have an idea, feel free to open an issue or pull request.
