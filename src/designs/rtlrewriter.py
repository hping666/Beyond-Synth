"""RTLRewriter-Bench layout rules (calibration-only suite, docs/PLAN.md 1.1). The repository names files
inconsistently; this module turns each case directory into roles:
  original   the starting RTL (suffix _raw / _raw_N / _redundancy, camel-case ...Raw, or `basic[1]`, or the plain
             case file when no raw sibling exists)
  expert     the engineers' rewrite (_optimized / _optimzied / _improve / _improve_more / _opt / _opt_N, `optimized[1]`,
             or the plain case file when a raw/redundancy sibling exists)
  tool       RTLRewriter's own output (_ours)          llm   GPT-4 / Claude 3 / RTLCoder / VeriGen samples
  testbench  _test                                     other _revision and anything unclassifiable
The rule is deterministic and the resulting table is part of reports/phase1.md for a hand check."""
import re
from pathlib import Path

from src.designs import verilog as V

SUFFIX_ROLES = [("_test", "testbench"), ("_gpt4", "llm"), ("_gp4", "llm"), ("_claude3", "llm"), ("_RTLCoder", "llm"),
                ("_VeriGen", "llm"), ("_ours", "tool"), ("_revision", "other"), ("_improve_more", "expert"),
                ("_improved", "expert"), ("_improve", "expert"), ("_optimized", "expert"), ("_optimzied", "expert"),
                ("_opt_1", "expert"), ("_opt", "expert"), ("_raw_1", "original"), ("_raw_2", "original"),
                ("_raw", "original"), ("_redundancy", "original")]
_RAW_LIKE = re.compile(r"(_raw(_\d+)?|_redundancy|Raw)$")


def classify_file(stem, siblings):
    for suf, role in SUFFIX_ROLES:
        if stem.endswith(suf):
            return role
    if stem in ("basic", "basic1"):
        return "original"
    if stem in ("optimized", "optimized1"):
        return "expert"
    if stem.endswith("Raw"):
        return "original"
    if any(s != stem and _RAW_LIKE.search(s) for s in siblings):
        return "expert"
    return "original"


def classify_case(case_dir):
    files = sorted(p for p in Path(case_dir).iterdir() if p.suffix == ".v" and p.is_file())
    stems = [p.stem for p in files]
    roles = {p.name: classify_file(p.stem, stems) for p in files}
    return {"case": Path(case_dir).name, "category": Path(case_dir).parent.name, "dir": Path(case_dir), "roles": roles}


def short_cases(root):
    root = Path(root) / "short_benchmark"
    out = []
    for cat in sorted(p for p in root.iterdir() if p.is_dir()):
        for case in sorted(p for p in cat.iterdir() if p.is_dir()):
            out.append(classify_case(case))
    return out


def by_role(case, role):
    return [n for n, r in sorted(case["roles"].items()) if r == role]


def top_of(text):
    """The module of a single-file design: the one no other module in the file instantiates (first declared wins)."""
    spans = V.module_spans(text)
    if not spans:
        return None
    names = [n for n, _, _, _ in spans]
    used = set()
    for _, _, _, body in spans:
        used |= V.instantiated_modules(body)
    tops = [n for n in names if n not in used]
    return tops[0] if tops else names[0]


def long_pairs(root):
    """[(design, module, raw_file, plain_file, alternates)] for the long benchmark: modules with both a camel-case
    `<Module>Raw.v` (or `<Module>_raw*.v`) and a `<Module>.v`."""
    root = Path(root) / "long_benchmark"
    out = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        files = {p.stem: p for p in d.iterdir() if p.suffix == ".v"}
        for stem, plain in sorted(files.items()):
            if _RAW_LIKE.search(stem):
                continue
            raws = [s for s in files if s != stem and (s == stem + "Raw" or re.fullmatch(re.escape(stem) + r"_raw(_\d+)?", s))]
            if not raws:
                continue
            raws.sort(key=lambda s: (0 if s == stem + "Raw" else 1, s))
            out.append((d.name, stem, files[raws[0]], plain, [files[s] for s in raws[1:]]))
    return out


def resolve_closure(dir_files, top_file, prefer_raw):
    """Closure of the top module of `top_file` over the files of a long-benchmark directory; a module name defined in
    several files is taken from a raw-variant file when the top is a raw variant, else from a plain file."""
    table = {}
    for f in dir_files:
        for name, _, _, body in V.module_spans(f.read_text(errors="replace")):
            table.setdefault(name, []).append((f, V.instantiated_modules(body)))
    top_text = top_file.read_text(errors="replace")
    top = top_of(top_text)
    files, seen, stack, unknown, ambiguous = [top_file], {top}, [top], [], []
    while stack:
        m = stack.pop(0)
        for f, insts in table.get(m, [])[:1] if m == top else []:
            pass
        defs = table.get(m)
        if not defs:
            unknown.append(m)
            continue
        if m == top:
            chosen = next(((f, i) for f, i in defs if f == top_file), defs[0])
        else:
            raw_defs = [x for x in defs if _RAW_LIKE.search(x[0].stem)]
            plain_defs = [x for x in defs if not _RAW_LIKE.search(x[0].stem)]
            pool = (raw_defs or plain_defs) if prefer_raw else (plain_defs or raw_defs)
            chosen = pool[0]
            if len(defs) > 1:
                ambiguous.append((m, [str(x[0].name) for x in defs], chosen[0].name))
        f, insts = chosen
        if f not in files:
            files.append(f)
        for i in sorted(insts):
            if i not in seen:
                seen.add(i)
                stack.append(i)
    return {"top": top, "files": files, "unknown": unknown, "ambiguous": ambiguous}
