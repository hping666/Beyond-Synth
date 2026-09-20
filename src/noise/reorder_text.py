"""Text-level P2 statement reorder (REQUEST 2026-09-20 (e) item 3, PLAN 6.9): without Pyverilog, permute the order of
consecutive module-level items of the same kind — continuous assignments (`assign ...;`) and always blocks with a
`begin ... end` body — inside each module of the design text. Module items are concurrent, so their order carries no
semantics; declarations, instances, parameters, generate blocks and every other item keep their place and act as barriers
between runs. A module the scanner cannot segment with certainty (src/noise/textscan.Refuse) is left untouched and named in
the details. ptype `P2_text`."""
import re

from src.noise import perturb as P
from src.noise import textscan as TS
from src.noise import vast as V

PTYPE = "P2_text"
KINDS = ("assign", "always")


def runs_of(items):
    """Maximal runs (length >= 2) of consecutive items of the same reorderable kind."""
    runs, run = [], []
    for it in items:
        if run and it[0] == run[-1][0] and it[0] in KINDS:
            run.append(it)
        else:
            if len(run) >= 2:
                runs.append(run)
            run = [it] if it[0] in KINDS else []
    if len(run) >= 2:
        runs.append(run)
    return runs


def _splice(text, edits):
    """edits: [(spans [(s, e)...], perm)] on `text`, non-overlapping; applied from the end so that offsets stay valid; the text
    between the spans of a run (whitespace, comments) stays in its slot."""
    out = text
    for spans, perm in sorted(edits, key=lambda x: -x[0][0][0]):
        pieces = [text[s:e] for s, e in spans]
        gaps = [text[spans[i][1]:spans[i + 1][0]] for i in range(len(spans) - 1)]
        rebuilt = "".join(pieces[perm[i]] + (gaps[i] if i < len(gaps) else "") for i in range(len(spans)))
        out = out[:spans[0][0]] + rebuilt + out[spans[-1][1]:]
    return out


def reorder_text(text, r, details, label=""):
    """One file, two passes: (1) inside every always block whose begin ... end body is nothing but nonblocking assignments to
    distinct registers, the statements are permuted (the AST reorder's always-block rule); (2) every run of consecutive assigns and
    of consecutive always blocks of every module is permuted. Each permutation differs from the identity. -> new text."""
    for pass_no in (1, 2):
        m = TS.mask(text, escaped=False)
        edits = []
        try:
            headers = TS.module_headers(m)
        except TS.Refuse as e:
            details.setdefault("refused", {})[label or "<file>"] = str(e)
            return text
        for name, _hs, bs, be in headers:
            try:
                items = TS.module_items(m, bs, be)
            except TS.Refuse as e:
                details.setdefault("refused", {})[name] = str(e)
                continue
            d = details.setdefault(name, {"assign_runs": 0, "always_runs": 0, "nba_blocks": 0, "items_moved": 0})
            if pass_no == 1:
                for kind, s, e in items:
                    if kind != "always":
                        continue
                    mo = re.search(r"\bbegin\b", m[s:e])
                    if mo is None:
                        continue
                    stmts = TS.nba_statements(m, s + mo.start(), e)
                    if stmts:
                        perm = P._permute(list(range(len(stmts))), r)
                        edits.append((stmts, perm))
                        d["nba_blocks"] += 1
                        d["items_moved"] += sum(1 for i, j in enumerate(perm) if i != j)
            else:
                for run in runs_of(items):
                    perm = P._permute(list(range(len(run))), r)
                    edits.append(([(s, e) for _, s, e in run], perm))
                    d[run[0][0] + "_runs"] += 1
                    d["items_moved"] += sum(1 for i, j in enumerate(perm) if i != j)
        text = _splice(text, edits)
    for name in [k for k, v in details.items() if k != "refused" and isinstance(v, dict) and not v.get("items_moved")]:
        del details[name]
    return text


def text_variants(design_files, seed, n, start=0):
    """-> [(k, details, {path: new_text})] for k in range(start, start + n); NotApplicable when no module has a run to permute."""
    texts = {str(f): open(f, errors="replace").read() for f in design_files}
    out = []
    for k in range(start, start + n):
        r = V.rng(seed, PTYPE, k)
        details = {}
        new = {f: reorder_text(t, r, details, label=f) for f, t in sorted(texts.items())}
        if not any(key != "refused" for key in details):
            raise P.NotApplicable("nothing to reorder at text level" + (f" (refused: {details['refused']})" if details.get("refused") else ""))
        out.append((k, {"reordered": details}, new))
    return out
