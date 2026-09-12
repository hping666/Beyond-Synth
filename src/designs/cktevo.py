"""Module-level extraction from the CktEvo repositories (docs/PLAN.md 1.2: "about 30 medium-size modules, hundreds to
thousands of lines, self-contained interfaces"). A repository is scanned once; for every module the transitive
closure of instantiated modules is computed from the text (src/designs/verilog.py). The pool keeps modules whose own
size is at least `loc_min` lines and whose closure is at most `closure_loc_max` lines and that are not testbenches
and carry no duplicated module definition (config: design_sets.suites.cktevo). Unresolved references (vendor RAM
models under `ifdef`) are only flagged: the Yosys inventory and the E4 trial decide."""
from pathlib import Path

from src.designs import verilog as V

RTL_EXTS = (".v", ".sv")
HEADER_EXTS = (".v", ".sv", ".vh", ".h", ".svh", ".inc")


def scan_repo(repo):
    """-> {repo, files, modules{name: {module, file, own_loc, insts, flags, ports}}, headers, duplicates{name: [files]}}"""
    repo = Path(repo)
    files = sorted(p for p in repo.rglob("*") if p.is_file() and p.suffix in RTL_EXTS)
    modules, headers, dups = {}, [], {}
    for f in files:
        text = f.read_text(errors="replace")
        spans = V.module_spans(text)
        if not spans:
            headers.append(f)
            continue
        for name, a, b, body in spans:
            rec = {"module": name, "file": f, "own_loc": b - a + 1, "insts": V.instantiated_modules(body),
                   "flags": V.flags(body), "ports": V.declared_ports(body)}
            if name in modules:
                dups.setdefault(name, [modules[name]["file"]]).append(f)
            else:
                modules[name] = rec
    header_files = headers + sorted(p for p in repo.rglob("*") if p.is_file() and p.suffix in HEADER_EXTS[2:])
    return {"repo": repo, "files": files, "modules": modules, "headers": sorted(set(header_files)), "duplicates": dups}


def closure(scan, top):
    """Transitive closure of `top`: modules (top first), their files (in first-use order), unresolved names, size, flags."""
    mods = scan["modules"]
    seen, unknown, stack = [], set(), [top]
    while stack:
        m = stack.pop(0)
        if m in seen:
            continue
        if m not in mods:
            unknown.add(m)
            continue
        seen.append(m)
        stack.extend(sorted(mods[m]["insts"]))
    files = []
    for m in seen:
        f = mods[m]["file"]
        if f not in files:
            files.append(f)
    flags = V.merge_flags(*(mods[m]["flags"] for m in seen)) if seen else {}
    return {"modules": seen, "files": files, "unknown": sorted(unknown),
            "closure_loc": sum(mods[m]["own_loc"] for m in seen), "flags": flags}


def is_testbench(rec):
    return not rec["ports"] or (rec["flags"]["initial"] and rec["flags"]["sysfunc"])


def select_pool(scan, params):
    """Every module of the repository with its closure and the reasons (if any) that exclude it from the pool."""
    loc_min, loc_max = int(params["loc_min"]), int(params["closure_loc_max"])
    out = []
    for name, rec in sorted(scan["modules"].items()):
        c = closure(scan, name)
        reasons = []
        if is_testbench(rec):
            reasons.append("testbench-like (no ports, or initial block with system tasks)")
        if rec["own_loc"] < loc_min:
            reasons.append(f"own_loc {rec['own_loc']} < {loc_min}")
        if c["closure_loc"] > loc_max:
            reasons.append(f"closure_loc {c['closure_loc']} > {loc_max}")
        dup = [m for m in c["modules"] if m in scan["duplicates"]]
        if dup:
            reasons.append(f"duplicate module definitions in the repository: {dup}")
        out.append({"module": name, "file": rec["file"].name, "own_loc": rec["own_loc"], "closure_loc": c["closure_loc"],
                    "closure_modules": c["modules"], "files": c["files"], "flags": c["flags"], "unknown": c["unknown"],
                    "excluded": reasons})
    return out
