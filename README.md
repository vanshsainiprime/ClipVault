# ClipVault 📋

A simple clipboard history manager for Linux.

Ever copied something, copied something else, and then realized you needed the first thing again?

That's what ClipVault is for.

It keeps a local history of the things you copy, so you can search through them and copy them again whenever you need them.

**Everything stays on your computer.** There are no accounts, cloud sync, telemetry, or internet connection involved.

## What it can do

* Keep a history of your copied text
* Search through your clipboard history
* Copy an old entry back to your clipboard
* Pin things you want to keep
* Delete individual entries
* Clear unpinned entries
* Avoid saving the same thing repeatedly
* Run quietly in the background
* Start automatically when you log into Linux

## Getting started

### Requirements

ClipVault currently works on **Linux with X11**.

You'll need:

* Python 3.10+
* `xclip`
* X11

On Debian/Ubuntu-based systems:

```bash
sudo apt install xclip
```

### Install

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/clipvault.git
cd clipvault
```

Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install ClipVault:

```bash
pip install -e .
```

That's it.

Check that it works:

```bash
clipvault --help
```

## Using ClipVault

See your clipboard history:

```bash
clipvault list
```

Search for something:

```bash
clipvault search "hello"
```

Copy an old entry again:

```bash
clipvault copy 5
```

Pin an entry:

```bash
clipvault pin 5
```

Delete one:

```bash
clipvault delete 5
```

See how many entries are stored:

```bash
clipvault count
```

You can also run the clipboard monitor manually:

```bash
clipvault watch
```

Or run it as a background daemon:

```bash
clipvault daemon
```

## Where is my clipboard history stored?

ClipVault uses a small SQLite database stored locally at:

```text
~/.local/share/clipvault/clipboard.db
```

There is no separate database server or online storage.

## Privacy

Clipboard contents can sometimes contain passwords, tokens, addresses, code, and other private information.

That's why ClipVault is designed to stay local.

ClipVault doesn't need:

* An account
* Cloud storage
* Internet access
* Telemetry
* Analytics
* Remote APIs

Your clipboard history is stored on your own machine.

## Current status

ClipVault is still a work in progress.

The core clipboard monitoring, storage, CLI, background daemon, and automatic startup are working.

The next big part is the desktop interface.

### Roadmap

* [x] Clipboard monitoring
* [x] Local SQLite history
* [x] Search
* [x] Pin / unpin
* [x] Delete
* [x] Clear history
* [x] CLI
* [x] Background daemon
* [x] Automatic startup
* [ ] Desktop GUI
* [ ] `Super + V` clipboard popup
* [ ] Keyboard navigation
* [ ] System tray
* [ ] Wayland support
* [ ] Settings

## Why I made this

Linux has several clipboard managers already, but I wanted to build one myself and learn how the pieces fit together — clipboard events, local storage, background processes, and desktop integration.

ClipVault is the result.

## Tech

Built with:

* Python
* SQLite
* X11 / XFixes
* python-xlib
* xclip
* systemd

## License

MIT License.
