"""Phase 1.1 staging (docs/PLAN.md 1.1): copy every design of the pinned upstream checkouts (config
design_sets.sources) into data/designs/<suite>/<name>/ with a design.json (src/designs/catalog.py) describing top,
clock/reset ports, files, testbench, reference version and provenance (URL, commit, license, source paths, sha256).
The RTL copies are gitignored (upstream licenses differ); the metadata is versioned, so `scripts/stage_designs.py`
rebuilds the tree from the pinned commits and a sha256 mismatch is detected by catalog.validate().

Per-suite rules:
  rtllm        one design per `verified_<x>.v`; the top is the module name the testbench instantiates; when the
               file's `verified_<x>` module does not carry that name it is renamed (PLAN 1.2 canonical top name)
  drrtl        top / clock / reset from syn_flow/design_all.json; testbenches only where the repository ships one
  rtlopt       start = the suboptimal version, reference = `<name>_ref` (expert-optimized)
  cktevo       module-level extraction (src/designs/cktevo.py), one design per pool module, `include files copied
  rtlrewriter  roles per file (src/designs/rtlrewriter.py); start = original, reference = expert, other versions as samples
"""
import json
import shutil
import subprocess
from pathlib import Path

from src import config as C
from src.designs import catalog as K
from src.designs import cktevo as CK
from src.designs import rtlrewriter as RW
from src.designs import verilog as V
from src.equiv.ports import _CLOCK, _RESET, _RESET_HIGH


class StageError(RuntimeError):
    pass


def source_root(cfg, suite):
    p = Path(cfg["design_sets"]["sources"][suite]["local"])
    return p if p.is_absolute() else Path(C.ROOT) / p


def git_head(path):
    try:
        return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def source_block(cfg, suite, paths):
    s = cfg["design_sets"]["sources"][suite]
    head = git_head(source_root(cfg, suite))
    return {"suite_key": suite, "url": s["url"], "commit": s["commit"],
            "commit_verified": (head == s["commit"]) if head else None, "license": s["license"],
            "paths": [str(p) for p in paths], "note": s.get("note")}


def guess_control(text, top):
    """Regex guess of (clock ports, reset port, reset sense) for the staging record; the Yosys inventory
    (src/designs/inventory.py) replaces it with the parsed values."""
    spans = {n: body for n, _, _, body in V.module_spans(text)}
    ports = V.declared_ports(spans.get(top, V.strip_comments(text)))
    clks = [n for n, d, w in ports if d == "input" and not w and _CLOCK.match(n)]
    rst = sense = None
    for n, d, w in ports:
        if d == "input" and not w and n not in clks:
            if _RESET.match(n):
                rst, sense = n, "low"
                break
            if _RESET_HIGH.match(n):
                rst, sense = n, "high"
                break
    return clks, rst, sense


def _fresh(ddir):
    for sub in ("rtl", "tb", "reference", "samples"):
        shutil.rmtree(Path(ddir) / sub, ignore_errors=True)
    Path(ddir).mkdir(parents=True, exist_ok=True)


def _copy(src, ddir, sub, name=None):
    dst = Path(ddir) / sub / (name or Path(src).name)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return f"{sub}/{dst.name}"


def _write(ddir, sub, name, text):
    dst = Path(ddir) / sub / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text)
    return f"{sub}/{name}"


def _finish(suite, name, top, files, *, ddir, clk_ports, rst_port, rst_sense, sverilog, incdirs, tb, reference,
            samples, source, tags, notes, includes=None):
    d = {"design_id": K.design_id_for(suite, name), "suite": suite, "name": name, "top": top, "files": files,
         "clk_ports": clk_ports, "rst_port": rst_port, "rst_sense": rst_sense, "sverilog": bool(sverilog),
         "incdirs": incdirs, "includes": includes or [], "tb": tb, "reference": reference, "samples": samples or [],
         "source": source, "tags": tags, "notes": notes, "_dir": str(ddir)}
    d["sha256"] = {rel: K.sha256_of(Path(ddir) / rel) for rel in K.hashed_files(d)}
    d["loc"] = sum(V.count_lines(Path(ddir) / rel) for rel in files)
    return K.write_design(d)


def _single_rtl(dirpath):
    files = sorted(p for p in Path(dirpath).iterdir() if p.suffix in (".v", ".sv") and p.is_file())
    if len(files) != 1:
        raise StageError(f"{dirpath}: expected exactly one RTL file, found {[f.name for f in files]}")
    return files[0]


# --------------------------------------------------------------------------- RTLLM v2.0
def stage_rtllm(cfg, log=print):
    root = source_root(cfg, "rtllm")
    out, skipped = [], []
    for f in sorted(root.rglob("verified_*.v")):
        src_dir, name = f.parent, f.parent.name
        try:
            rtl = f.read_text(errors="replace")
            mods = V.module_names(rtl)
            tbp = src_dir / "testbench.v"
            tb_txt = tbp.read_text(errors="replace") if tbp.exists() else ""
            tb_mods = set(V.module_names(tb_txt))
            inst = set()
            for _, _, _, body in V.module_spans(tb_txt):
                inst |= V.instantiated_modules(body)
            inst -= tb_mods
            notes = []
            declared = sorted(m for m in inst if m in mods)
            if len(declared) == 1:
                top = declared[0]
            elif len(declared) > 1:
                raise StageError(f"testbench instantiates several modules of the design: {declared}")
            else:
                missing = sorted(inst - set(mods))
                vmods = [m for m in mods if m.startswith("verified_")]
                if not tb_txt:
                    raise StageError("no testbench.v: canonical top name unknown")
                if len(missing) == 1 and len(vmods) == 1:
                    top = missing[0]
                    rtl = V.rename_identifier(rtl, vmods[0], top)
                    notes.append(f"module {vmods[0]} renamed to {top}, the name the testbench instantiates (PLAN 1.2 canonical top)")
                else:
                    raise StageError(f"cannot map the testbench instantiation {missing} onto the modules {mods}")
            ddir = K.design_dir("rtllm", name)
            _fresh(ddir)
            rel = _write(ddir, "rtl", f"{name}.v", rtl)
            tb = None
            if tb_txt:
                data = [_copy(x, ddir, "tb") for x in sorted(src_dir.iterdir())
                        if x.is_file() and x.name not in ("design_description.txt", "makefile", "testbench.v", f.name)]
                tb = {"files": [_copy(tbp, ddir, "tb")], "top": sorted(tb_mods)[0] if len(tb_mods) == 1 else None, "data": data}
            clks, rst, sense = guess_control(rtl, top)
            d = _finish("rtllm", name, top, [rel], ddir=ddir, clk_ports=clks, rst_port=rst, rst_sense=sense, sverilog=False,
                        incdirs=[], tb=tb, reference=None, samples=None,
                        source=source_block(cfg, "rtllm", [f.relative_to(root)]), tags=["rtllm"], notes=notes)
            out.append(d)
        except (StageError, K.CatalogError) as e:
            skipped.append((name, str(e)))
            log(f"SKIP rtllm/{name}: {e}")
    return out, skipped


# --------------------------------------------------------------------------- Dr.RTL
def stage_drrtl(cfg, log=print):
    root = source_root(cfg, "drrtl")
    table = json.loads((root / "syn_flow" / "design_all.json").read_text())
    out, skipped = [], []
    for name, (top, clk, rst, ext) in sorted(table.items()):
        try:
            f = root / "rtl_dataset" / f"{name}.v0.{ext}"
            if not f.exists():
                raise StageError(f"{f} missing")
            rtl = f.read_text(errors="replace")
            if top not in V.module_names(rtl):
                raise StageError(f"top {top} not declared in {f.name}")
            notes = []
            if _RESET.match(rst):
                sense = "low"
            elif _RESET_HIGH.match(rst):
                sense = "high"
            else:
                sense = "low" if rst.endswith(("_n", "N")) else "high"
                notes.append(f"reset sense of {rst} guessed from its name ({sense}); verify in the Phase 1 hand check")
            clks, _, _ = guess_control(rtl, top)
            clk_ports = [clk] + [c for c in clks if c != clk]
            ddir = K.design_dir("drrtl", name)
            _fresh(ddir)
            rel = _copy(f, ddir, "rtl", f"{name}.{ext}")
            tb = None
            tbp = root / "syn_flow_eda" / "tb" / f"{name}.v"
            if tbp.exists():
                tmods = V.module_names(tbp.read_text(errors="replace"))
                tb = {"files": [_copy(tbp, ddir, "tb")], "top": tmods[0] if len(tmods) == 1 else None, "data": []}
            d = _finish("drrtl", name, top, [rel], ddir=ddir, clk_ports=clk_ports, rst_port=rst, rst_sense=sense,
                        sverilog=(ext == "sv"), incdirs=[], tb=tb, reference=None, samples=None,
                        source=source_block(cfg, "drrtl", [f.relative_to(root)]), tags=["drrtl"], notes=notes)
            out.append(d)
        except (StageError, K.CatalogError) as e:
            skipped.append((name, str(e)))
            log(f"SKIP drrtl/{name}: {e}")
    return out, skipped


# --------------------------------------------------------------------------- RTL-OPT
def stage_rtlopt(cfg, log=print):
    root = source_root(cfg, "rtlopt") / "benchmark"
    out, skipped = [], []
    for sub in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.endswith("_ref")):
        name = sub.name
        try:
            ref = root / f"{name}_ref"
            if not ref.is_dir():
                raise StageError("no _ref sibling (unpaired design)")
            src, rsrc = _single_rtl(sub), _single_rtl(ref)
            text, rtext = src.read_text(errors="replace"), rsrc.read_text(errors="replace")
            if name not in V.module_names(text):
                raise StageError(f"top {name} not declared in {src.name}")
            rtop = f"{name}_ref"
            if rtop not in V.module_names(rtext):
                raise StageError(f"reference top {rtop} not declared in {rsrc.name}")
            ddir = K.design_dir("rtlopt", name)
            _fresh(ddir)
            rel, rrel = _copy(src, ddir, "rtl"), _copy(rsrc, ddir, "reference")
            clks, rst, sense = guess_control(text, name)
            d = _finish("rtlopt", name, name, [rel], ddir=ddir, clk_ports=clks, rst_port=rst, rst_sense=sense,
                        sverilog=(src.suffix == ".sv" or rsrc.suffix == ".sv"), incdirs=[], tb=None,
                        reference={"files": [rrel], "top": rtop, "note": "expert-optimized version (RTL-OPT golden reference)"},
                        samples=None, source=source_block(cfg, "rtlopt", [src.relative_to(root.parent), rsrc.relative_to(root.parent)]),
                        tags=["rtlopt", "pair"], notes=[])
            out.append(d)
        except (StageError, K.CatalogError) as e:
            skipped.append((name, str(e)))
            log(f"SKIP rtlopt/{name}: {e}")
    return out, skipped


# --------------------------------------------------------------------------- CktEvo modules
def stage_cktevo(cfg, log=print):
    base = source_root(cfg, "cktevo")
    root = base / "benchmark"
    params = cfg["design_sets"]["suites"]["cktevo"]
    out, skipped, pool_report = [], [], {}
    for repo in sorted(p for p in root.iterdir() if p.is_dir()):
        scan = CK.scan_repo(repo)
        pool = CK.select_pool(scan, params)
        pool_report[repo.name] = [{**{k: v for k, v in rec.items() if k != "files"}, "files": [f.name for f in rec["files"]]} for rec in pool]
        for rec in pool:
            if rec["excluded"]:
                continue
            name = f"{repo.name}__{rec['module']}"
            try:
                ddir = K.design_dir("cktevo", name)
                _fresh(ddir)
                files = [_copy(f, ddir, "rtl") for f in rec["files"]]
                includes = [_copy(h, ddir, "rtl") for h in scan["headers"] if h not in rec["files"]]
                text = rec["files"][0].read_text(errors="replace")
                clks, rst, sense = guess_control(text, rec["module"])
                notes = [f"closure: {len(rec['closure_modules'])} modules, {rec['closure_loc']} lines ({', '.join(rec['closure_modules'][:12])}{'...' if len(rec['closure_modules']) > 12 else ''})"]
                if rec["unknown"]:
                    notes.append(f"unresolved references in the text (vendor models under `ifdef?): {rec['unknown']}")
                d = _finish("cktevo", name, rec["module"], files, ddir=ddir, clk_ports=clks, rst_port=rst, rst_sense=sense,
                            sverilog=any(f.suffix == ".sv" for f in rec["files"]), incdirs=["rtl"], tb=None, reference=None,
                            samples=None, source=source_block(cfg, "cktevo", [f.relative_to(base) for f in rec["files"]]),
                            tags=["cktevo", repo.name], notes=notes, includes=includes)
                out.append(d)
            except (StageError, K.CatalogError) as e:
                skipped.append((name, str(e)))
                log(f"SKIP cktevo/{name}: {e}")
    (K.DESIGNS_DIR / "cktevo").mkdir(parents=True, exist_ok=True)
    (K.DESIGNS_DIR / "cktevo" / "POOL.json").write_text(json.dumps(
        {"params": {k: params[k] for k in ("loc_min", "closure_loc_max")}, "repos": pool_report}, indent=1, sort_keys=True, default=str) + "\n")
    return out, skipped


# --------------------------------------------------------------------------- RTLRewriter-Bench
def stage_rtlrewriter(cfg, log=print):
    root = source_root(cfg, "rtlrewriter")
    out, skipped = [], []
    for case in RW.short_cases(root):
        name = f"{case['category']}__{case['case']}"
        try:
            originals, experts = RW.by_role(case, "original"), RW.by_role(case, "expert")
            if not originals:
                raise StageError(f"no original version among {sorted(case['roles'])}")
            start = case["dir"] / originals[0]
            text = start.read_text(errors="replace")
            top = RW.top_of(text)
            if top is None:
                raise StageError(f"no module in {start.name}")
            ddir = K.design_dir("rtlrewriter", name)
            _fresh(ddir)
            rel = _copy(start, ddir, "rtl")
            reference = None
            if experts:
                rp = case["dir"] / experts[0]
                reference = {"files": [_copy(rp, ddir, "reference")], "top": RW.top_of(rp.read_text(errors="replace")),
                             "note": "engineers' rewrite" + (f"; further expert versions staged as samples: {experts[1:]}" if len(experts) > 1 else "")}
            samples = []
            for role, names in (("llm", RW.by_role(case, "llm")), ("tool", RW.by_role(case, "tool")),
                                ("expert", experts[1:]), ("original", originals[1:]), ("other", RW.by_role(case, "other"))):
                for n in names:
                    p = case["dir"] / n
                    samples.append({"files": [_copy(p, ddir, "samples")], "top": RW.top_of(p.read_text(errors="replace")), "role": role})
            tests = RW.by_role(case, "testbench")
            tb = {"files": [_copy(case["dir"] / t, ddir, "tb") for t in tests], "top": None, "data": []} if tests else None
            clks, rst, sense = guess_control(text, top)
            d = _finish("rtlrewriter", name, top, [rel], ddir=ddir, clk_ports=clks, rst_port=rst, rst_sense=sense, sverilog=False,
                        incdirs=[], tb=tb, reference=reference, samples=samples,
                        source=source_block(cfg, "rtlrewriter", [(case["dir"] / n).relative_to(root) for n in sorted(case["roles"])]),
                        tags=["rtlrewriter", "short", case["category"], "calibration_only"],
                        notes=[f"file roles: {json.dumps(case['roles'], sort_keys=True)}"])
            out.append(d)
        except (StageError, K.CatalogError) as e:
            skipped.append((name, str(e)))
            log(f"SKIP rtlrewriter/{name}: {e}")
    for design, module, raw, plain, alts in RW.long_pairs(root):
        name = f"long_{design}__{module}"
        try:
            dir_files = sorted(p for p in raw.parent.iterdir() if p.suffix == ".v")
            c = RW.resolve_closure(dir_files, raw, prefer_raw=True)
            rc = RW.resolve_closure(dir_files, plain, prefer_raw=False)
            if c["top"] is None or rc["top"] is None:
                raise StageError("no module in the raw or plain file")
            ddir = K.design_dir("rtlrewriter", name)
            _fresh(ddir)
            files = [_copy(f, ddir, "rtl") for f in c["files"]]
            reference = {"files": [_copy(f, ddir, "reference") for f in rc["files"]], "top": rc["top"],
                         "note": "engineers' rewrite (long benchmark, module-level pair)"}
            samples = [{"files": [_copy(a, ddir, "samples")], "top": RW.top_of(a.read_text(errors="replace")), "role": "original"} for a in alts]
            notes = [f"closure of {c['top']}: {[f.name for f in c['files']]}"]
            if c["unknown"]:
                notes.append(f"unresolved references: {c['unknown']}")
            if c["ambiguous"]:
                notes.append(f"module names defined in several files, chosen by variant: {c['ambiguous']}")
            text = raw.read_text(errors="replace")
            clks, rst, sense = guess_control(text, c["top"])
            d = _finish("rtlrewriter", name, c["top"], files, ddir=ddir, clk_ports=clks, rst_port=rst, rst_sense=sense, sverilog=False,
                        incdirs=[], tb=None, reference=reference, samples=samples,
                        source=source_block(cfg, "rtlrewriter", [f.relative_to(root) for f in c["files"] + rc["files"]]),
                        tags=["rtlrewriter", "long", design, "calibration_only"], notes=notes)
            out.append(d)
        except (StageError, K.CatalogError) as e:
            skipped.append((name, str(e)))
            log(f"SKIP rtlrewriter/{name}: {e}")
    return out, skipped


STAGERS = {"rtllm": stage_rtllm, "drrtl": stage_drrtl, "rtlopt": stage_rtlopt, "cktevo": stage_cktevo, "rtlrewriter": stage_rtlrewriter}


def write_suite_index(cfg, suite, designs, skipped):
    sdir = K.DESIGNS_DIR / suite
    sdir.mkdir(parents=True, exist_ok=True)
    s = cfg["design_sets"]["sources"][suite]
    index = {"suite": suite, "count": len(designs), "skipped": skipped, "source": {k: s.get(k) for k in ("url", "commit", "license", "note")},
             "designs": [{"design_id": d["design_id"], "top": d["top"], "loc": d["loc"], "files": d["files"], "clk_ports": d["clk_ports"],
                          "tb": bool(d["tb"]), "reference": bool(d["reference"]), "tags": d["tags"]} for d in designs]}
    (sdir / "index.json").write_text(json.dumps(index, indent=1, sort_keys=True) + "\n")
    head = git_head(source_root(cfg, suite))
    lines = [f"# {suite} — source record (Phase 1.1)", "",
             f"- Source: {s['url']}", f"- Pinned commit: `{s['commit']}` (local checkout at `{s['local']}`: {'verified' if head == s['commit'] else 'HEAD ' + str(head)})",
             f"- License: {s['license']}", f"- Note: {s.get('note') or '-'}",
             f"- Staged designs: {len(designs)}; skipped: {len(skipped)}", "",
             "Staged copies (`rtl/`, `tb/`, `reference/`, `samples/`) are rebuilt by `scripts/stage_designs.py` and are not versioned; "
             "`design.json` carries top, ports, provenance and sha256 of every copy.", ""]
    if skipped:
        lines += ["## Skipped", ""] + [f"- {n}: {why}" for n, why in skipped] + [""]
    lines += ["## Designs", "", "| design_id | top | loc | clocks | tb | reference | source paths |", "|---|---|---|---|---|---|---|"]
    for d in designs:
        lines.append(f"| {d['design_id']} | {d['top']} | {d['loc']} | {' '.join(d['clk_ports']) or '-'} | {'y' if d['tb'] else '-'} | "
                     f"{'y' if d['reference'] else '-'} | {', '.join(d['source']['paths'][:3])}{' ...' if len(d['source']['paths']) > 3 else ''} |")
    (sdir / "SOURCE.md").write_text("\n".join(lines) + "\n")
    return index
