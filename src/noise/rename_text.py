"""Text-level P1 renamer (DECISIONS 2026-09-14, G1.2): for designs whose Pyverilog re-print is unusable (the printer
breaks the design or its round trip is not proven), rename internal identifiers directly in the original text with a
regular expression. The identifier table (declared nets / registers / integers / parameters / genvars of every module,
minus the ports of every module, module and instance names, function and task names) comes from the parser-free text
scanner src/noise/textscan.py since REQUEST 2026-09-20 (e) item 3 (harness note: the renamer no longer depends on the
Pyverilog step, which fails on 7 of the 13 pooled-floor designs); the Pyverilog-based table (identifier_table(ast)) is kept
for cross-checks and older callers. Named port connections `.name(`, hierarchical references, macro references and escaped
identifiers are never touched; comments and strings are renamed like code (harmless for synthesis and equivalence).
ptype `P1_text`."""
import re

from src.noise import perturb as P
from src.noise import textscan as TS
from src.noise import vast as V

PTYPE = "P1_text"


def identifier_table(ast):
    """Renamable identifiers of a design: declared internal names of every module minus every port name, module name,
    instance name and function / task name of any module (a name shared with a port elsewhere is left alone)."""
    A = V.A
    declared, protected = {}, set()
    for m in V.modules(ast):
        protected.add(m.name)
        protected |= V.port_names(m)
        for n in V.walk(m):
            if isinstance(n, A.Instance):
                protected.add(n.name)
                protected.add(n.module)
            if isinstance(n, (A.Function, A.Task)):
                protected.add(n.name)
            if isinstance(n, A.PortArg) and n.portname:
                protected.add(n.portname)
        for name, kind in V.declared_names(m).items():
            declared.setdefault(name, kind)
    return {n: k for n, k in declared.items() if n not in protected and n not in V.KEYWORDS and not n.startswith("\\")}  # escaped identifiers stay


def rename_map(names, taken, seed, k):
    """Deterministic new names (NATO word + index, like P1) that collide with nothing in the design."""
    r = V.rng(seed, PTYPE, k)
    words = P.WORDS[:]
    r.shuffle(words)
    out, used = {}, set(taken) | set(names)
    for i, name in enumerate(sorted(names)):
        new = f"{words[i % len(words)]}_{i}"
        while new in used:
            new = f"{new}x"
        used.add(new)
        out[name] = new
    return out


def apply(text, mapping):
    """Whole-word replacement outside named port connections (`.name`), hierarchical tails and escaped identifiers."""
    if not mapping:
        return text
    pat = re.compile(r"(?<![\w$.\\`])(" + "|".join(re.escape(n) for n in sorted(mapping, key=len, reverse=True)) + r")(?![\w$])")
    return pat.sub(lambda m: mapping[m.group(1)], text)


def text_variants(design_files, ast, seed, n, start=0):
    """-> [(k, mapping, {path: new_text})] for k in range(start, start + n); the mapping is shared by all files of the design.
    ast None (the default path since REQUEST 2026-09-20 (e) 3): the identifier table and the taken names come from the text
    scanner; an AST gives the Pyverilog-based table of the earlier designs."""
    texts = {str(f): open(f, errors="replace").read() for f in design_files}
    if ast is None:
        table = TS.identifier_table(list(texts.values()))
        taken = TS.all_identifiers(list(texts.values())) | V.KEYWORDS
    else:
        table = identifier_table(ast)
        taken = V.all_identifiers(ast) | V.KEYWORDS
    if not table:
        raise P.NotApplicable("no renamable internal identifier")
    out = []
    for k in range(start, start + n):
        mapping = rename_map(list(table), taken, seed, k)
        out.append((k, mapping, {f: apply(t, mapping) for f, t in texts.items()}))
    return out
