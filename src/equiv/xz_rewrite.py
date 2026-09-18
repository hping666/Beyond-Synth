"""DECISION 2026-09-18 (f) item 1 — the harness_version 2 source rewrite for V3: x / z literals in value positions only — the
right-hand sides of continuous and procedural assignments and reset values — become 0 (each x or z digit), located with the
Pyverilog AST, never by a regular expression over the text. Case items, casez / casex patterns, comparisons (== != === !==,
wildcard ==? / !=?) and any literal containing '?' are never rewritten; a line where the same literal text occurs both in a
value position and elsewhere is left alone and reported (ambiguous). Only the designs listed in config
equiv.harness_v2_rewrite_designs are rewritten; every other design's V3 copy is byte-identical to its source.

    plan = analyze(files, incdirs=[...], rst_port="resetn")   # -> {"targets": [...], "counts": {context: n}, "errors": [...]}
    paths, report = rewrite_copies(files, out_dir, incdirs=[...], rst_port=...)
"""
import re
import shutil
from pathlib import Path

VALUE_CONTEXTS = ("continuous", "procedural", "reset_value")
SKIP_CONTEXTS = ("pattern", "comparison", "question", "other")
_XZ = re.compile(r"[xXzZ]")


def _has_xz(value):
    return bool(_XZ.search(value.split("'", 1)[1])) if "'" in value else False


def _has_q(value):
    return "?" in value


def _parse(files, incdirs=()):
    from pyverilog.vparser.parser import parse
    ast, _ = parse([str(f) for f in files], preprocess_include=[str(d) for d in (incdirs or [])], preprocess_define=[])
    return ast


def _walk(node, ancestors, out):
    """Collect (IntConst node, ancestors) pairs."""
    from pyverilog.vparser import ast as A
    if isinstance(node, A.IntConst):
        out.append((node, list(ancestors)))
        return
    ancestors.append(node)
    for ch in node.children():
        _walk(ch, ancestors, out)
    ancestors.pop()


def _classify(node, ancestors, rst_port):
    """The context of a literal: continuous / procedural / reset_value (value positions), or pattern / comparison / other."""
    from pyverilog.vparser import ast as A
    comparison = (A.Eq, A.NotEq, A.Eql, A.NotEql, A.LessThan, A.GreaterThan, A.LessEq, A.GreaterEq)
    for i in range(len(ancestors) - 1, -1, -1):
        anc = ancestors[i]
        child = ancestors[i + 1] if i + 1 < len(ancestors) else node
        if isinstance(anc, (A.Case,)):   # a case item: the literal sits in the item's cond list (patterns); the switch expression is `comp`
            return "pattern"
        if isinstance(anc, (A.CaseStatement, A.CasezStatement, A.CasexStatement)) and child is anc.comp:
            return "other"
        if isinstance(anc, comparison):
            return "comparison"
        if isinstance(anc, A.Assign):
            return "continuous" if child is anc.right else "other"
        if isinstance(anc, (A.NonblockingSubstitution, A.BlockingSubstitution)):
            if child is not anc.right:
                return "other"
            # a reset value: the assignment sits in the TRUE branch of the nearest if whose condition names the reset port
            for j in range(i - 1, -1, -1):
                a2 = ancestors[j]
                below = ancestors[j + 1] if j + 1 < len(ancestors) else anc
                if isinstance(a2, A.IfStatement):
                    if rst_port and rst_port in _names(a2.cond):
                        return "reset_value" if below is a2.true_statement else "procedural"
                    continue   # an inner if (soft reset, a counter test): keep looking for the reset if
                if isinstance(a2, A.Always):
                    break
            return "procedural"
        if isinstance(anc, (A.Parameter, A.Localparam, A.Ioport, A.Decl, A.Width, A.Length, A.Repeat, A.Partselect, A.Pointer)):
            return "other"
    return "other"


def _names(expr):
    from pyverilog.vparser import ast as A
    out = set()
    def rec(n):
        if isinstance(n, A.Identifier):
            out.add(n.name)
        for ch in n.children():
            rec(ch)
    rec(expr)
    return out


def analyze(files, incdirs=(), rst_port=None):
    """-> {"targets": [(file, lineno, literal)], "counts": {context: n}, "skipped": {context: n}, "errors": [...]} for the x / z / ?
    literals of `files` (each file parsed on its own, so that line numbers are the file's)."""
    from pyverilog.vparser import ast as A  # noqa: F401
    counts = {c: 0 for c in VALUE_CONTEXTS}
    skipped = {c: 0 for c in SKIP_CONTEXTS}
    targets, errors = [], []
    for f in files:
        try:
            ast = _parse([f], incdirs)
        except Exception as e:   # a file Pyverilog cannot parse is left unrewritten and reported
            errors.append({"file": str(f), "error": f"{type(e).__name__}: {str(e)[:160]}"})
            continue
        found = []
        _walk(ast, [], found)
        for node, anc in found:
            v = str(node.value)
            if not (_has_xz(v) or _has_q(v)):
                continue
            if _has_q(v):
                skipped["question"] += 1
                continue
            ctx = _classify(node, anc, rst_port)
            if ctx in VALUE_CONTEXTS:
                counts[ctx] += 1
                targets.append((str(f), int(node.lineno), v))
            else:
                skipped[ctx] += 1
    return {"targets": targets, "counts": counts, "skipped": skipped, "errors": errors}


def _literal_pattern(lit):
    """A regex matching the literal as written (whitespace allowed after the quote and the base)."""
    size, rest = lit.split("'", 1)
    base, digits = rest[0], rest[1:]
    sign = ""
    if base in "sS":
        sign, base, digits = base, rest[1], rest[2:]
    return re.compile(r"(?<![\w?])" + re.escape(size) + r"\s*'\s*" + re.escape(sign) + re.escape(base) + r"\s*" + re.escape(digits) + r"(?![\w?])")


def rewrite_copies(files, out_dir, incdirs=(), rst_port=None):
    """Copies of `files` under `out_dir` with the value-position x / z literals rewritten to 0; -> (paths, report). A file whose
    rewrite would be ambiguous on some line (the same literal text also in a non-value position) keeps that line unchanged and the
    line is reported under `ambiguous`."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = analyze(files, incdirs, rst_port)
    by_file = {}
    for f, ln, lit in plan["targets"]:
        by_file.setdefault(f, {}).setdefault(ln, []).append(lit)
    # every x / z literal anywhere, per (file, line), to detect the ambiguous lines
    all_lits = {}
    for f in files:
        try:
            ast = _parse([f], incdirs)
        except Exception:
            continue
        found = []
        _walk(ast, [], found)
        for node, anc in found:
            v = str(node.value)
            if _has_xz(v) or _has_q(v):
                all_lits.setdefault((str(f), int(node.lineno)), []).append(v)
    paths, rewritten, ambiguous = [], {}, []
    for f in files:
        src = Path(f)
        dst = out_dir / src.name
        if dst.exists() and str(dst.resolve()) != str(src.resolve()):
            dst = out_dir / f"{src.stem}_{len(paths)}{src.suffix}"
        lines = src.read_text(errors="replace").splitlines(keepends=True)
        n = 0
        for ln, lits in (by_file.get(str(f)) or {}).items():
            if ln - 1 >= len(lines):
                continue
            line = lines[ln - 1]
            others = [v for v in all_lits.get((str(f), ln), []) if v not in lits]
            if any(_literal_pattern(o).search(line) and o in lits for o in others) or len(all_lits.get((str(f), ln), [])) != len(lits) + len(others) or any(v in others for v in lits):
                ambiguous.append({"file": src.name, "line": ln}); continue
            for lit in lits:
                pat = _literal_pattern(lit)
                m = list(pat.finditer(line))
                if len(m) != lits.count(lit):   # the literal must occur on the line exactly as often as the AST places it in value positions
                    ambiguous.append({"file": src.name, "line": ln, "literal": lit}); break
                new_lit = lit.split("'", 1)[0] + "'" + _XZ.sub("0", lit.split("'", 1)[1])
                line = pat.sub(lambda mm: new_lit, line)
                n += len(m)
            else:
                lines[ln - 1] = line
        dst.write_text("".join(lines))
        paths.append(str(dst))
        rewritten[src.name] = n
    report = {"counts": plan["counts"], "skipped": plan["skipped"], "rewritten": rewritten, "ambiguous": ambiguous, "errors": plan["errors"]}
    return paths, report


def identical_copies(files, out_dir):
    """Byte-identical copies (the designs outside the rewrite list)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for f in files:
        src = Path(f)
        dst = out_dir / src.name
        if dst.exists() and str(dst.resolve()) != str(src.resolve()):
            dst = out_dir / f"{src.stem}_{len(paths)}{src.suffix}"
        shutil.copyfile(src, dst)
        paths.append(str(dst))
    return paths
