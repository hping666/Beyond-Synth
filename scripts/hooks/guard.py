#!/usr/bin/env python3
"""PreToolUse guard for Beyond-Synth (enforces CLAUDE.md hard rules 1, 3, 5, 10, 12 mechanically).

Reads the Claude Code hook JSON on stdin and DENIES the tool call when it would
  * delete, move, truncate or overwrite anything under results/       (rule 5: results are append-only)
  * read results/hidden/ by any means other than scripts/report_hidden.py
    (or scripts/hidden_worker.py, its only writer)                    (rule 3: hidden-configuration isolation)
  * modify anything under /hdd1/hping/eda/flow/                       (rule 1: never modify flow/)
  * overwrite eda-knowledge/05-traps.md wholesale (Edit-append only)  (rule 10: traps are append-only)
  * print, dump or copy secrets: the OPENAI_API_KEY env file, the deploy private key,
    or the whole environment                                          (rule 12: secrets never in logs/conversation)
  * exfiltrate files: scp/sftp/nc/socat, remote rsync, piping into ssh, curl/wget uploads, gists,
    cloud storage, ad-hoc HTTP servers / tunnels, git pushes to anything but the project remote

How Bash commands are analysed. Heredoc bodies are separated from the command line that owns them;
the rest is split into shell words (quotes respected) and grouped into simple commands at
; && || | & and unquoted newlines. Rules look at the head word of each simple command, its argument
words and its redirections. Consequences:
  * a protected path inside a commit message, an echo string, or a heredoc that is merely written
    to an ordinary file is DATA and passes;
  * the same path given to cat / sqlite3 / ls / python -c, or appearing in a python heredoc
    (executed code), is denied;
  * `bash -c` / `sh -c` / `eval` strings and `python -c` / `perl -e` / `node -e` code are analysed
    recursively; commands that cannot be parsed (unbalanced quotes) are denied and must be rewritten.
The guard inspects command text only: it cannot see inside files, so a script written to disk and then
executed is not inspected (that is what tests/test_isolation.py and code review are for).

Everything else is allowed. Denials are appended to .claude/guard-denied.log (secret-like tokens
redacted). Exit status is always 0; the decision travels as JSON on stdout
(hookSpecificOutput.permissionDecision). Tests: tests/test_guard_hook.py (bidirectional).
"""
import datetime
import json
import os
import re
import shlex
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.dirname(os.path.dirname(HERE))
HOME = os.path.expanduser("~")
FLOW_DIR = "/hdd1/hping/eda/flow"
RESULTS_DIR = os.path.join(PROJECT, "results")
HIDDEN_DIR = os.path.join(RESULTS_DIR, "hidden")
SECRET_DIR = os.path.join(HOME, ".config/beyond-synth")
DEPLOY_KEY = os.path.join(HOME, ".ssh/id_ed25519_beyond_synth")
TRAPS = os.path.join(HOME, "eda-knowledge/05-traps.md")
LOG = os.environ.get("BEYOND_SYNTH_GUARD_LOG") or os.path.join(PROJECT, ".claude", "guard-denied.log")  # tests point this at /dev/null

R1 = "/hdd1/hping/eda/flow/ must never be modified (CLAUDE.md rule 1)"
R3 = "results/hidden/ may only be read by scripts/report_hidden.py (CLAUDE.md rule 3)"
R5 = "results/ is append-only: nothing under results/ is deleted, moved or overwritten (CLAUDE.md rule 5)"
R10 = "eda-knowledge/05-traps.md is append-only (CLAUDE.md rule 10)"
R12_ENV = "dumping the environment or shell variables could print OPENAI_API_KEY (CLAUDE.md rule 12)"
R12_KEY = "OPENAI_API_KEY may only be used silently in requests to api.openai.com (CLAUDE.md rule 12)"
R12_FILE = "the secrets file ~/.config/beyond-synth/env.sh may only be sourced (CLAUDE.md rule 12)"
R12_SSH = "the deploy private key must not be read or copied (CLAUDE.md rule 12)"

HIDDEN_ALLOWED = re.compile(r"(^|/)scripts/(report_hidden|hidden_worker)\.py$")
OPERATOR_RE = re.compile(r"\|\||&&|\|&|;;|>>|<<|>&|<&|[();<>|&]")
OPERATORS = {";", "&&", "||", "|", "&", "|&", ";;"}
GROUPING = {"(", ")", "{", "}", "!"}
WRAPPERS = {"sudo", "nohup", "setsid", "time", "exec", "command", "builtin", "nice", "ionice", "timeout", "stdbuf"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
INTERPRETERS = {"python", "python3", "ipython", "perl", "ruby", "node", "tclsh", "dc_shell", "pt_shell", "vcf"}
DELETE_HEADS = {"rm", "shred", "rmdir", "unlink", "truncate", "mv"}
FLOW_WRITE_ANY_ARG = DELETE_HEADS | {"touch", "chmod", "chown", "patch", "tee"}
DEST_ARG_HEADS = {"cp", "rsync", "ln", "install"}
EXFIL_HEADS = {"scp", "sftp", "ftp", "lftp", "nc", "ncat", "netcat", "socat", "telnet", "mail", "sendmail", "mutt",
               "ngrok", "cloudflared", "localtunnel", "lt", "serveo", "bore"}
CLOUD_HEADS = {"aws", "gsutil", "az", "rclone", "b2", "s3cmd", "mc"}
DATA_FLAGS = ("-d", "--data", "--data-binary", "--data-raw", "--data-ascii", "--data-urlencode", "--json")
SAFE_PRINTENV = re.compile(r"^(PATH|HOME|USER|SHELL|PWD|SYNOPSYS|PT_HOME|EDA_\w+|LM_LICENSE_FILE|SNPSLMD_LICENSE_FILE|ORFS_\w+|CLAUDE_\w+)$")
SECRET_TOKEN = re.compile(r"sk-[A-Za-z0-9_\-]{8,}")
HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)(\w+)\1[^\n]*\n(.*?)\n[ \t]*\2[ \t]*(?=\n|$)", re.S)
ASSIGN = re.compile(r"^[A-Za-z_]\w*=")
REMOTE_SPEC = re.compile(r"^[\w.@\-]+:\S*$")
CURL_SHORT_UPLOAD = re.compile(r"^-[a-zA-Z]*[TF][a-zA-Z]*$")


# ----------------------------------------------------------------------------- path helpers
def _norm(path):
    p = os.path.expanduser(path)
    if not os.path.isabs(p):
        p = os.path.join(PROJECT, p)
    return os.path.realpath(p)


def _under(path, root):
    if not path:
        return False
    p, r = _norm(path), os.path.realpath(root)
    return p == r or p.startswith(r + os.sep)


def _pathish(tok):
    return bool(tok) and not tok.startswith("-") and not re.search(r"\s", tok)


def _hidden_ref(tok):
    return "results/hidden" in tok or "hidden.sqlite" in tok or (_pathish(tok) and _under(tok, HIDDEN_DIR))


def _secret_env_ref(tok):
    return ".config/beyond-synth" in tok or (_pathish(tok) and _under(tok, SECRET_DIR))


def _deploy_key_ref(tok):
    return "id_ed25519_beyond_synth" in tok and ".pub" not in tok


def _traps_ref(tok):
    return "05-traps.md" in tok or (_pathish(tok) and _norm(tok) == os.path.realpath(TRAPS))


# ----------------------------------------------------------------------------- shell parsing
def _split_heredocs(cmd):
    """Return (command text with heredoc bodies removed, [(owning command line, body), ...])."""
    bodies = []

    def repl(m):
        s = m.string
        line_start = s.rfind("\n", 0, m.start()) + 1          # the match begins at "<<"; the owning
        line_end = s.find("\n", m.start())                    # command starts at the beginning of that line
        bodies.append((s[line_start:line_end], m.group(3)))
        return m.group(0).split("\n", 1)[0] + "\n"

    return HEREDOC.sub(repl, cmd), bodies


def _unquoted_newlines_to_semicolons(text):
    out, quote, esc = [], None, False
    for ch in text:
        if esc:
            out.append(ch)
            esc = False
            continue
        if ch == "\\" and quote != "'":
            out.append(ch)
            esc = True
            continue
        if quote:
            if ch == quote:
                quote = None
            out.append(ch)
            continue
        if ch in ("'", '"'):
            quote = ch
            out.append(ch)
            continue
        out.append(" ; " if ch == "\n" else ch)
    return "".join(out)


def _tokens(text):
    lex = shlex.shlex(text, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    toks = []
    for t in lex:
        if t and re.fullmatch(r"[();<>|&]+", t):
            toks.extend(OPERATOR_RE.findall(t))
        else:
            toks.append(t)
    return toks


def _segments(tokens):
    """Group tokens into simple commands: list of (operator_before, [tokens])."""
    segs, cur, op = [], [], ""
    for t in tokens:
        if t in OPERATORS:
            if cur:
                segs.append((op, cur))
            cur, op = [], t
        elif t in GROUPING:
            continue
        else:
            cur.append(t)
    if cur:
        segs.append((op, cur))
    return segs


def _head(seg):
    """(head word, argument tokens) after stripping assignments and wrappers; `env X=1 cmd` is a wrapper."""
    i = 0
    while i < len(seg):
        t = seg[i]
        if ASSIGN.match(t):
            i += 1
            continue
        base = os.path.basename(t)
        if base in WRAPPERS:
            i += 1
            if base in ("timeout", "nice", "ionice", "stdbuf"):
                while i < len(seg) and (seg[i].startswith("-") or re.fullmatch(r"\d+[smhd]?", seg[i])):
                    i += 1
            continue
        if base == "env":
            j = i + 1
            while j < len(seg) and (ASSIGN.match(seg[j]) or seg[j].startswith("-")):
                j += 1
            if j < len(seg):
                i = j
                continue
            return "env", seg[i + 1:]
        return base, seg[i + 1:]
    return "", []


def _redirects(seg):
    """[(kind, target)] with kind in {overwrite, append, input}."""
    out = []
    for i, t in enumerate(seg):
        if i + 1 >= len(seg):
            break
        nxt = seg[i + 1]
        if t in (">", ">|", "&>"):
            out.append(("overwrite", nxt))
        elif t in (">>", "&>>"):
            out.append(("append", nxt))
        elif t == "<" or t == "<<<":
            out.append(("input", nxt))
        elif t == ">&" and not re.fullmatch(r"\d+|-", nxt):
            out.append(("overwrite", nxt))
    return out


# ----------------------------------------------------------------------------- executed code (python -c, heredocs)
def _check_code(code):
    if "results/hidden" in code or "hidden.sqlite" in code:
        return R3
    if FLOW_DIR in code and re.search(r"open\(|write_text|write_bytes|shutil\.|os\.remove|os\.unlink|os\.rename|os\.replace|rmtree|\.unlink\(|chmod", code):
        return R1
    if "results/" in code and re.search(r"rmtree|os\.remove|os\.unlink|os\.rename|os\.replace|\.unlink\(|shutil\.move", code):
        return R5
    if "05-traps" in code and re.search(r"['\"]w['\"]|write_text|os\.remove|\.unlink\(", code):
        return R10
    if "OPENAI_API_KEY" in code and re.search(r"\bprint\b|sys\.stdout|logging|\.write\(", code):
        return R12_KEY
    if ".config/beyond-synth" in code:
        return R12_FILE
    if "id_ed25519_beyond_synth" in code and ".pub" not in code:
        return R12_SSH
    if re.search(r"http\.server|SimpleHTTPServer|smtplib|paramiko|ftplib|requests\.(post|put|patch)|urlopen\([^)]*data=", code):
        return "network upload or serving from ad-hoc code is blocked (exfiltration)"
    return None


# ----------------------------------------------------------------------------- one simple command
def _check_segment(op_before, seg, prev_tokens, depth):
    head, args = _head(seg)
    if not head:
        return None
    redirects = _redirects(seg)
    pathargs = [a for a in args if _pathish(a)]

    # recursion into strings that are executed
    if head in SHELLS and "-c" in args and args.index("-c") + 1 < len(args):
        r = check_bash(args[args.index("-c") + 1], depth + 1)
        if r:
            return r
    if head == "eval":
        r = check_bash(" ".join(args), depth + 1)
        if r:
            return r
    if head in INTERPRETERS:
        for flag in ("-c", "-e"):
            if flag in args and args.index(flag) + 1 < len(args):
                r = _check_code(args[args.index(flag) + 1])
                if r:
                    return r
        if "-m" in args and args.index("-m") + 1 < len(args) and args[args.index("-m") + 1] in ("http.server", "SimpleHTTPServer"):
            return "serving files over HTTP is blocked (exfiltration)"
    if head == "xargs":
        sub_head, _ = _head([a for a in args if not a.startswith("-")])
        if sub_head in DELETE_HEADS and any(_pathish(t) and _under(t, RESULTS_DIR) for t in prev_tokens):
            return R5
        if sub_head in FLOW_WRITE_ANY_ARG and any(_pathish(t) and _under(t, FLOW_DIR) for t in prev_tokens):
            return R1

    # ---- rule 5: results/ append-only ----
    if head in DELETE_HEADS and any(_under(a, RESULTS_DIR) for a in pathargs):
        return R5
    if head == "find" and any(_under(a, RESULTS_DIR) for a in pathargs) and ("-delete" in args or ("-exec" in args and "rm" in args)):
        return R5
    if head == "git" and args[:1] == ["clean"] and any(re.match(r"^-\w*[xX]", a) for a in args[1:]):
        return "git clean -x would delete the ignored results/ tree (CLAUDE.md rule 5)"
    for kind, target in redirects:
        if kind == "overwrite" and _pathish(target) and _under(target, RESULTS_DIR):
            return R5
        if kind == "append" and _hidden_ref(target):
            return R3
    if head in ("tee", "cp", "install") and pathargs:
        dest = pathargs[-1]
        if head == "tee" and "-a" not in args and "--append" not in args:
            dests = pathargs
        elif head == "tee":
            dests = []
        else:
            dests = [dest]
        for d in dests:
            if _under(d, RESULTS_DIR) and os.path.isfile(_norm(d)):
                return R5

    # ---- rule 3: hidden results ----
    if head == "git":
        if args[:1] == ["add"] and any(a in ("-f", "--force") for a in args) and any(_hidden_ref(a) for a in args):
            return "results/hidden/ must never be committed (CLAUDE.md rule 3)"
    elif head not in ("echo", "printf", "mkdir"):
        if any(_hidden_ref(t) for t in seg) and not any(HIDDEN_ALLOWED.search(a) for a in pathargs):
            return R3

    # ---- rule 1: flow/ read-only ----
    if head in FLOW_WRITE_ANY_ARG and any(_under(a, FLOW_DIR) for a in pathargs):
        return R1
    if head == "sed" and any(a.startswith("-i") or a == "--in-place" for a in args) and any(_under(a, FLOW_DIR) for a in pathargs):
        return R1
    if head in DEST_ARG_HEADS and pathargs and _under(pathargs[-1], FLOW_DIR):
        return R1
    if any(kind != "input" and _pathish(t) and _under(t, FLOW_DIR) for kind, t in redirects):
        return R1

    # ---- rule 10: 05-traps.md append-only ----
    if head in ("sed",) and any(a.startswith("-i") or a == "--in-place" for a in args) and any(_traps_ref(a) for a in pathargs):
        return R10
    if head in DELETE_HEADS and any(_traps_ref(a) for a in pathargs):
        return R10
    if head in DEST_ARG_HEADS and pathargs and _traps_ref(pathargs[-1]):
        return R10
    if head == "tee" and "-a" not in args and "--append" not in args and any(_traps_ref(a) for a in pathargs):
        return R10
    if any(kind == "overwrite" and _traps_ref(t) for kind, t in redirects):
        return R10

    # ---- rule 12: secrets ----
    if head == "printenv" and (not args or any(not SAFE_PRINTENV.match(a) for a in args)):
        return R12_ENV
    if head == "env":
        return R12_ENV
    if head in ("set", "declare", "typeset", "export") and (not args or "-p" in args):
        return R12_ENV
    if any("$OPENAI_API_KEY" in t or "${OPENAI_API_KEY" in t for t in seg):
        ok = head in ("[", "test", ":") or (
            head == "curl" and any("api.openai.com" in t for t in seg)
            and not any(t in ("-v", "--verbose") or t.startswith("--trace") for t in args))
        if not ok:
            return R12_KEY
    if head not in ("git", "echo", "printf"):
        if any(_secret_env_ref(t) for t in seg) and head not in ("source", ".", "[", "test", "ls", "stat", "chmod", "mkdir"):
            return R12_FILE
        if any(_deploy_key_ref(t) for t in seg) and head not in ("ssh", "ssh-add", "ssh-keygen", "ls", "stat", "chmod", "test", "["):
            return R12_SSH
    for kind, target in redirects:
        if kind != "input" and (_secret_env_ref(target) or _deploy_key_ref(target)):
            return "secret files are managed by the user only (CLAUDE.md rule 12)"

    # ---- exfiltration ----
    if head in EXFIL_HEADS:
        return f"'{head}' is an exfiltration channel and is blocked"
    if head == "ssh" and (op_before in ("|", "|&") or any(kind == "input" for kind, _ in redirects)):
        return "piping local data into ssh is blocked (exfiltration)"
    if head == "rsync" and (any(a in ("-e", "--rsh") or a.startswith("--rsh=") for a in args) or any(REMOTE_SPEC.match(a) for a in pathargs)):
        return "remote rsync is blocked (exfiltration)"
    if head == "curl":
        if any(CURL_SHORT_UPLOAD.match(a) or a in ("--upload-file", "--form", "--form-string") for a in args):
            return "curl file upload is blocked (exfiltration)"
        for i, a in enumerate(args):
            if a in DATA_FLAGS and i + 1 < len(args) and args[i + 1].startswith("@"):
                return "curl file upload is blocked (exfiltration)"
            if any(a.startswith(f + "=@") for f in DATA_FLAGS):
                return "curl file upload is blocked (exfiltration)"
    if head == "wget" and any(a.startswith(("--post-file", "--body-file")) for a in args):
        return "wget file upload is blocked (exfiltration)"
    if head == "gh":
        if args[:2] in (["gist", "create"], ["release", "upload"]):
            return "gh upload is blocked (exfiltration)"
        if args[:1] == ["api"] and (any(a == "--input" for a in args) or any(a.startswith("@") or "=@" in a for a in args)):
            return "gh api upload is blocked (exfiltration)"
    if head in CLOUD_HEADS and any(a in ("s3", "storage", "cp", "copy", "sync", "mv", "upload", "put", "blob", "rsync") for a in args):
        return "cloud storage transfer is blocked (exfiltration)"
    if head == "git" and args:
        if args[0] == "push" and any(re.search(r"(https?://|git@|ssh://)", a) for a in args) and not any("hping666/Beyond-Synth" in a for a in args):
            return "git push to a foreign remote is blocked (exfiltration)"
        if args[0] == "remote" and args[1:2] and args[1] in ("add", "set-url") and not any("hping666/Beyond-Synth" in a for a in args):
            return "only the project remote hping666/Beyond-Synth may be configured (exfiltration guard)"
    return None


def check_bash(cmd, depth=0):
    if depth > 3 or not cmd.strip():
        return None
    text, heredocs = _split_heredocs(cmd)
    for first_line, body in heredocs:
        try:
            head, _ = _head(_tokens(first_line))
        except ValueError:
            head = ""
        if head in INTERPRETERS:
            r = _check_code(body)
            if r:
                return r
        elif head in SHELLS or head == "":
            r = check_bash(body, depth + 1)
            if r:
                return r
    try:
        tokens = _tokens(_unquoted_newlines_to_semicolons(text))
    except ValueError:
        return "guard.py could not parse this command (unbalanced quotes); rewrite it more simply"
    prev = []
    for op_before, seg in _segments(tokens):
        r = _check_segment(op_before, seg, prev, depth)
        if r:
            return r
        prev.extend(seg)
    return None


# ----------------------------------------------------------------------------- file tools
def check_path_tool(tool, ti):
    path = ti.get("file_path") or ti.get("path") or ti.get("notebook_path") or ""
    if not path:
        return None
    if tool in ("Read", "Grep", "Glob"):
        if _under(path, HIDDEN_DIR):
            return R3
        if _under(path, SECRET_DIR) or _norm(path) == os.path.realpath(DEPLOY_KEY):
            return "secret files must not be read (CLAUDE.md rule 12)"
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        if _under(path, FLOW_DIR):
            return R1
        if _under(path, HIDDEN_DIR):
            return "results/hidden/ is written only by scripts/hidden_worker.py (CLAUDE.md rule 3)"
        if tool == "Write" and _under(path, RESULTS_DIR) and os.path.exists(_norm(path)):
            return R5
        if _under(path, SECRET_DIR) or _norm(path) == os.path.realpath(DEPLOY_KEY):
            return "secret files are managed by the user only (CLAUDE.md rule 12)"
        if _norm(path) == os.path.realpath(TRAPS) and tool != "Edit":
            return "eda-knowledge/05-traps.md is append-only: use Edit to append, never Write (CLAUDE.md rule 10)"
    return None


# ----------------------------------------------------------------------------- entry point
def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # unreadable input: do not block
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    reason = None
    if tool == "Bash":
        reason = check_bash(str(ti.get("command", "")))
    elif tool in ("Read", "Grep", "Glob", "Edit", "Write", "MultiEdit", "NotebookEdit"):
        reason = check_path_tool(tool, ti)
    if reason:
        try:
            os.makedirs(os.path.dirname(LOG), exist_ok=True)
            what = str(ti.get("command") or ti.get("file_path") or ti.get("path") or "")[:200]
            with open(LOG, "a") as f:
                f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {tool} DENY: {reason} :: "
                        f"{SECRET_TOKEN.sub('sk-<redacted>', what)!r}\n")
        except Exception:
            pass
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": "guard.py: " + reason}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
