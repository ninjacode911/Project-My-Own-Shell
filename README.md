<div align="left">

<img width="100%" alt="GHBanner" src="https://github.com/ninjacode911/Github/raw/main/NAVNIT%20background.png" />



#  Build Your Own Shell — Python

A fully functional Unix shell built from scratch in Python as part of the "Build Your Own Shell" challenge. Zero external dependencies — only the Python standard library.

![Shell Demo](Screenshot.png)

---

##  Features

### Core Shell
- **REPL** — Interactive Read-Eval-Print Loop with `$ ` prompt
- **Command Parsing** — Handles single quotes, double quotes, and backslash escapes
- **External Programs** — Locates and runs executables via `PATH` resolution

### Builtins
| Command | Description |
|---|---|
| `echo <args>` | Print arguments to stdout |
| `type <cmd>` | Identify if a command is a builtin or external program |
| `pwd` | Print the current working directory |
| `cd <path>` | Change directory (supports absolute, relative, and `~`) |
| `exit` | Exit the shell |
| `history` | Display command history with indices |

### I/O Redirection
| Operator | Description |
|---|---|
| `>` / `1>` | Redirect stdout (overwrite) |
| `>>` / `1>>` | Redirect stdout (append) |
| `2>` | Redirect stderr (overwrite) |
| `2>>` | Redirect stderr (append) |

### Pipelines
- Two-command pipelines: `cat file \| wc`
- N-stage pipelines: `ls -la \| tail -n 5 \| head -n 3 \| grep "file"`
- Builtins in pipelines: `echo hello \| wc`

### Tab Completion
- Single match auto-complete with trailing space
- Longest common prefix completion for multiple matches
- Display all matches on double-Tab

### Command History
- `history` / `history <n>` — Display all or last N commands
- **Arrow key navigation** — Up/Down arrow to recall previous commands
- `history -r <file>` — Read history from a file
- `history -w <file>` — Write history to a file
- `history -a <file>` — Append new commands to a file
- **HISTFILE** — Automatic load on startup and save on exit

---

##  Getting Started

### Prerequisites
- Python 3.11+

### Run

```bash
# Clone the repository
git clone https://github.com/ninjacode911/codecrafters-shell-python.git
cd codecrafters-shell-python

# Run the shell
python app/main.py
```

### Example Session

```
$ echo hello world
hello world
$ type echo
echo is a shell builtin
$ pwd
/home/user
$ cd /tmp
$ ls -la | head -n 3
total 48
drwxrwxrwt 12 root root 4096 Feb 22 22:00 .
drwxr-xr-x 20 root root 4096 Feb 22 10:00 ..
$ history 3
    4  ls -la | head -n 3
    5  history 3
$ exit
```

---

##  Architecture

```
app/
└── main.py          # Single-file shell implementation (285 lines)
```

| Function | Purpose |
|---|---|
| `parse_command()` | Tokenizes input respecting quotes and escapes |
| `get_executable_path()` | Searches PATH for executables |
| `run_builtin()` | Dispatches all builtin commands |
| `main()` | REPL loop, readline setup, pipelines, redirection |

---

##  What I Learned

- How shells work under the hood — REPL loops, command parsing, and process management
- Unix process model — `fork`, `exec`, pipes, and file descriptors via Python's `subprocess`
- Terminal I/O — `readline` library for tab completion, history navigation, and line editing
- State machine parsing — handling nested quotes, escape characters, and special tokens
- Inter-process communication — connecting processes via `os.pipe()` and `subprocess.PIPE`
- File descriptor management — redirection of `stdout` and `stderr` to files

---

##  Challenge Progress

All **36 stages** completed, including:
- ✅ Basic REPL & builtins
- ✅ PATH resolution & external programs
- ✅ Quoting & escape sequences
- ✅ I/O redirection (stdout & stderr)
- ✅ Tab completion (single, multiple, display)
- ✅ N-stage pipelines with builtin support
- ✅ Full command history with file persistence
