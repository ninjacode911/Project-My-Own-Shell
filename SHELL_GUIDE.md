# 🐚 Building a Shell from Scratch — The Complete Master Guide

> **What you've accomplished:** You haven't just learned how to *use* a shell — you've
> reverse-engineered the core mechanics of how an operating system interacts with the
> user, handles concurrent processes, and manages data streams. Building this foundational
> system from scratch gives you a massive advantage when architecting complex CI/CD
> workflows or automating deployment pipelines, as you now know exactly what is happening
> under the hood.

---

## Table of Contents

1.  [What is a Shell?](#1-what-is-a-shell)
2.  [The REPL — The Heartbeat of Every Shell](#2-the-repl--the-heartbeat-of-every-shell)
3.  [Phase 1: Environment & Directory Navigation](#3-phase-1-environment--directory-navigation)
4.  [Phase 2: The Lexer & Parsing Engine (Quoting & Escaping)](#4-phase-2-the-lexer--parsing-engine-quoting--escaping)
5.  [Phase 3: I/O Stream Redirection](#5-phase-3-io-stream-redirection)
6.  [Phase 4: Concurrency & Pipelines](#6-phase-4-concurrency--pipelines)
7.  [Phase 5: Interactive User Experience (Tab Completion)](#7-phase-5-interactive-user-experience-tab-completion)
8.  [Phase 6: Session State & History Management](#8-phase-6-session-state--history-management)
9.  [How the Shell Finds & Runs External Programs](#9-how-the-shell-finds--runs-external-programs)
10. [Complete Python API Reference](#10-complete-python-api-reference)
11. [Stages Completed](#11-stages-completed)

---

## 1. What is a Shell?

A **shell** is a program that acts as the interface between you (the human) and the
operating system. When you open a "terminal" or "command prompt", the program that
reads your commands and executes them **is** the shell.

### Why is it called a "shell"?

The name comes from the idea that it is the outermost "shell" around the operating
system kernel. You interact with the shell, and the shell interacts with the kernel
on your behalf.

```
┌──────────────────────────┐
│       You (Human)        │
├──────────────────────────┤
│       Shell (bash/zsh)   │  ← You built this!
├──────────────────────────┤
│       OS Kernel          │
├──────────────────────────┤
│       Hardware (CPU/RAM) │
└──────────────────────────┘
```

### What does a shell actually do?

Every shell in the world (Bash, Zsh, Fish, PowerShell) does these four things:

1.  **Reads** your input (what you type after the `$` prompt)
2.  **Parses** it (figures out what command you want and what the arguments are)
3.  **Executes** it (either runs a builtin function or launches an external program)
4.  **Prints** the result (shows you the output or an error)

Then it loops back to step 1. This is called a **REPL**.

### Builtins vs. External Commands

| Type | Definition | Example | Where it runs |
|---|---|---|---|
| **Builtin** | A command handled inside the shell process itself | `cd`, `echo`, `type`, `pwd`, `exit`, `history` | Inside the shell |
| **External** | A separate executable file found in `PATH` | `ls`, `cat`, `grep`, `wc` | In a new child process |

**Why do builtins exist?** Some commands **cannot** be external programs because they
need to modify the shell's own state. The most important example is `cd`:

If `cd` were an external program, it would:
1.  Fork a child process
2.  The child would change **its own** working directory to `/tmp`
3.  The child would exit
4.  The parent shell's working directory would be **unchanged**

This is because each process has its own working directory. A child process **cannot**
change its parent's directory. Therefore, `cd` **must** be handled inside the shell
process itself. That's what makes it a "builtin."

---

## 2. The REPL — The Heartbeat of Every Shell

**REPL** stands for **R**ead → **E**val → **P**rint → **L**oop. It is the most
fundamental concept in any interactive program.

### The Simplest Shell in Python

```python
while True:                    # Loop (L)
    command = input("$ ")      # Read (R)
    # ... figure out command   # Eval (E)
    # ... print result         # Print (P)
```

That's it. Every shell on earth is built around this simple loop.

### Why `input("$ ")` and not `print("$ ")` + `input()`?

This is a subtle but critical distinction:

```python
# ❌ BAD — readline doesn't know where the prompt ends
sys.stdout.write("$ ")
sys.stdout.flush()
command = input()

# ✅ GOOD — readline knows the prompt is "$ "
command = input("$ ")
```

When you pass the prompt string directly to `input()`, Python's `readline` library
knows exactly how many characters the prompt occupies. This is essential for:

-   **Arrow key navigation** — Without it, pressing Up/Down can corrupt the display
    because readline doesn't know where your cursor should return to.
-   **Tab completion** — readline needs to know the prompt width to correctly
    position the cursor after inserting a completion.
-   **Line editing** — If you use Home/End keys, readline uses the prompt width to
    calculate the start of editable text.

### Handling Invalid Commands

If a command doesn't match any builtin or external program, print an error:

```python
print(f"{cmd}: command not found", file=sys.stderr)
```

**Lesson:** Always write errors to `stderr` (`sys.stderr`), not `stdout`. This keeps
error messages separate from normal output, which matters for redirection and pipelines.

### Handling `Ctrl+D` (EOF)

When a user presses `Ctrl+D`, it sends an **End Of File** signal to `input()`,
which raises an `EOFError`. A well-behaved shell should catch this and exit gracefully:

```python
try:
    command = input("$ ")
except EOFError:
    break  # Exit the REPL cleanly
```

---

## 3. Phase 1: Environment & Directory Navigation

At its core, the shell must interact with the operating system's file hierarchy and
maintain its current location.

### `pwd` — Print Working Directory

-   **Syntax:** `pwd`
-   **Logic:** Retrieves and prints the absolute path of the current working directory.

```python
print(os.getcwd(), file=out)
```

`os.getcwd()` returns the **absolute path** of the current working directory.

### `cd` — Change Directory

-   **Syntax:** `cd <path>`

```python
path = parts[1]
if path == "~":
    path = os.path.expanduser("~")   # Reads HOME env var
os.chdir(path)
```

**Three types of paths `cd` supports:**

| Input | Type | Description |
|---|---|---|
| `/tmp/foo` | **Absolute** | Starts from root `/`. Goes directly to that location. |
| `./bar` or `../` | **Relative** | Navigation relative to the current directory. `.` = current, `..` = parent. |
| `~` | **Home** | Reads the `HOME` environment variable and navigates there. |

**Relative path details:**
-   `.` — Current directory (`cd ./folder` = `cd folder`)
-   `..` — Parent directory
-   Bare names act as relative paths (`cd folder` = `cd ./folder`)

**Error Handling:** If the directory doesn't exist, the shell strictly outputs
`cd: <directory>: No such file or directory` and leaves the current working directory
unchanged.

```python
try:
    os.chdir(path)
except Exception:
    print(f"cd: {path}: No such file or directory", file=err)
```

### `echo` — Print Arguments

-   **Syntax:** `echo <args>`

```python
print(" ".join(parts[1:]), file=out)
```

`parts[1:]` takes everything after `"echo"`. For example:
-   Input: `echo hello world`
-   `parts` = `["echo", "hello", "world"]`
-   `parts[1:]` = `["hello", "world"]`
-   `" ".join(...)` = `"hello world"`

### `type` — Identify Commands

`type` answers the question: "Is this command a builtin or an external program?"

```python
if target in builtins_list:
    print(f"{target} is a shell builtin")
else:
    path = get_executable_path(target)
    if path:
        print(f"{target} is {path}")
    else:
        print(f"{target}: not found")
```

It checks builtins **first**, then searches PATH — this mirrors the real lookup
order that shells use when executing commands.

### `exit` — Terminate the Shell

```python
if parts[0] == "exit":
    # Save history to HISTFILE...
    break  # Exits the while True loop
```

Before breaking, the shell saves history to `HISTFILE` if it's set.

### How Builtins Are Organized — The Dispatch Pattern

```python
def run_builtin(parts, out, err, builtins_list, history_list, last_append_ptr):
    cmd = parts[0]
    if cmd == "echo":      ...
    elif cmd == "pwd":     ...
    elif cmd == "cd":      ...
    elif cmd == "type":    ...
    elif cmd == "history": ...
```

The key insight is that `out` and `err` are **configurable streams**. By default they
are `sys.stdout` and `sys.stderr`, but when used in a pipeline or with redirection,
they can be files or `io.StringIO()` buffers. This makes builtins work seamlessly
with pipes and redirects.

**Key Python APIs for this phase:**

| API | Purpose |
|---|---|
| `os.getcwd()` | Returns the current working directory |
| `os.chdir(path)` | Changes the current working directory |
| `os.path.expanduser("~")` | Expands `~` to the user's home directory |
| `os.environ.get("HOME")` | Reads the HOME environment variable |

---

## 4. Phase 2: The Lexer & Parsing Engine (Quoting & Escaping)

You upgraded from simple string splitting to a **stateful parsing engine** that
understands shell grammar, allowing users to pass complex arguments safely.

### The Problem

When you type:

```bash
echo "hello world" 'it'\''s' great
```

The shell must split this into **three** arguments:
1.  `hello world` (double quotes preserved the space)
2.  `it's` (the escaped single quote)
3.  `great`

Simple `str.split(" ")` would give 4 wrong results. We need a proper **parser**.

### The State Machine Approach

Our parser processes input **one character at a time**, keeping track of whether
we're inside single quotes, double quotes, or normal mode:

```python
quote_char = None   # None = normal mode
                    # "'"  = single quote mode
                    # '"'  = double quote mode

for each character:
    if quote_char is None:          # NORMAL MODE
        if char == '\\':   → escape next character
        if char in "'\"":  → enter quoted mode (set quote_char)
        if char == ' ':    → end current argument
        otherwise:         → add to current argument

    elif quote_char == "'":         # SINGLE QUOTE MODE
        if char == "'":    → exit quoted mode (reset quote_char to None)
        otherwise:         → add literally (no escaping!)

    elif quote_char == '"':         # DOUBLE QUOTE MODE
        if char == '"':    → exit quoted mode
        if char == '\\':   → check if next char is special
        otherwise:         → add literally
```

### Quoting Rules — Explained Thoroughly

#### Single Quotes (`'...'`) — Strict Literalism

**Every character inside single quotes is treated exactly as written.** Spaces are
preserved as part of the argument, not as delimiters. Special characters lose their
meaning. Not even backslash has any power here.

```bash
echo 'hello   world'        # Output: hello   world    (spaces preserved)
echo 'hello\nworld'         # Output: hello\nworld     (literal backslash-n)
echo '$HOME is $HOME'       # Output: $HOME is $HOME   ($ is literal)
```

**How to include a single quote literal?**

You can't put a single quote inside single quotes. Instead, end the quote, escape
a quote, and restart:

```bash
echo 'it'\''s fine'          # Output: it's fine
#     ^^^ ^^ ^^^^^^
#      |   |    |
#      |   |    └── single-quoted string: "s fine"
#      |   └────── escaped literal quote: '
#      └────────── single-quoted string: "it"
```

#### Double Quotes (`"..."`) — Partial Literalism

Preserves whitespace like single quotes, but allows **specific escape sequences**
to be evaluated inside.

**Characters that can be escaped with `\` inside double quotes:**

| Escape | Result |
|---|---|
| `\"` | Literal `"` |
| `\\` | Literal `\` |
| `\$` | Literal `$` |
| `` \` `` | Literal `` ` `` |

**If `\` precedes anything else, the backslash is treated as a literal character
and is NOT dropped:**

```bash
echo "hello\nworld"         # Output: hello\nworld    (\n is NOT special here)
echo "say \"hi\""           # Output: say "hi"        (\" IS special)
echo "back\\slash"          # Output: back\slash      (\\ IS special)
```

#### Backslash Outside Quotes — Absolute Escape

Outside of any quotes, `\` **always** escapes the very next character. The `\` is
dropped, and the next character (even a space) becomes a literal part of the argument.

```bash
echo hello\ world           # Output: hello world     (escaped space)
echo hello\\world           # Output: hello\world     (escaped backslash)
echo three\ \ \ spaces      # Output: three   spaces  (three escaped spaces)
```

#### Concatenation — Adjacent Strings Merge

Adjacent strings (quoted or unquoted) are merged into a **single argument**:

```bash
echo 'hello'"world"          # Output: helloworld     (two quoted strings merged)
echo he"ll"o                 # Output: hello          (unquoted + quoted merged)
```

---

## 5. Phase 3: I/O Stream Redirection

You implemented routing for standard streams using **File Descriptors**.

### The Unix I/O Model

Every process in Unix has three standard streams:

| Stream | File Descriptor | Default | Purpose |
|---|---|---|---|
| **stdin** | FD 0 | Keyboard | Input to the program |
| **stdout** | FD 1 | Terminal screen | Normal output |
| **stderr** | FD 2 | Terminal screen | Error messages |

**Redirection** means changing where these streams point — from the terminal to a
file, or from one process to another.

### Supported Redirection Operators

#### Standard Output Redirection (`>` and `1>`)

-   **Syntax:** `cmd > file.txt` or `cmd 1> file.txt`
-   **Logic:** Captures the command's normal output and writes it to a file.
    **Overwrites** the file if it exists, creates it if it doesn't. Stderr still
    prints to the terminal.

```python
stdout_file = open(stdout_file_path, "w")    # "w" = overwrite
subprocess.run(parts, stdout=stdout_file)
stdout_file.close()
```

**Why is `1>` the same as `>`?** Because `>` defaults to file descriptor 1 (stdout).
The `1` is implicit.

#### Standard Error Redirection (`2>`)

-   **Syntax:** `cmd 2> error.log`
-   **Logic:** Captures only the **error output** and writes it to a file. Overwrites
    existing files. Stdout still prints to the terminal.

```python
stderr_file = open(stderr_file_path, "w")
subprocess.run(parts, stderr=stderr_file)
```

#### Append Output (`>>` and `1>>`)

-   **Syntax:** `cmd >> file.txt`
-   **Logic:** Appends standard output to the **very end** of the file without
    deleting existing content.

```python
stdout_file = open(stdout_file_path, "a")    # "a" = append
```

#### Append Error (`2>>`)

-   **Syntax:** `cmd 2>> error.log`
-   **Logic:** Appends standard error to the very end of the file.

### Overwrite vs. Append — Critical Distinction

| Mode | Operator | Python | Behavior |
|---|---|---|---|
| **Overwrite** | `>` | `open(path, "w")` | Creates file or **truncates** existing contents to zero |
| **Append** | `>>` | `open(path, "a")` | Creates file or **adds** to the end of existing contents |

> **Warning:** Using `>` on an existing file will **destroy** its previous contents.
> Using `>>` preserves them. This is one of the most common mistakes in shell scripting.

### How Redirection is Parsed

Redirection tokens are parsed **before** command execution:

```python
while i < len(initial_parts):
    p = initial_parts[i]
    if p in (">", "1>"):
        stdout_file_path = initial_parts[i + 1]   # Next token is the filename
        stdout_mode = "w"
        i += 2                                      # Skip the operator and filename
    elif p in (">>", "1>>"):
        stdout_file_path = initial_parts[i + 1]
        stdout_mode = "a"
        i += 2
    elif p == "2>":
        stderr_file_path = initial_parts[i + 1]
        stderr_mode = "w"
        i += 2
    elif p == "2>>":
        stderr_file_path = initial_parts[i + 1]
        stderr_mode = "a"
        i += 2
    else:
        parts.append(p)                            # Regular argument
        i += 1
```

---

## 6. Phase 4: Concurrency & Pipelines (`|`)

You implemented **Inter-Process Communication (IPC)**, allowing asynchronous,
real-time data streaming between concurrent processes.

### What is a Pipe?

A **pipe** is a one-way data channel between two processes. The output of the first
process flows directly into the input of the second process, **without ever touching
the disk**.

```bash
cat /etc/passwd | grep root | wc -l
```

This creates **two pipes** (N commands require N-1 pipes):

```
┌─────┐  pipe1  ┌──────┐  pipe2  ┌─────┐
│ cat │ ──────→ │ grep │ ──────→ │ wc  │ → terminal
└─────┘         └──────┘         └─────┘
```

### Basic Pipelines (Two Commands)

-   **Syntax:** `cat file.txt | wc`
-   **Logic:** Uses `os.pipe()` and `subprocess.Popen()`. The stdout of the left
    command is directly connected to the stdin of the right command.

```python
p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE)
p2 = subprocess.Popen(cmd2, stdin=p1.stdout)
p1.stdout.close()      # ← CRITICAL LINE (see explanation below)
p2.communicate()       # Wait for p2 to finish
```

**Why is `p1.stdout.close()` critical?**

This is one of the most subtle concepts in Unix programming:

1.  `p2` (e.g., `head -n 5`) reads 5 lines and decides it's done.
2.  `p2` closes its stdin (the read end of the pipe).
3.  `p1` (e.g., `cat huge_file`) tries to write more data to the pipe.
4.  Normally, the OS would send `p1` a **SIGPIPE** signal, telling it "nobody is
    reading, stop writing."
5.  **But** the shell process still has a reference to `p1.stdout` (the write end).
    As long as **any** process holds the write end open, the OS won't send SIGPIPE.
6.  **Result without close:** `p1` hangs forever, waiting for someone to read.

By calling `p1.stdout.close()` in the parent shell, we release our reference,
allowing the OS to properly signal `p1` to stop.

### Multi-Stage Pipelines

-   **Syntax:** `cmd1 | cmd2 | cmd3 | cmd4`
-   **Logic:** Dynamically managing an array of pipes. N commands require N-1 pipes.

```python
stages = split_by_pipe(parts)
curr_in = None

for i, stage in enumerate(stages):
    is_last = (i == len(stages) - 1)

    p = subprocess.Popen(
        stage,
        stdin=curr_in,
        stdout=subprocess.PIPE if not is_last else None
    )

    if curr_in is not None:
        curr_in.close()         # Aggressively close unused pipe ends

    if not is_last:
        curr_in = p.stdout      # Chain: next command reads from this output
```

**Crucial logic:** Aggressively closing unused pipe file descriptors in parent and
child processes ensures streams successfully trigger an **EOF** (End of File) and
don't hang indefinitely.

### Builtins in Pipelines

Builtins don't create child processes, so they can't use pipes directly. The solution
depends on where the builtin appears:

#### Builtin as the First Command (`echo "hello" | wc`)

Safely route I/O streams for commands that execute internally:

```python
# 1. Run builtin into an in-memory buffer
buf = io.StringIO()
run_builtin(cmd1_parts, buf, ...)

# 2. Feed the buffer's contents to the external command
subprocess.run(cmd2_parts, input=buf.getvalue().encode())
```

`io.StringIO()` is an in-memory text stream — it behaves like a file but lives
entirely in RAM.

#### Builtin in the Middle of a Chain

Use `os.pipe()` to create a manual pipe:

```python
r, w = os.pipe()         # r = read end (file descriptor), w = write end
os.write(w, data)        # Write the builtin's output to the write end
os.close(w)              # Close write end (signals EOF to reader)
# Pass 'r' as stdin to the next command
```

### Key Concepts Learned

| Concept | Description |
|---|---|
| `subprocess.Popen()` | Starts a process **without waiting** — essential for concurrent pipelines |
| `subprocess.PIPE` | Creates a pipe to capture stdout/stdin |
| `io.StringIO()` | In-memory text stream for capturing builtin output |
| `os.pipe()` | Low-level OS pipe: returns `(read_fd, write_fd)` |
| SIGPIPE | Signal sent when writing to a pipe nobody is reading |
| EOF | End of File — triggered when all write ends of a pipe are closed |

---

## 7. Phase 5: Interactive User Experience (Tab Completion)

You transformed the shell into a truly interactive UI by reading raw keystrokes and
scanning the `PATH` environment variable.

### Setting Up readline

```python
import readline

readline.set_completer(my_completer_function)     # Register completion logic
readline.set_completer_delims('')                 # Don't split on any delimiter
readline.parse_and_bind("tab: complete")          # Bind Tab key to completion
```

### The Completer Function

readline calls your completer function repeatedly with increasing `state` values
(0, 1, 2, ...) until you return `None`:

```python
def completer(text, state):
    # 'text' = what the user has typed so far (the prefix)
    # 'state' = which match to return (0 = first, 1 = second, etc.)

    matches = [b for b in builtins if b.startswith(text)]
    # Also search PATH executables...
    matches = sorted(list(set(matches)))

    if state < len(matches):
        return matches[state]
    return None                # No more matches → stop
```

### Three Completion Scenarios

#### Scenario 1: Single Executable Match

**Action:** User types prefix, hits `<TAB>`.
**Logic:** If exactly one executable in `PATH` matches the prefix, auto-complete the
word and append a trailing space.

```python
if len(matches) == 1:
    return matches[0] + " "   # Trailing space = "I'm done completing"
```

#### Scenario 2: Multiple Matches with a Common Prefix

**Action:** User types `xy` + `<TAB>`. Matches are `xyz_1`, `xyz_2`, `xyz_3`.
The shell completes to `xyz_` (the **longest common prefix**):

```python
common = os.path.commonprefix(matches)    # "xyz_"
if len(common) > len(text):
    return common                         # Complete to the common prefix
```

`os.path.commonprefix()` finds the longest string that is a prefix of ALL items
in the list. Despite its name containing "path", it works on any strings.

#### Scenario 3: No More Common Prefix (Ambiguity)

**Action:** User types `xyz_` + `<TAB>`. Matches are `xyz_1` and `xyz_2`. There's
no further common prefix to complete to.

-   **1st Tab:** Rings the terminal bell (`\x07`) visually/audibly. No visible change.
-   **2nd Tab:** Prints all matching executables on a new line in **alphabetical order**,
    separated by **two spaces** (`  `). Redraws the prompt and fully restores the
    user's initial input buffer.

```python
def display_matches(substitution, matches, longest_match_len):
    valid = sorted(set(m for m in matches if m))
    sys.stdout.write("\n" + "  ".join(valid) + "\n$ " + readline.get_line_buffer())
    sys.stdout.flush()

readline.set_completion_display_matches_hook(display_matches)
```

`readline.get_line_buffer()` returns whatever the user has typed so far, so we can
re-display it after showing the matches.

---

## 8. Phase 6: Session State & History Management

You built a persistent "memory" for the REPL, tracking an indexed ledger of user
inputs across commands and across sessions.

### Two Separate History Systems

Our shell maintains **two** history systems that must be kept in sync:

| System | Used For | Storage |
|---|---|---|
| `history_list` (Python list) | The `history` builtin command output | In-memory list |
| readline's internal buffer | Arrow key Up/Down navigation | readline C library |

```python
# After every command, add to BOTH:
history_list.append(command_raw)           # For 'history' command
readline.add_history(command_raw)          # For arrow keys
```

### The `history` Builtin

-   **Syntax:** `history`
-   **Logic:** Prints the session ledger. Every executed command (even invalid ones
    and the `history` command itself) is recorded.
-   **Formatting:** 1-based index, properly padded with spaces.

```python
for i, h in enumerate(history_list, 1):
    print(f"{i:5}  {h}")
```

The format string `f"{i:5}"` right-aligns the number in a field of 5 characters:

```
    1  echo hello
    2  ls -la
   10  history
  100  cd /tmp
```

### Limiting History (`history <n>`)

-   **Syntax:** `history <n>`
-   **Logic:** Prints only the most recent n commands, while flawlessly preserving
    their **absolute execution index** numbers.

```python
limit = int(parts[1])                     # e.g., 3
start_idx = max(0, len(history_list) - limit)
for i in range(start_idx, len(history_list)):
    print(f"{i+1:5}  {history_list[i]}")
```

### Interactive Navigation (Up/Down Arrows)

-   **Action:** `<UP ARROW>` and `<DOWN ARROW>`
-   **Logic:** Replaces the current terminal buffer with past commands, allowing the
    user to press `<ENTER>` to re-execute them (powered by readline).

readline handles Up/Down arrows automatically once you call `readline.add_history()`.
But there's a subtle bug to avoid — **deduplication**:

```python
# ❌ BAD — causes duplicate entries, making Up arrow seem "stuck"
readline.add_history(command_raw)

# ✅ GOOD — deduplication check
hist_len = readline.get_current_history_length()
if hist_len == 0 or readline.get_history_item(hist_len) != command_raw:
    readline.add_history(command_raw)
```

Without the deduplication check, typing the same command twice in a row would
require two Up presses to navigate past it, which feels broken.

### File I/O History Flags

#### `history -r <file>` — Read from File

Opens a file, strips newlines, and appends the contents to the active in-memory
ledger. Ignores empty lines.

```python
with open(path, "r") as f:
    for line in f:
        h_line = line.rstrip("\r\n")
        if h_line:
            history_list.append(h_line)
            readline.add_history(h_line)
```

#### `history -w <file>` — Write to File (Overwrite)

**Overwrites** a file with the entire current in-memory ledger.

```python
with open(path, "w") as f:
    for h_item in history_list:
        f.write(h_item + "\n")           # Each command on its own line
```

The file always ends with a trailing newline (the "empty line" at the end).

#### `history -a <file>` — Append to File (Incremental)

Utilizes a **sync pointer** to append only newly executed commands to the file,
preventing duplicates.

```python
last_append_ptr = [0]     # Index of the first unsaved command

# When appending:
with open(path, "a") as f:
    for i in range(last_append_ptr[0], len(history_list)):
        f.write(history_list[i] + "\n")
last_append_ptr[0] = len(history_list)   # Update the pointer
```

**Why is `last_append_ptr` a list `[0]` instead of an integer `0`?**

In Python, integers are **immutable**. If you pass `ptr = 0` to a function and the
function does `ptr = 5`, the original variable is unaffected. But if you pass
`ptr = [0]` and the function does `ptr[0] = 5`, the change is visible to the
caller because lists are **mutable**.

This is a common Python pattern for creating **pass-by-reference** semantics.

### Boot Sequence & Teardown (`HISTFILE`)

The `HISTFILE` environment variable tells the shell where to store history
permanently.

#### Startup — Before the First Prompt

Before the first prompt, the shell checks the `HISTFILE` environment variable.
If the file exists, it pre-loads the commands into memory.

```python
histfile = os.environ.get("HISTFILE")
if histfile and os.path.exists(histfile):
    with open(histfile, "r") as f:
        for line in f:
            h_line = line.rstrip("\r\n")
            if h_line:
                history_list.append(h_line)
                readline.add_history(h_line)

# Important: set the append pointer AFTER loading
last_append_ptr = [len(history_list)]
```

#### Shutdown — When `exit` is Called

When `exit` is called, the shell gracefully dumps the in-memory ledger back to
the `HISTFILE` before fully terminating the process.

```python
# Append mode ("a") preserves existing history from prior sessions
with open(histfile, "a") as f:
    for i in range(last_append_ptr[0], len(history_list)):
        f.write(history_list[i] + "\n")
```

We use **append mode** (`"a"`), not overwrite (`"w"`), because the file may contain
history from earlier sessions that we don't want to destroy.

---

## 9. How the Shell Finds & Runs External Programs

### Step 1: Searching the PATH

The `PATH` environment variable is a list of directories separated by `:` (on
Linux/Mac) or `;` (on Windows). When you type a command, the shell searches
through these directories **in order**, looking for an executable file with that name.

```python
def get_executable_path(cmd):
    path_env = os.environ.get("PATH", "")
    for directory in path_env.split(os.pathsep):
        full_path = os.path.join(directory, cmd)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    return None
```

**Line-by-line explanation:**

-   `os.environ.get("PATH", "")` — reads the PATH variable. Defaults to empty string.
-   `os.pathsep` — `:` on Linux/Mac, `;` on Windows. Cross-platform compatibility.
-   `os.path.join(directory, cmd)` — joins `"/usr/bin"` + `"ls"` → `"/usr/bin/ls"`.
-   `os.path.isfile(full_path)` — verifies it's a file, not a directory.
-   `os.access(full_path, os.X_OK)` — checks the **execute permission** bit.

### Step 2: Launching a Process

```python
# Simple: run and wait
subprocess.run(["ls", "-la"])

# Advanced: run without waiting (for pipelines)
process = subprocess.Popen(["ls", "-la"], stdout=subprocess.PIPE)
```

**What happens under the hood on Unix:**

1.  **`fork()`** — creates an exact copy of the shell process (the child)
2.  **`exec()`** — replaces the child's code with the target program (`ls`)
3.  The parent shell calls **`wait()`** to pause until the child finishes

| Feature | `subprocess.run()` | `subprocess.Popen()` |
|---|---|---|
| Blocking? | Yes — waits for completion | No — returns immediately |
| Use case | Simple single commands | Pipelines, background processes |
| Returns | `CompletedProcess` result | `Popen` process handle |

---

## 10. Complete Python API Reference

### `sys` Module — System-Level I/O

| API | Purpose |
|---|---|
| `sys.stdout` | The standard output stream (terminal) |
| `sys.stderr` | The standard error stream (terminal) |
| `sys.modules` | Dictionary of all imported modules |
| `sys.platform` | `"linux"`, `"darwin"` (Mac), or `"win32"` |

### `os` Module — Operating System Interface

| API | Purpose |
|---|---|
| `os.getcwd()` | Current working directory |
| `os.chdir(path)` | Change directory |
| `os.environ` | All environment variables |
| `os.environ.get("KEY")` | Safely read an env var (returns `None` if missing) |
| `os.path.join(a, b)` | Join path segments |
| `os.path.isfile(path)` | Is it a regular file? |
| `os.path.isdir(path)` | Is it a directory? |
| `os.path.exists(path)` | Does it exist? |
| `os.path.expanduser("~")` | Expand `~` to home directory |
| `os.path.commonprefix(list)` | Longest common prefix of strings |
| `os.access(path, os.X_OK)` | Check execute permission |
| `os.pathsep` | Path separator (`:` or `;`) |
| `os.listdir(dir)` | List directory contents |
| `os.pipe()` | Create pipe: `(read_fd, write_fd)` |
| `os.close(fd)` | Close a file descriptor |
| `os.write(fd, bytes)` | Write bytes to a file descriptor |

### `subprocess` Module — Process Management

| API | Purpose |
|---|---|
| `subprocess.run(args)` | Run command, wait for completion |
| `subprocess.run(args, input=b"...")` | Run with data piped to stdin |
| `subprocess.run(args, stdout=file)` | Redirect stdout to file |
| `subprocess.Popen(args)` | Start process without waiting |
| `subprocess.Popen(args, stdin=...)` | Set process stdin source |
| `subprocess.Popen(args, stdout=PIPE)` | Capture stdout for piping |
| `process.communicate()` | Wait and collect output |
| `process.wait()` | Wait for completion |

### `io` Module — In-Memory Streams

| API | Purpose |
|---|---|
| `io.StringIO()` | In-memory text stream |
| `buf.getvalue()` | Get everything written to the buffer |

### `readline` Module — Terminal Line Editing

| API | Purpose |
|---|---|
| `readline.set_completer(fn)` | Register tab-completion function |
| `readline.set_completer_delims(str)` | Set word-break characters |
| `readline.parse_and_bind("tab: complete")` | Bind Tab key |
| `readline.set_completion_display_matches_hook(fn)` | Custom match display |
| `readline.add_history(line)` | Add to interactive history |
| `readline.get_current_history_length()` | Number of history entries |
| `readline.get_history_item(n)` | Get nth entry (1-indexed!) |
| `readline.get_line_buffer()` | Current text in input line |

---

## 11. Stages Completed

| # | Stage | Difficulty | Status |
|---|---|---|---|
| 1 | Print a prompt | — | ✅ |
| 2 | Handle invalid commands | — | ✅ |
| 3 | Implement a REPL | — | ✅ |
| 4 | Implement `exit` | — | ✅ |
| 5 | Implement `echo` | — | ✅ |
| 6 | Implement `type` | — | ✅ |
| 7 | Locate executable files (PATH) | — | ✅ |
| 8 | Run a program | — | ✅ |
| 9 | The `pwd` builtin | — | ✅ |
| 10 | `cd` — Absolute paths | — | ✅ |
| 11 | `cd` — Relative paths | — | ✅ |
| 12 | `cd` — Home directory (`~`) | — | ✅ |
| 13 | Single quotes | Medium | ✅ |
| 14 | Double quotes | Medium | ✅ |
| 15 | Backslash outside quotes | Medium | ✅ |
| 16 | Backslash inside double quotes | Medium | ✅ |
| 17 | Stdout redirection (`>`, `1>`) | Medium | ✅ |
| 18 | Stderr redirection (`2>`) | Medium | ✅ |
| 19 | Append redirection (`>>`, `2>>`) | Medium | ✅ |
| 20 | Tab completion — Single match | Medium | ✅ |
| 21 | Tab completion — Multiple matches | Hard | ✅ |
| 22 | Tab completion — Display matches | Hard | ✅ |
| 23 | Pipelines — Two commands | Hard | ✅ |
| 24 | Pipelines — Builtins in pipelines | Hard | ✅ |
| 25 | Pipelines — N-stage pipelines | Hard | ✅ |
| 26 | History — Basic `history` | Medium | ✅ |
| 27 | History — `history <n>` | Medium | ✅ |
| 28 | History — Up-arrow navigation | Medium | ✅ |
| 29 | History — Down-arrow navigation | Medium | ✅ |
| 30 | History — Execute recalled command | Medium | ✅ |
| 31 | History — `history -r` (read) | Medium | ✅ |
| 32 | History — `history -w` (write) | Medium | ✅ |
| 33 | History — `history -a` (append) | Hard | ✅ |
| 34 | History — Load from HISTFILE | Easy | ✅ |
| 35 | History — Save to HISTFILE on exit | Easy | ✅ |
| 36 | History — Append to HISTFILE on exit | Medium | ✅ |

---

> *Built from scratch — **285 lines** of Python, zero external dependencies.*
> 
> *Final codebase:* [main.py](file:///c:/Users/navni/OneDrive/Desktop/codecrafters-shell-python/app/main.py)
