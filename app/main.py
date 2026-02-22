import sys
import os
import subprocess
import io

try:
    import readline
except ImportError:
    pass

def parse_command(command):
    """Parse command line respecting single quotes, double quotes, and backslashes."""
    parts = []
    current_part = ""
    quote_char = None
    i = 0
    while i < len(command):
        char = command[i]
        if quote_char is None:
            if char == "\\":
                i += 1
                if i < len(command): current_part += command[i]
            elif char in ("'", '"'): quote_char = char
            elif char == " ":
                if current_part:
                    parts.append(current_part)
                    current_part = ""
            else: current_part += char
        elif char == quote_char: quote_char = None
        elif char == "\\" and quote_char == '"':
            if i + 1 < len(command) and command[i+1] in ('"', '\\', '$', '`'):
                current_part += command[i+1]
                i += 1
            else: current_part += char
        else: current_part += char
        i += 1
    if current_part: parts.append(current_part)
    return parts

def get_executable_path(cmd):
    path_env = os.environ.get("PATH", "")
    for dir in path_env.split(os.pathsep):
        full_path = os.path.join(dir, cmd)
        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
            return full_path
    return None

def run_builtin(parts, out, err, builtins_list, history_list=None, last_append_ptr=None):
    """Executes a builtin command and writes output/error to specified streams."""
    cmd = parts[0]
    if cmd == "echo":
        print(" ".join(parts[1:]), file=out)
    elif cmd == "pwd":
        print(os.getcwd(), file=out)
    elif cmd == "cd":
        if len(parts) > 1:
            path = parts[1]
            if path == "~": path = os.path.expanduser("~")
            try: os.chdir(path)
            except Exception: print(f"cd: {path}: No such file or directory", file=err)
    elif cmd == "type":
        if len(parts) > 1:
            target = parts[1]
            if target in builtins_list:
                print(f"{target} is a shell builtin", file=out)
            else:
                full_path = get_executable_path(target)
                if full_path: print(f"{target} is {full_path}", file=out)
                else: print(f"{target}: not found", file=out)
    elif cmd == "history":
        if history_list is not None:
            if len(parts) >= 3 and parts[1] == "-r":
                path = parts[2]
                try:
                    if os.path.exists(path):
                        with open(path, "r") as f:
                            for line in f:
                                h_line = line.rstrip("\r\n")
                                if h_line:
                                    history_list.append(h_line)
                                    if 'readline' in sys.modules:
                                        readline.add_history(h_line)
                except Exception: pass
            elif len(parts) >= 3 and parts[1] == "-w":
                path = parts[2]
                try:
                    with open(path, "w") as f:
                        for h_item in history_list:
                            f.write(h_item + "\n")
                except Exception: pass
            elif len(parts) >= 3 and parts[1] == "-a":
                path = parts[2]
                try:
                    start_idx = last_append_ptr[0] if last_append_ptr else 0
                    with open(path, "a") as f:
                        for i in range(start_idx, len(history_list)):
                            f.write(history_list[i] + "\n")
                    if last_append_ptr is not None:
                        last_append_ptr[0] = len(history_list)
                except Exception: pass
            else:
                limit = len(history_list)
                if len(parts) > 1:
                    try: limit = int(parts[1])
                    except ValueError: pass
                start_idx = max(0, len(history_list) - limit)
                for i in range(start_idx, len(history_list)):
                    print(f"{i+1:5}  {history_list[i]}", file=out)
    return True

def main():
    builtins_list = ["echo", "exit", "pwd", "cd", "type", "history"]
    history_list = []
    
    # Load history from HISTFILE on startup
    histfile = os.environ.get("HISTFILE")
    if histfile and os.path.exists(histfile):
        try:
            with open(histfile, "r") as f:
                for line in f:
                    h_line = line.rstrip("\r\n")
                    if h_line:
                        history_list.append(h_line)
                        if 'readline' in sys.modules:
                            readline.add_history(h_line)
        except Exception:
            pass

    last_append_ptr = [len(history_list)] # Pointer to the first un-appended command for 'history -a'

    def completer(text, state):
        matches = [b for b in builtins_list if b.startswith(text)]
        path_env = os.environ.get("PATH", "")
        for directory in path_env.split(os.pathsep):
            if not os.path.isdir(directory): continue
            try:
                for filename in os.listdir(directory):
                    full_path = os.path.join(directory, filename)
                    if (filename.startswith(text) and os.path.isfile(full_path) and os.access(full_path, os.X_OK)):
                        matches.append(filename)
            except Exception: continue
        matches = sorted(list(set(matches)))
        if not matches: return None
        if len(matches) == 1:
            if state == 0: return matches[0] + " "
            return None
        common = os.path.commonprefix(matches)
        if len(common) > len(text):
            if state == 0: return common
            return None
        if state < len(matches): return matches[state]
        return None

    def display_matches(substitution, matches, longest_match_len):
        valid_matches = sorted(list(set([m for m in matches if m])))
        sys.stdout.write("\n" + "  ".join(valid_matches) + "\n$ " + readline.get_line_buffer())
        sys.stdout.flush()

    if 'readline' in sys.modules:
        readline.set_completer(completer)
        readline.set_completion_display_matches_hook(display_matches)
        readline.set_completer_delims('')
        if sys.platform != 'darwin': readline.parse_and_bind("tab: complete")

    while True:
        try:
            command_raw = input("$ ")
        except EOFError:
            break
        
        # Capture raw command for history list
        history_list.append(command_raw)
        
        if 'readline' in sys.modules and command_raw.strip():
            hist_len = readline.get_current_history_length()
            if hist_len == 0 or readline.get_history_item(hist_len) != command_raw:
                readline.add_history(command_raw)

        initial_parts = parse_command(command_raw)
        if not initial_parts: continue
        
        stdout_file_path, stderr_file_path = None, None
        stdout_mode, stderr_mode = "w", "w"
        parts = []
        i = 0
        while i < len(initial_parts):
            p = initial_parts[i]
            if p in (">", "1>"): stdout_file_path, stdout_mode, i = initial_parts[i+1], "w", i + 2
            elif p in (">>", "1>>"): stdout_file_path, stdout_mode, i = initial_parts[i+1], "a", i + 2
            elif p == "2>": stderr_file_path, stderr_mode, i = initial_parts[i+1], "w", i + 2
            elif p == "2>>": stderr_file_path, stderr_mode, i = initial_parts[i+1], "a", i + 2
            else: parts.append(p); i += 1

        if not parts: continue

        # --- PIPELINE HANDLING (N stages) ---
        if "|" in parts:
            stages = []
            tmp = []
            for p in parts:
                if p == "|": stages.append(tmp); tmp = []
                else: tmp.append(p)
            stages.append(tmp)

            out_f = open(stdout_file_path, stdout_mode) if stdout_file_path else None
            err_f = open(stderr_file_path, stderr_mode) if stderr_file_path else None
            
            try:
                curr_in = None
                procs = []
                for i, stage in enumerate(stages):
                    is_last = (i == len(stages) - 1)
                    if stage[0] in builtins_list:
                        buf = io.StringIO()
                        run_builtin(stage, buf, err_f or sys.stderr, builtins_list, history_list, last_append_ptr)
                        data = buf.getvalue().encode()
                        if curr_in is not None:
                            if isinstance(curr_in, int): os.close(curr_in)
                            else: curr_in.close()
                            curr_in = None
                        if is_last:
                            dest = out_f if out_f else sys.stdout
                            dest.write(data.decode())
                            dest.flush()
                        else:
                            r, w = os.pipe()
                            os.write(w, data)
                            os.close(w)
                            curr_in = r
                    else:
                        stdout = subprocess.PIPE if not is_last else out_f
                        p = subprocess.Popen(stage, stdin=curr_in, stdout=stdout, stderr=err_f)
                        procs.append(p)
                        if curr_in is not None:
                            if isinstance(curr_in, int): os.close(curr_in)
                            else: curr_in.close()
                        if not is_last: curr_in = p.stdout
                        else: curr_in = None
                for p in procs: p.wait()
            except Exception: pass
            finally:
                if out_f: out_f.close()
                if err_f: err_f.close()
            continue

        # --- SINGLE COMMAND HANDLING ---
        stdout_file = open(stdout_file_path, stdout_mode) if stdout_file_path else None
        stderr_file = open(stderr_file_path, stderr_mode) if stderr_file_path else None
        try:
            out, err = (stdout_file or sys.stdout), (stderr_file or sys.stderr)
            if parts[0] == "exit":
                # Append session history to HISTFILE on exit
                histfile = os.environ.get("HISTFILE")
                if histfile:
                    try:
                        start_idx = last_append_ptr[0] if last_append_ptr else 0
                        with open(histfile, "a") as f:
                            for i in range(start_idx, len(history_list)):
                                f.write(history_list[i] + "\n")
                    except Exception:
                        pass
                break
            if parts[0] in builtins_list:
                run_builtin(parts, out, err, builtins_list, history_list, last_append_ptr)
            elif get_executable_path(parts[0]):
                subprocess.run(parts, stdout=stdout_file, stderr=stderr_file)
            else:
                print(f"{parts[0]}: command not found", file=err)
        finally:
            if stdout_file: stdout_file.close()
            if stderr_file: stderr_file.close()

    # Also append on EOF exit (loop break)
    histfile = os.environ.get("HISTFILE")
    if histfile:
        try:
            start_idx = last_append_ptr[0] if last_append_ptr else 0
            with open(histfile, "a") as f:
                for i in range(start_idx, len(history_list)):
                    f.write(history_list[i] + "\n")
        except Exception:
            pass

if __name__ == "__main__":
    main()