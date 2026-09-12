"""V4: VC Formal DPV (datapath validation, Hector) for RTL-vs-RTL equivalence of arithmetic datapath modules
(docs/spec/03-equivalence.md §1). Used as the second line when SEQ is inconclusive.

Why a project-owned driver: flow/vcf.py passes `-no_ui`, which DPV mode rejects, and DPV's console needs the
system terminfo database (config tools.vcformal.terminfo; without it the tool exits at start-up with
"'xterm': unknown terminal type"). The environment, ASCII work-directory check and process-tree cleanup are
reused from flow/vcf.py unchanged.

Script shape (from $VC_STATIC_HOME/doc/vcst/examples/DPV): two designs `spec` (D) and `impl` (C) read with the
VCS front end, inputs mapped by name at phase 1, one lemma per output `spec.<out>(P) == impl.<out>(P)`,
compose, run_solver, then getlemmas by status. Combinational modules use phase 1; a clocked module is created
with -clock/-reset and compared at the caller's phase.
"""
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

STATUSES = ("proven", "falsified", "inconclusive", "error", "not_run", "vacuous", "cond_proven", "cond_falsified", "killed")


def vacuity_check(job_dir, d_files, top, ports, cfg, *, design_id=None, sverilog=True, timeout_sec=None, max_mutants=4,
                  sim_cycles=500, max_time_sec=300):
    """Guardrail 2(iii) (DECISIONS 2026-09-12): before a DPV `proven` may be accepted for a module, DPV must falsify at
    least one injected-error variant of that module. Variants come from src/equiv/mutants.py; a variant counts only
    if lock-step simulation shows it differs from the original (a mutation in dead code proves nothing). The result
    is cached per (design_id, content of D) under results/raw/<design_id>/DPV_VACUITY/."""
    from src import config as C
    from src.equiv.harness import run_lockstep
    from src.equiv.mutants import generate_mutants
    d_files = [str(Path(f).resolve()) for f in d_files]
    cache = None
    if design_id:
        h = hashlib.sha256(b"".join(Path(f).read_bytes() for f in d_files) + top.encode()).hexdigest()[:16]
        cache = Path(C.results_dir(cfg)) / "raw" / design_id / "DPV_VACUITY" / f"{h}.json"
        if cache.exists():
            rec = json.loads(cache.read_text())
            rec["cached"] = True
            return rec
    outs = [n for n, p in ports.items() if p["dir"] in ("output", "inout")]
    idx = next((i for i, f in enumerate(d_files) if re.search(rf"^\s*module\s+{re.escape(top)}\b", Path(f).read_text(errors="replace"), re.M)), 0)
    text = Path(d_files[idx]).read_text(errors="replace")
    cfg_sim = dict(cfg)
    cfg_sim["sim"] = dict(cfg["sim"], random_cycles=int(sim_cycles))
    wd = Path(job_dir) / "v4_vacuity"
    wd.mkdir(parents=True, exist_ok=True)
    rec = {"status": "failed", "mutant": None, "tried": [], "design_id": design_id, "top": top, "cached": False}
    for name, mutated in generate_mutants(text)[:max_mutants]:
        mfile = wd / f"mutant_{len(rec['tried'])}{Path(d_files[idx]).suffix}"
        mfile.write_text(mutated)
        m_files = [str(mfile) if i == idx else f for i, f in enumerate(d_files)]
        sim = run_lockstep(wd / f"sim_{len(rec['tried'])}", d_files, m_files, top, ports, None, None, None, cfg_sim,
                           sverilog=sverilog, timeout_sec=timeout_sec)
        entry = {"mutant": name, "sim_status": sim.get("status"), "dpv_status": None}
        if sim.get("status") != "mismatch":
            rec["tried"].append(entry)
            continue
        dpv = run_dpv(wd / f"dpv_{len(rec['tried'])}", d_files, m_files, top, outs, cfg, sverilog=sverilog,
                      timeout_sec=timeout_sec, max_time_sec=max_time_sec)
        entry["dpv_status"] = dpv["v4_status"]
        entry["dpv_workdir"] = dpv["workdir"]
        rec["tried"].append(entry)
        if dpv["v4_status"] == "falsified":
            rec.update(status="ok", mutant=name, dpv_workdir=dpv["workdir"])
            break
        if dpv["v4_status"] == "proven":  # DPV calls a simulation-distinguished variant equal: the setup is vacuous
            rec.update(status="failed", error=f"DPV proved a variant that simulation distinguishes ({name})")
            break
    if rec["status"] != "ok" and not rec.get("error"):
        rec["error"] = "no injected-error variant was falsified by DPV" if rec["tried"] else "no mutation site in the module body"
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(rec, indent=1, sort_keys=True, default=str))
    return rec


def _vcf(cfg):
    fd = cfg["project"]["flow_dir"]
    if fd not in sys.path:
        sys.path.insert(0, fd)
    import vcf  # noqa: E402  (flow/vcf.py)
    return vcf


def dpv_script(d_files, c_files, top, outputs, *, clk=None, rst=None, rst_sense=None, sverilog=True, phase=1, max_time_sec=600, workers=1):
    lang = "sverilog" if sverilog else "verilog"
    vopt = "-sverilog " if sverilog else ""
    cr = ""
    if clk:
        cr += f" -clock {clk}"
    if rst:
        cr += f" -reset {rst}" + (" -negreset" if rst_sense == "low" else "")
    L = ["set_fml_appmode DPV",
         f"set_grid_usage -type rsh={int(workers)}",
         "proc compile_spec {} {",
         f"  create_design -name spec -top {top} -lang {lang}{cr}",
         f"  vcs {vopt}{' '.join(d_files)}",
         "  compile_design spec",
         "}",
         "proc compile_impl {} {",
         f"  create_design -name impl -top {top} -lang {lang}{cr}",
         f"  vcs {vopt}{' '.join(c_files)}",
         "  compile_design impl",
         "}",
         "proc ual {} {",
         f"  map_by_name -inputs -specphase {phase} -implphase {phase}"]
    for o in outputs:
        L.append(f"  lemma eq_{o} = spec.{o}({phase}) == impl.{o}({phase})")
    L += ["}",
          'set_user_assumes_lemmas_procedure "ual"',
          'puts "DPV_STEP compile_spec"', "compile_spec",
          'puts "DPV_STEP compile_impl"', "compile_impl",
          'puts "DPV_STEP compose"', "compose",
          'puts "DPV_STEP solve"',
          f"solveNB -ual ual -maxtime {int(max_time_sec)} p1",
          "proofwait p1",
          "catch { listproof }"]
    for st in STATUSES:
        L.append(f"foreach l [getlemmas -status {st}] {{ puts \"DPV_LEMMA {st} [lindex $l 0]\" }}")
    L += ['puts "DPV_END"', "exit"]
    return "\n".join(L) + "\n"


def run_dpv(job_dir, d_files, c_files, top, outputs, cfg, *, clk=None, rst=None, rst_sense=None, sverilog=True, phase=1,
            timeout_sec=None, max_time_sec=None):
    vcf = _vcf(cfg)
    wd = Path(job_dir) / "v4_dpv"
    wd.mkdir(parents=True, exist_ok=True)
    vcf._check_workdir(wd)
    dpv_min = int(cfg["timeouts"]["dpv_min"])
    max_time = int(max_time_sec or dpv_min * 60)
    timeout = float(timeout_sec or max_time + 300)
    d_files = [str(Path(f).resolve()) for f in d_files]
    c_files = [str(Path(f).resolve()) for f in c_files]
    tcl = wd / "dpv.tcl"
    tcl.write_text(dpv_script(d_files, c_files, top, outputs, clk=clk, rst=rst, rst_sense=rst_sense, sverilog=sverilog,
                              phase=phase, max_time_sec=max_time, workers=int(cfg["tools"]["vcformal"].get("seq_workers", 1))))
    env = vcf._env()
    env["TERM"] = "xterm"
    env["TERMINFO"] = cfg["tools"]["vcformal"].get("terminfo", "/lib/terminfo")
    shim = str(Path(__file__).resolve().parent.parent.parent / "scripts" / "bin")   # dc stand-in for hector's vlogan wrapper
    env["PATH"] = shim + ":" + env["PATH"]
    argv = [str(vcf.VCF_HOME / "bin/vcf"), "-fmode", "DPV", "-batch", "-output_log_file", "console.log", "-f", str(tcl)]
    if cfg["tools"]["vcformal"].get("dpv_bash_namespace", True):
        # the RTL frontend is launched through /bin/sh with bash syntax (eda-knowledge/05-traps.md #20 form 2);
        # bind bash over /bin/sh in a private mount namespace, as flow/vcf.py's VCF_NS does for SEQ
        argv = ["unshare", "-rm", "sh", "-c", 'mount --bind /bin/bash /bin/sh && exec "$@"', "--"] + argv
    t0 = time.time()
    try:
        p = subprocess.run(argv, cwd=str(wd), env=env, timeout=timeout, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, stdin=subprocess.DEVNULL)
        out, rc, timed_out = p.stdout, p.returncode, False
    except subprocess.TimeoutExpired as e:
        out, rc, timed_out = (e.stdout if isinstance(e.stdout, str) else ""), -1, True
        vcf._kill_tree(wd)
    (wd / "vcf_console_stdout.log").write_text(out or "")
    full = out or ""
    for name in ("console.log", "vcf.log"):
        if (wd / name).exists():
            full += "\n" + (wd / name).read_text(errors="replace")
    # the console echoes each script line before executing it, so only identifier-shaped names count
    # (the echoed template line carries "[lindex $l 0]" instead of a name)
    lemmas = {}
    for m in re.finditer(r"DPV_LEMMA (\w+) ([A-Za-z_][\w.]*)\s*$", full, re.M):
        lemmas.setdefault(m.group(2), m.group(1))
    plain = re.sub(r"\x1b\[[0-9;]*m", "", full)
    errors = [l.strip() for l in plain.splitlines() if re.match(r"^\s*(\[Error\]|Error-\[|Error:|(?:vcf> )?ERROR:)", l)]
    script_text = tcl.read_text()
    rec = {"v4_status": "error", "lemmas": lemmas, "seconds": round(time.time() - t0, 1), "workdir": str(wd), "returncode": rc,
           "timed_out": timed_out, "errors": errors[:8], "steps_done": list(dict.fromkeys(re.findall(r"DPV_STEP (\w+)", full))),
           "outputs": list(outputs), "assume_count": len(re.findall(r"^\s*assume\b", script_text, re.M))}
    checked_out = re.findall(r"License feature checked out: (VC-FORMAL-DPV[A-Z0-9_-]*|Hector)", plain)
    rec["licenses_checked_out"] = sorted(set(checked_out))
    lic = re.search(r"Unable to check out license feature \(([A-Z0-9_-]+)\)[^\n]*?status:\s*(-?\d+)", plain)
    if lic and not any(f.startswith("VC-FORMAL-DPV") for f in checked_out):
        # the tool tries the BASE feature first and falls back to ELITE; only a complete miss means no solver.
        # Then no lemma result can exist and the candidate stays undecided (CLAUDE.md rule 8).
        rec.update(v4_status="unavailable", license_feature=lic.group(1), license_status=int(lic.group(2)),
                   error=f"DPV license feature {lic.group(1)} unavailable (FlexNet status {lic.group(2)})")
        return rec
    if timed_out:
        rec["v4_status"] = "inconclusive"
        rec["error"] = f"DPV exceeded {timeout:.0f} s"
        return rec
    if lemmas and "DPV_END" in full:
        vals = set(lemmas.values())
        if "falsified" in vals or "cond_falsified" in vals:
            rec["v4_status"] = "falsified"
        elif vals <= {"proven"} and len(lemmas) == len(outputs):
            rec["v4_status"] = "proven"
        else:
            rec["v4_status"] = "inconclusive"
    else:
        rec["error"] = errors[0] if errors else f"no lemma results (rc {rc})"
    return rec
