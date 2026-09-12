"""Injected-error variants (docs/spec/03-equivalence.md §3): deterministic single-site mutations of an RTL text
used for the negative direction of equivalence checks and for the DPV non-vacuity check (guardrail 2).

Mutations never touch the module header (port list), so the interface stays identical and V1 passes; whether a
mutation actually changes the function is decided by lock-step simulation, not assumed (a mutation inside dead
code is silently equivalent).
"""
import re

# (name, pattern, replacement) applied to ONE occurrence inside the module body; the order is the preference order
MUTATIONS = [
    ("eq_to_ne", re.compile(r"(?<![=!<>])==(?!=)"), "!="),
    ("ne_to_eq", re.compile(r"!==?"), "=="),
    ("lt_to_ge", re.compile(r"(?<![<=])<(?![<=])"), ">="),
    ("gt_to_le", re.compile(r"(?<![>=])>(?![>=])"), "<="),
    ("add_to_sub", re.compile(r"(?<![+])\+(?![+=])"), "-"),
    ("sub_to_add", re.compile(r"(?<![-])-(?![-=>])(?=\s*[\w(])"), "+"),
    ("and_to_or", re.compile(r"(?<![&])&(?![&=])"), "|"),
    ("or_to_and", re.compile(r"(?<![|])\|(?![|=])"), "&"),
    ("xor_to_or", re.compile(r"\^(?!~|=)"), "|"),
    ("const_plus_one", re.compile(r"(?<=')d(\d+)"), lambda m: "d" + str(int(m.group(1)) + 1)),
    ("shift_dir", re.compile(r"<<(?!<|=)"), ">>"),
]


def _body_start(text):
    """Index just after the module header's closing ');' (the port list), or 0 if it cannot be found."""
    m = re.search(r"^\s*module\b[^;]*;", text, re.M | re.S)
    return m.end() if m else 0


def _strip_comments(text):
    """Positions of comment characters, so that mutations skip them (returned as a mask of the same length)."""
    mask = bytearray(len(text))
    for m in re.finditer(r"//[^\n]*|/\*.*?\*/", text, re.S):
        for i in range(m.start(), m.end()):
            mask[i] = 1
    return mask


def generate_mutants(text, max_per_kind=1, max_total=8):
    """-> list of (name, mutated_text); each differs from `text` at exactly one site inside the module body."""
    start = _body_start(text)
    mask = _strip_comments(text)
    out = []
    for name, pat, repl in MUTATIONS:
        n = 0
        for m in pat.finditer(text, start):
            if mask[m.start()] or "endmodule" in text[m.start():m.start() + 9]:
                continue
            new = text[:m.start()] + (repl(m) if callable(repl) else repl) + text[m.end():]
            if new != text:
                out.append((f"{name}@{m.start()}", new))
                n += 1
            if n >= max_per_kind or len(out) >= max_total:
                break
        if len(out) >= max_total:
            break
    return out
