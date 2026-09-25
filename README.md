# ClipVault 📋

**A fast, private, offline clipboard history manager for Linux.**

ClipVault keeps a local history of the things you copy, allowing you to quickly search, reuse, pin, and manage clipboard entries without relying on cloud services or an online account.

It runs locally, stores clipboard history in **SQLite**, and provides both a **desktop GUI** and a convenient **Super + V** quick-access popup.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python\&logoColor=white)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/Storage-SQLite-003B57?logo=sqlite\&logoColor=white)](https://www.sqlite.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-FCC624?logo=linux\&logoColor=black)](https://www.linux.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

##  Features

*  **Clipboard history** — Save copied text locally
*  **Search** — Quickly find previous clipboard entries
*  **Pin entries** — Keep important items from being removed
*  **Copy from history** — Restore any saved entry to the clipboard
*  **Delete entries** — Remove individual clipboard items
*  **Clear history** — Remove unpinned entries in one action
*  **Duplicate prevention** — Avoid storing the same clipboard content twice in a row
*  **Desktop GUI** — Browse and manage clipboard history visually
*  **Super + V popup** — Quickly access clipboard history
*  **Keyboard navigation** — Navigate and select entries without relying entirely on the mouse
*  **Themes** — Switch between dark and light themes
*  **Content detection** — Recognize common content such as URLs, commands, code, and file paths
*  **Background watcher** — Monitor the clipboard in the background

---

##  How It Works

ClipVault watches the **X11 clipboard** and stores copied text in a local SQLite database.

```text
             Copy something
                    │
                    ▼
             ┌─────────────┐
             │ X11 Clipboard│
             └──────┬──────┘
                    │
                    ▼
          ┌───────────────────┐
          │ Clipboard Watcher │
          └─────────┬─────────┘
                    │
                    ▼
             ┌─────────────┐
             │    SQLite   │
             │   Database  │
             └──────┬──────┘
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
   ┌─────────────┐     ┌──────────────┐
   │ Main GUI    │     │  Super + V   │
   └─────────────┘     │    Popup     │
                       └──────────────┘
```

Clipboard history is stored locally at:

```text
~/.local/share/clipvault/clipboard.db
```

---

## 🖥️ Interface

### Main GUI

The main ClipVault window provides a graphical interface for managing your clipboard history.

You can:

* Search clipboard entries
* Browse recent items
* Copy an entry
* Pin or unpin entries
* Delete individual entries
* Clear unpinned history
* Switch between dark and light themes

### ⚡ Super + V

ClipVault also provides a quick clipboard popup.

Press:

```text
Super + V
```

to open the popup.

From there you can:

* Search clipboard history
* Navigate through entries
* Press `Enter` to copy an entry
* Press `Esc` to close the popup

---

##  Requirements

ClipVault currently targets:

* **Linux**
* **X11**
* **Python 3.10+**
* **SQLite**
* **Tkinter**
* **xclip**
* **python-xlib**

### Debian / Ubuntu / Kali Linux

Install the required system packages:

```bash
sudo apt install python3 python3-venv python3-tk xclip
```

> **Note:** Wayland is not currently supported.

---

##  Installation

### 1. Clone the repository

```bash
git clone https://github.com/vanshsainiprime/ClipVault.git
cd ClipVault
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
```

### 3. Activate the environment

```bash
source .venv/bin/activate
```

### 4. Install ClipVault

```bash
pip install -e .
```

After installation, the `clipvault` command will be available inside the environment.

---

# Usage

## Start the GUI

```bash
clipvault gui
```

## Start the clipboard watcher

```bash
clipvault watch
```

## Start the background daemon

```bash
clipvault daemon
```

---

# CLI

ClipVault includes a small command-line interface for managing clipboard history.

### List history

```bash
clipvault list
```

Specify the number of entries:

```bash
clipvault list --limit 50
```

### Search history

```bash
clipvault search "github"
```

For example:

```bash
clipvault search "python"
```

### Copy an entry

```bash
clipvault copy <ID>
```

Example:

```bash
clipvault copy 42
```

### Pin an entry

```bash
clipvault pin <ID>
```

### Unpin an entry

```bash
clipvault unpin <ID>
```

### Delete an entry

```bash
clipvault delete <ID>
```

### Clear history

```bash
clipvault clear
```

This removes **unpinned** entries. Pinned entries are preserved.

### Count entries

```bash
clipvault count
```

---

# ⚡ Super + V Background Service

The `Super + V` popup can be run as a systemd user service.

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

Replace:

```text
/path/to/clipvault
```

with the actual path to your ClipVault installation.

Then reload systemd:

```bash
systemctl --user daemon-reload
```

Enable and start the service:

```bash
systemctl --user enable --now clipvault-hotkey.service
```

Check its status:

```bash
systemctl --user status clipvault-hotkey.service
```

---

# 🗄️ Database

ClipVault uses **SQLite** for local clipboard storage.

The database is created automatically at:

```text
~/.local/share/clipvault/clipboard.db
```

Each clipboard entry contains information including:

* ID
* Content
* Creation time
* Pinned status

The default history limit is **1000 entries**.

Pinned entries are preserved when the history limit is reached.

---

#  Project Structure

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

### Core modules

| File           | Purpose                                          |
| -------------- | ------------------------------------------------ |
| `clipboard.py` | X11 clipboard monitoring                         |
| `database.py`  | SQLite database and clipboard history management |
| `gui.py`       | Desktop graphical interface                      |
| `hotkey.py`    | Global `Super + V` popup                         |
| `main.py`      | CLI commands and application entry point         |
| `models.py`    | Application data models                          |

---

#  Privacy

ClipVault is designed to keep your clipboard history **local to your machine**.

There is:

* ❌ No account
* ❌ No cloud synchronization
* ❌ No remote server
* ❌ No analytics
* ❌ No telemetry
* ❌ No internet requirement

Your clipboard history is stored locally in SQLite.

###  Important

A clipboard manager can also save sensitive information.

If you copy things such as:

* Passwords
* API keys
* Authentication tokens
* Private messages
* Personal information

they may be stored in ClipVault's local database.

Always be aware of what you copy while using a clipboard history manager.

---

# 🛠️ Development

Clone the repository:

```bash
git clone https://github.com/vanshsainiprime/ClipVault.git
cd ClipVault
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the project in editable mode:

```bash
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

Run the test suite:

```bash
pytest
```

---

# Tech Stack

ClipVault is built using:

* **Python** — Application logic
* **Tkinter** — Desktop GUI
* **SQLite** — Local data storage
* **python-xlib** — X11 interaction
* **XFixes** — Clipboard monitoring support
* **xclip** — Clipboard integration
* **systemd** — Optional background service

---

# 💡 Why ClipVault?

I wanted a clipboard manager that was:

* Simple
* Local
* Private
* Lightweight
* Easy to use

without requiring an account, cloud service, or unnecessary infrastructure.

The basic idea is:

```text
Copy
  ↓
Save
  ↓
Search
  ↓
Copy again
```

That's ClipVault.

# 🤝 Contributing

Contributions, bug reports, and ideas are welcome.

If you find a bug or have an improvement in mind:

1. Open an issue
2. Describe the problem or proposed change
3. Fork the repository
4. Create a feature branch
5. Make your changes
6. Open a pull request

---

#  License

ClipVault is released under the **MIT License**.

See [LICENSE](LICENSE) for the full license text.

---

##  Author

**Vansh Saini**

GitHub: [@vanshsainiprime](https://github.com/vanshsainiprime)

---

<p align="center">
  Built for Linux users who want their clipboard history to stay on their machine.
</p>
