# Chapter 1 — Computer basics (start here if you have never coded)

[README](../../README.md) · Next: [Chapter 2 →](02-install-and-run.md)

This chapter assumes **nothing**. If you already know what a terminal, Git and Python are, skip to
[Chapter 2](02-install-and-run.md).

---

## 1.1 Files and folders

Everything on a computer is stored in **files** (a photo, a document, a program) that live inside
**folders** (also called **directories**). Folders can contain other folders, forming a tree:

```
Pneumonia-Check/            ← the project folder
├── README.md               ← a file (this guide's front page)
├── backend/                ← a folder
│   ├── app/
│   │   └── main.py         ← a file inside app/, inside backend/
│   └── requirements.txt
└── frontend/
```

A **path** is the address of a file, written by joining folder names with `/`
(on Windows you will also see `\`): `Pneumonia-Check/backend/app/main.py`.

A **file extension** — the letters after the last dot — tells you the file type:

| Extension                | What it is                                                                          |
| ------------------------ | ----------------------------------------------------------------------------------- |
| `.py`                    | Python code                                                                         |
| `.ts`, `.tsx`            | TypeScript code (`.tsx` = TypeScript that also contains HTML-like markup for React) |
| `.json`                  | Data in JSON format (see Chapter 5.7)                                               |
| `.md`                    | Markdown — formatted text, like this guide                                          |
| `.png`, `.jpg`, `.jpeg`  | Images                                                                              |
| `.pth`, `.onnx`          | Saved neural-network models                                                         |
| `.csv`                   | A table saved as text (comma-separated values)                                      |
| `.yml`, `.yaml`, `.toml` | Configuration files                                                                 |

## 1.2 The terminal (command line)

A **terminal** is a window where you type commands instead of clicking. Developers use it because
it is precise and repeatable: a command written in this guide will do exactly the same thing on
your computer.

**How to open one:**

- **macOS:** press `⌘ Command` + `Space`, type `Terminal`, press `Enter`.
- **Windows:** press the `Windows` key, type `PowerShell`, press `Enter`.
- **Linux:** press `Ctrl` + `Alt` + `T`.

You will see a **prompt** — some text ending in `$`, `%` or `>` — and a blinking cursor. Type a
command and press `Enter` to run it.

### The ten commands you will use

| Command                    | What it does                                                | Example                |
| -------------------------- | ----------------------------------------------------------- | ---------------------- |
| `pwd`                      | Print **w**orking **d**irectory — which folder you are "in" | `pwd`                  |
| `ls` (Windows: `dir`)      | List the files in the current folder                        | `ls`                   |
| `cd folder`                | **C**hange **d**irectory — go into a folder                 | `cd backend`           |
| `cd ..`                    | Go up one folder                                            | `cd ..`                |
| `mkdir name`               | Make a new folder                                           | `mkdir my-project`     |
| `cp a b` (Windows: `copy`) | Copy a file                                                 | `cp .env.example .env` |
| `python3 file.py`          | Run a Python program (Windows: `python` or `py`)            | `python3 train.py`     |
| `npm install`              | Download the website's dependencies                         | `npm install`          |
| `Ctrl` + `C`               | **Stop** the program currently running in this terminal     | —                      |
| `↑` (up arrow)             | Bring back the previous command                             | —                      |

Tips:

- Press `Tab` while typing a file or folder name and the terminal completes it for you.
- If a path contains spaces, wrap it in quotes: `cd "My Documents"`.
- Lines in this guide starting with `#` are **comments** — explanations, not commands. You may paste
  them; the terminal ignores them.
- When a guide shows `$ command`, do **not** type the `$`; it represents the prompt.

## 1.3 What we need to install, and why

| Tool                                | What it is                                                                                     | Why this project needs it                                         |
| ----------------------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| **Git**                             | A version-control tool: it records every change to the code and downloads projects from GitHub | To download ("clone") this project and to upload your changes     |
| **Python 3.10+**                    | A programming language, popular for science and AI                                             | The backend server and all AI training code are written in Python |
| **Node.js 20+** (includes **npm**)  | Lets JavaScript run outside the browser; npm downloads JavaScript libraries                    | Builds and runs the website during development                    |
| **VS Code** (optional, recommended) | A free code editor                                                                             | To read and edit the code comfortably                             |

### macOS

1. Install **Homebrew**, a tool that installs other tools. Open Terminal and paste the single line
   shown on https://brew.sh (it begins with `/bin/bash -c "$(curl -fsSL ...`). Press `Enter`, type
   your Mac password when asked (nothing appears while you type — that is normal), and wait.
   At the end Homebrew prints two or three "Next steps" commands — run them.
2. Install the tools:
   ```bash
   brew install git python@3.11 node
   ```
3. Check they work (each prints a version number):
   ```bash
   git --version
   python3 --version     # must be 3.10 or newer
   node --version        # must be v20 or newer
   ```

### Windows

1. **Git:** download "Git for Windows" from https://git-scm.com/download/win, run the installer,
   accept the defaults.
2. **Python:** download Python 3.11 from https://www.python.org/downloads/windows/. In the first
   installer screen **tick "Add python.exe to PATH"**, then click _Install Now_.
3. **Node.js:** download the **LTS** installer from https://nodejs.org and accept the defaults.
4. **Close and reopen PowerShell**, then check:
   ```powershell
   git --version
   python --version
   node --version
   ```
   If PowerShell refuses to run scripts later (an error mentioning "execution policy"), run once:
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   ```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

### VS Code (all systems)

Download from https://code.visualstudio.com, install, then _File → Open Folder…_ and pick the
project folder. Useful extensions (left sidebar → Extensions icon): **Python**, **Pylance**,
**ESLint**, **Prettier**, **Tailwind CSS IntelliSense**. VS Code also has a built-in terminal:
_Terminal → New Terminal_.

## 1.4 Git and GitHub in five minutes

- **Git** keeps the full history of a project. Each saved snapshot is a **commit**, with a message
  describing the change.
- **GitHub** is a website that stores Git projects (**repositories**, or "repos") online so people can
  share them.
- A **branch** is a line of development; ours is called `main`.

The commands you need:

```bash
git clone https://github.com/UzumakiAnirudh/Pneumonia-Check.git   # download a copy
git status                       # what changed since the last commit?
git add -A                       # include all changes in the next commit
git commit -m "Describe what you changed"
git push                         # upload commits to GitHub
git pull                         # download other people's new commits
```

The first time you commit, Git asks who you are:

```bash
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
```

To **push** you need permission on the repository. GitHub no longer accepts your account password
in the terminal; the easiest way to log in is the GitHub CLI: `brew install gh` (macOS) or
https://cli.github.com, then `gh auth login` and follow the browser prompts.

## 1.5 What "running" a web app means

This project is two programs that talk to each other:

- The **backend** (a _server_) waits for requests on a **port** — a numbered door on your computer.
  Ours uses port **8000**.
- The **frontend** (the _website_) is served on port **5173** during development.
- Your browser opens `http://localhost:5173`. **localhost** means "this computer".

Both programs keep running until you stop them with `Ctrl + C`, so each needs **its own terminal
window**. Closing the terminal also stops the program.

## 1.6 Reading error messages (do not panic)

Errors are normal — professional developers see dozens a day. A Python error ends with a line such as:

```
ModuleNotFoundError: No module named 'fastapi'
```

Read the **last line first**: it says what went wrong (here: a library is not installed — you
probably forgot to activate the virtual environment, see Chapter 2). Copy that last line into a
search engine or into [Chapter 23 — Troubleshooting](23-troubleshooting-faq.md).

---

Next: **Chapter 2 — Install and run the app** → [02-install-and-run.md](02-install-and-run.md)
