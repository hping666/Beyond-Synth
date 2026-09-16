#!/usr/bin/env python3
"""Phase 5 storage footprint: measure what the existing records occupy and project Phase 5 (G5 decisions item 5).

  measure   walk results/raw (never the hidden tree: CLAUDE.md rule 3), results/candidates, results/llm, results/queue,
            results/db, results/snapshots, results/scratch; aggregate bytes and file counts per record kind, configuration,
            object type (baseline / perturbation / candidate), status or verdict and file category; write
            reports/data/phase5_footprint_measured.json (aggregates only, no record content)
  project   read the measurement, config `scale` / `retention` / `exp5` and the Phase 4 rates by tier from the results
            database; write reports/data/phase5_footprint.md with the projected footprint under the current retention
            rules and under the tiered policy of G5 item 5 (ii)

Read-only on results/ (measurement); nothing is deleted or moved here (rule 5).
"""
import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import load as load_config  # noqa: E402

DC_CONFIGS = {"E1", "E1d", "E2", "E2g", "E2r", "E2t", "E3", "E4", "K_asap7", "K_sky130hd", "K_nangate45", "PT"}
YOSYS_CONFIGS = {"Y", "Ycoevo", "O0", "O1", "O2", "O"}
SMALL_REPORTS = {"qor.rpt", "area.rpt", "area_hier.rpt", "timing.rpt", "power_default.rpt", "power_saif.rpt",
                 "metrics.txt", "status.txt", "saif.rpt", "clock_gating.rpt", "resources.rpt"}


def categorize(kind, rel):
    """File category of a record-relative path, per record kind (dc / yosys / eq / other)."""
    parts = rel.split("/")
    name = parts[-1]
    if name == "meta.json" or name == "equiv.json":
        return "record"
    if kind in ("dc", "yosys"):
        if parts[0] == "inputs":
            return "inputs"
        if parts[0] == "outputs":
            if len(parts) > 1 and parts[1] in ("dc_work", "mw_design", "work", "tmp"):
                return "scratch"
            if len(parts) > 1 and parts[1] == "reports":
                if name == "netlist.v" or name.endswith(".v") or name.endswith(".vg"):
                    return "netlist"
                if name.endswith(".ddc"):
                    return "ddc"
                if name in SMALL_REPORTS:
                    return "small_reports"
                if name.endswith(".saif"):
                    return "saif"
                return "other_reports"
            if name.endswith(".log") or name.endswith(".txt"):
                return "logs"
            if name.endswith(".saif"):
                return "saif"
            if name.endswith(".v") or name.endswith(".json"):
                return "netlist"
            return "other"
        if name.endswith(".saif"):
            return "saif"
        if name.endswith(".log"):
            return "logs"
        return "other"
    if kind == "eq":
        if name.endswith(".saif"):
            return "saif"
        if parts[0].startswith("v1_ports"):
            return "v1_ports"
        if parts[0] == "v2_sim":
            if name.endswith(".vcd"):
                return "vcd"
            if name.endswith(".vcd.gz"):
                return "vcd_gz"
            if name == "trace.txt":
                return "trace"
            if parts[1] in ("csrc", "simv.daidir") or name.startswith("simv"):
                return "vcs_build"
            if name.endswith(".log") or name.endswith(".key"):
                return "logs"
            return "sim_other"
        if parts[0] == "v3_seq":
            if len(parts) > 1 and parts[1] == "vcst_rtdb":
                return "seq_rtdb"
            if name.startswith("learnt_data"):
                return "seq_learnt"
            if name.endswith(".log"):
                return "logs"
            if name.endswith(".vcd") or "cex" in name or "counter" in name:
                return "seq_cex"
            return "seq_other"
        if parts[0].startswith("v4"):
            return "v4"
        return "other"
    return "other"


def walk_bytes(path):
    """Total bytes and file count under path (lstat, no link following)."""
    total, n = 0, 0
    stack = [path]
    while stack:
        p = stack.pop()
        try:
            with os.scandir(p) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                        elif e.is_file(follow_symlinks=False):
                            total += e.stat(follow_symlinks=False).st_size
                            n += 1
                    except OSError:
                        pass
        except OSError:
            pass
    return total, n


def iter_files(path):
    stack = [path]
    while stack:
        p = stack.pop()
        try:
            with os.scandir(p) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                        elif e.is_file(follow_symlinks=False):
                            yield e.path, e.stat(follow_symlinks=False).st_size
                    except OSError:
                        pass
        except OSError:
            pass


def record_identity(rec_dir, config):
    """(kind, obj, status, cand_id) of a record directory from its meta.json / equiv.json; no content beyond those keys is used."""
    if config == "EQ":
        kind = "eq"
        f = rec_dir / "equiv.json"
    else:
        kind = "dc" if config in DC_CONFIGS or config.startswith("K_") or config.startswith("E") else ("yosys" if config in YOSYS_CONFIGS else "other")
        f = rec_dir / "meta.json"
    obj, status, cand_id = "unknown", "unknown", None
    try:
        m = json.loads(f.read_text())
        cand_id = m.get("cand_id") or None
        if m.get("cand_id"):
            obj = "cand"
        elif m.get("pert_id"):
            obj = "pert"
        elif m.get("is_baseline") or kind != "eq":
            obj = "base"
        else:
            obj = "pert" if m.get("pert") else "cand"
        status = m.get("verdict") if kind == "eq" else m.get("status")
        status = status or "unknown"
    except Exception:
        status = "no_record_file"
    return kind, obj, status, cand_id


def measure(args):
    cfg = load_config()
    results = Path(cfg["project"]["results_dir"]) if cfg.get("project", {}).get("results_dir") else ROOT / "results"
    raw = results / "raw"
    agg = defaultdict(lambda: {"bytes": 0, "files": 0})       # (design, config, kind, obj, status, category)
    recs = defaultdict(int)                                     # (design, config, kind, obj, status) -> records
    per_design_records = []                                     # per record: design, config, kind, obj, status, bytes
    n_rec = 0
    for design_dir in sorted(raw.iterdir()):
        if not design_dir.is_dir():
            continue
        design = design_dir.name
        for cfg_dir in sorted(design_dir.iterdir()):
            if not cfg_dir.is_dir():
                continue
            config = cfg_dir.name
            for rec_dir in cfg_dir.iterdir():
                if not rec_dir.is_dir():
                    continue
                kind, obj, status, cand_id = record_identity(rec_dir, config)
                recs[(design, config, kind, obj, status)] += 1
                rec_bytes = 0
                cats = defaultdict(int)
                for fpath, size in iter_files(str(rec_dir)):
                    rel = os.path.relpath(fpath, rec_dir)
                    cat = categorize(kind, rel)
                    a = agg[(design, config, kind, obj, status, cat)]
                    a["bytes"] += size
                    a["files"] += 1
                    rec_bytes += size
                    cats[cat] += size
                per_design_records.append((design, config, kind, obj, status, rec_bytes, cand_id, dict(cats)))
                n_rec += 1
                if n_rec % 2000 == 0:
                    print(f"  {n_rec} records ...", file=sys.stderr, flush=True)
    other_dirs = {}
    for name in ("candidates", "llm", "queue", "db", "snapshots", "scratch"):
        d = results / name
        if d.exists():
            other_dirs[name] = dict(zip(("bytes", "files"), walk_bytes(str(d))))
    # candidate run directories: per-run bytes, and by file suffix
    cand_suffix = defaultdict(lambda: {"bytes": 0, "files": 0})
    cand_runs = 0
    cdir = results / "candidates"
    if cdir.exists():
        for run_dir in cdir.iterdir():
            if run_dir.is_dir():
                cand_runs += 1
                for fpath, size in iter_files(str(run_dir)):
                    suf = Path(fpath).suffix or "(none)"
                    if Path(fpath).parent != run_dir:
                        suf = Path(fpath).parent.name + "/" + suf
                    cand_suffix[suf]["bytes"] += size
                    cand_suffix[suf]["files"] += 1
    import datetime
    out = {
        "measured_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "results_dir": str(results),
        "records": [{"design": k[0], "config": k[1], "kind": k[2], "obj": k[3], "status": k[4], "n": v} for k, v in sorted(recs.items())],
        "bytes": [{"design": k[0], "config": k[1], "kind": k[2], "obj": k[3], "status": k[4], "category": k[5], **v} for k, v in sorted(agg.items())],
        "per_record": [{"design": r[0], "config": r[1], "kind": r[2], "obj": r[3], "status": r[4], "bytes": r[5], "cand_id": r[6], "cats": r[7]} for r in per_design_records],
        "other_dirs": other_dirs,
        "candidates_by_suffix": dict(cand_suffix),
        "candidate_runs": cand_runs,
    }
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, indent=1))
    total = sum(v["bytes"] for v in agg.values())
    print(f"records {n_rec}, raw bytes {total / 1e9:.2f} GB, other dirs " + ", ".join(f"{k} {v['bytes'] / 1e9:.2f} GB" for k, v in other_dirs.items()))
    print(f"written {outp}")


def _gb(x):
    return x / 1e9


def summarize(args):
    """Print the measurement as tables: bytes per record by (kind, obj, status) and by category, overall and by design tier."""
    m = json.loads(Path(args.measured).read_text())
    by = defaultdict(lambda: {"bytes": 0, "files": 0})
    recs = defaultdict(int)
    for r in m["records"]:
        recs[(r["kind"], r["config"], r["obj"], r["status"])] += r["n"]
    for b in m["bytes"]:
        by[(b["kind"], b["config"], b["obj"], b["status"], b["category"])]["bytes"] += b["bytes"]
        by[(b["kind"], b["config"], b["obj"], b["status"], b["category"])]["files"] += b["files"]
    print("kind config obj status : records, GB, MB/record")
    tot = defaultdict(int)
    for k, n in sorted(recs.items()):
        gb = sum(v["bytes"] for kk, v in by.items() if kk[:4] == k)
        tot[k] = gb
        print(f"  {k[0]:6s} {k[1]:10s} {k[2]:5s} {k[3]:16s} {n:6d} {gb / 1e9:8.2f} {gb / n / 1e6:8.2f}")
    print("\ncategory share by kind (GB):")
    cat = defaultdict(int)
    for kk, v in by.items():
        cat[(kk[0], kk[4])] += v["bytes"]
    for k, v in sorted(cat.items(), key=lambda kv: (kv[0][0], -kv[1])):
        print(f"  {k[0]:6s} {k[1]:14s} {v / 1e9:8.2f}")
    print("\nother dirs:", {k: f"{v['bytes'] / 1e9:.2f} GB / {v['files']} files" for k, v in m["other_dirs"].items()})
    print("candidate runs:", m["candidate_runs"], {k: f"{v['bytes'] / 1e6:.1f} MB / {v['files']}" for k, v in sorted(m["candidates_by_suffix"].items(), key=lambda kv: -kv[1]["bytes"])[:8]})


# ----------------------------------------------------------------------------- projection (G5 item 5 (i)-(iii))
EQ_KEEP_SLIM = {"record", "logs", "seq_cex", "seq_other", "sim_other"}         # tiered policy: what an equivalence record of a non-accepted candidate keeps
DC_KEEP_SLIM = {"record", "small_reports", "logs"}                            # tiered policy: what a DC / Yosys record of a non-accepted candidate keeps
LADDER_DC = ("E1", "E1d", "E2", "E2g", "E3")
LADDER_YOSYS = ("Y", "O0", "O1", "O2", "Ycoevo")
PT_RECORD_BYTES = 100_000                                                     # H4 (PrimeTime) record: reports only (no PT record measured yet; upper bound)
DB_BYTES_PER_EVAL, DB_BYTES_PER_CAND = 6_000, 4_000                            # results.sqlite growth per row (164 MB / 24k evaluations + 3k candidates + 54k jobs)
QUEUE_BYTES_PER_JOB = 1_000


class Sizes:
    """Mean record bytes per (tier, kind, config, obj, status) with fallbacks (cand -> pert -> base; tier -> medium)."""

    def __init__(self, per_record, tiers):
        self.tier_of = {d: t for t, ds in tiers.items() for d in ds}
        self.acc = defaultdict(lambda: [0, 0])          # (tier, kind, config, obj, status) -> [n, bytes]
        self.cat = defaultdict(lambda: defaultdict(int))   # same key -> category -> bytes
        for r in per_record:
            t = self.tier_of.get(r["design"])
            if not t:
                continue
            k = (t, r["kind"], r["config"], r["obj"], r["status"])
            self.acc[k][0] += 1
            self.acc[k][1] += r["bytes"]
            for c, b in (r.get("cats") or {}).items():
                self.cat[k][c] += b

    def mean(self, tier, kind, config, status, objs=("cand", "pert", "base"), keep=None):
        """Mean bytes of a record; `keep` restricts to a set of categories (the slim record). Falls back across objs and to the medium tier."""
        for t in (tier, "medium", "large", "small"):
            for obj in objs:
                k = (t, kind, config, obj, status)
                n, b = self.acc.get(k, (0, 0))
                if n:
                    if keep is None:
                        return b / n, (t, obj, n)
                    return sum(v for c, v in self.cat[k].items() if c in keep) / n, (t, obj, n)
        return 0.0, None


def _rates(conn, tiers):
    """Phase 4 B0 verdict mix, duplicate share and accepted-of-proven per tier; Phase 3 M accepted-of-proven (all models)."""
    tier_of = {d: t for t, ds in tiers.items() for d in ds}
    rows = conn.execute("SELECT c.design_id, c.verdict, c.label, c.accepted, c.in_archive FROM candidates c JOIN runs r USING(run_id) WHERE r.exp='phase4' AND r.arm='B0'").fetchall()
    per = defaultdict(lambda: defaultdict(int))
    for design, verdict, label, acc, arch in rows:
        t = tier_of.get(design)
        if not t:
            continue
        per[t]["n"] += 1
        if label == "duplicate":
            per[t]["duplicate"] += 1
        else:
            per[t]["eq"] += 1
            per[t][verdict or "none"] += 1
        if verdict == "proven":
            per[t]["proven_all"] += 1
            per[t]["accepted"] += int(bool(acc or arch))
    out = {}
    for t, d in per.items():
        eq = max(d["eq"], 1)
        out[t] = {"n": d["n"], "p_dup": d["duplicate"] / d["n"],
                  "verdicts": {v: d[v] / eq for v in ("proven", "sim_fail", "falsified", "rejected", "inconclusive")},
                  "p_acc_b": (d["accepted"] / d["proven_all"]) if d["proven_all"] else None}
    m3 = conn.execute("SELECT COUNT(*), SUM(accepted OR in_archive) FROM candidates c JOIN runs r USING(run_id) WHERE r.exp='phase3' AND c.verdict='proven'").fetchone()
    p_acc_m = (m3[1] or 0) / m3[0] if m3[0] else 0.0
    rt = conn.execute("SELECT COUNT(*), SUM(label IN ('retained','tradeoff')) FROM candidates c JOIN runs r USING(run_id) WHERE r.exp='phase3' AND c.verdict='proven' AND c.label IS NOT NULL").fetchone()
    p_ret = (rt[1] or 0) / rt[0] if rt[0] else 0.0
    return out, p_acc_m, p_ret, m3


def _spread_share(conn, floor_version):
    r = conn.execute("SELECT COUNT(DISTINCT design_id), SUM(floor_class IN ('spread','offset')) FROM (SELECT design_id, floor_class FROM noise_floor WHERE config='E4' AND metric='area' AND floor_version=? GROUP BY design_id)", (floor_version,)).fetchone()
    return (r[1] or 0) / r[0] if r and r[0] else 0.2


def _cand_dir_bytes(results, conn, tiers):
    """Per-candidate bytes in results/candidates (RTL + json vs the M6 workdir) and results/llm per call, by tier, from the Phase 4 B0 runs."""
    tier_of = {d: t for t, ds in tiers.items() for d in ds}
    acc = defaultdict(lambda: {"cands": 0, "rtl": 0, "m6": 0, "llm": 0, "calls": 0})
    for run_id, design, calls in conn.execute("SELECT run_id, design_id, llm_calls FROM runs WHERE exp='phase4' AND arm='B0'"):
        t = tier_of.get(design)
        d = results / "candidates" / run_id
        if not t or not d.exists():
            continue
        a = acc[t]
        for fpath, size in iter_files(str(d)):
            rel = os.path.relpath(fpath, d)
            if rel.startswith("m6_"):
                a["m6"] += size
            elif rel.endswith(".v"):
                a["rtl"] += size
                a["cands"] += 1
            else:
                a["rtl"] += size
        ld = results / "llm" / run_id
        if ld.exists():
            a["llm"] += walk_bytes(str(ld))[0]
            a["calls"] += int(calls or 0)
    return {t: {"rtl": v["rtl"] / max(v["cands"], 1), "m6": v["m6"] / max(v["cands"], 1), "llm": v["llm"] / max(v["calls"], 1), "cands": v["cands"]} for t, v in acc.items()}


def project(args):
    cfg = load_config()
    results = Path(cfg["project"]["results_dir"])
    m = json.loads(Path(args.measured).read_text())
    tiers = cfg["exp5"]["projection_reference_tiers"]
    sizes = Sizes(m["per_record"], tiers)
    conn = sqlite3.connect(f"file:{results / 'db' / 'results.sqlite'}?mode=ro", uri=True)
    rates, p_acc_m, p_ret_m, m3 = _rates(conn, tiers)
    p_spread = _spread_share(conn, cfg["noise"].get("floor_version"))
    cand_bytes = _cand_dir_bytes(results, conn, tiers)
    scale = cfg["scale"]
    arms = list(scale["arms"])
    seeds = int(scale["seeds"])
    calls_per_run = int(scale["budget"]["llm_calls_per_run"])
    second = cfg["llm"].get("second_model") or {}
    sky = scale.get("cktevo_sky130_subexp") or {}
    probe = cfg["exp5"]["correctness_probe"]
    n_env = int(cfg["search"]["acceptance_envelope"]["n_perturbations"])
    hidden_cfgs = [n for n, c in cfg["configs"].items() if isinstance(c, dict) and c.get("hidden")]
    rej_sample = 0.10                                    # spec 06 §3: a random 10 % of visible-layer rejected candidates run the hidden layer
    large_proven = float(args.large_proven_rate)         # assumption for the models that carry the large tier (luna proved 0 there)

    # ---- workload: runs and calls by tier and arm family
    tier_n = cfg["exp5"]["tiers"]                        # starting points per tier
    fam = {"B0": "B0", "B1_E4": "B", "B2": "B", "M": "M", "DrRTL_reimpl": "B"}
    work = defaultdict(int)                              # (tier, family, model) -> calls
    for t, n in tier_n.items():
        for arm in arms:
            work[(t, fam.get(arm, "B"), "main")] += n * seeds * calls_per_run
        for arm in second.get("arms") or []:
            work[(t, fam.get(arm, "B"), "second")] += n * seeds * calls_per_run
    sky_tiers = {"medium": 5, "large": 3}                # cktevo_sky130 modules by E4 cell count (5 below 1k cells, hsm / sdc_controller / spikeLayer8_H7 above)
    for t, n in sky_tiers.items():
        for arm in sky.get("arms") or []:
            work[(t, fam.get(arm, "B"), "sky130")] += n * int(sky.get("seeds") or 1) * calls_per_run
    work[("large", "B", "probe")] += len(probe["models"]) * len(probe["designs"]) * int(probe["seeds"]) * int(probe["K"]) * int(probe["N"])

    # ---- per-call footprint by tier and family, under the current rules (A) and the tiered policy (B)
    def per_call(t, family, model):
        r = rates[t]
        v = dict(r["verdicts"])
        if t == "large" and model in ("second", "probe", "sky130") and v["proven"] == 0:
            # the models that carry the large tier: assumed proven rate, taken from the mismatch / counterexample share
            v["proven"] = large_proven
            s = sum(v[k] for k in ("sim_fail", "falsified", "rejected", "inconclusive")) or 1.0
            for k in ("sim_fail", "falsified", "rejected", "inconclusive"):
                v[k] *= (1 - large_proven) / s
        p_dup = r["p_dup"]
        p_acc = p_acc_m if family == "M" else (r["p_acc_b"] if r["p_acc_b"] is not None else rates["medium"]["p_acc_b"])
        p_prov = v["proven"]
        fit_cfg = "Y" if family == "B0" else "E4"
        fit_kind = "yosys" if family == "B0" else "dc"
        full = {"eq": 0.0, "eq_slim": 0.0}
        for verdict, p in v.items():
            b, _ = sizes.mean(t, "eq", "EQ", verdict)
            bs, _ = sizes.mean(t, "eq", "EQ", verdict, keep=EQ_KEEP_SLIM)
            full["eq"] += (1 - p_dup) * p * b
            full["eq_slim"] += (1 - p_dup) * p * bs
        e4, _ = sizes.mean(t, "dc", "E4", "ok")
        e4s, _ = sizes.mean(t, "dc", "E4", "ok", keep=DC_KEEP_SLIM)
        fit, _ = sizes.mean(t, fit_kind, fit_cfg, "ok")
        fits, _ = sizes.mean(t, fit_kind, fit_cfg, "ok", keep=DC_KEEP_SLIM)
        k7, _ = sizes.mean(t, "dc", "K_asap7", "ok")
        k130, _ = sizes.mean(t, "dc", "K_sky130hd", "ok")
        hidden_full = 0.0
        for h in hidden_cfgs:
            hidden_full += {"H2a": k7, "H2b": k130, "H4": PT_RECORD_BYTES}.get(h, e4)
        h_e4only = sum(e4 for h in hidden_cfgs if h in ("H1", "H3", "H5"))
        ladder = sum(sizes.mean(t, "dc", c, "ok")[0] for c in LADDER_DC) + sum(sizes.mean(t, "yosys", c, "ok")[0] for c in LADDER_YOSYS)
        env = (p_prov * p_spread * p_ret_m * n_env * e4) if family == "M" else 0.0
        env_slim = (p_prov * p_spread * p_ret_m * n_env * e4s) if family == "M" else 0.0
        cb = cand_bytes.get(t) or cand_bytes["medium"]
        p_keep = p_prov * (p_acc + (1 - p_acc) * rej_sample)      # full artifacts: accepted candidates and the hidden-layer audit sample
        jobs = (1 - p_dup) + p_prov * (1 + len(hidden_cfgs) * (p_acc + (1 - p_acc) * rej_sample)) + (env / e4 if e4 else 0)
        common = cb["rtl"] + cb["llm"] + jobs * QUEUE_BYTES_PER_JOB + DB_BYTES_PER_CAND + jobs * DB_BYTES_PER_EVAL
        A = {"candidates_dir": cb["rtl"] + cb["m6"], "llm": cb["llm"], "eq": full["eq"], "fitness": p_prov * fit,
             "envelope": env, "hidden": p_prov * (p_acc + (1 - p_acc) * rej_sample) * hidden_full,
             "queue_db": jobs * (QUEUE_BYTES_PER_JOB + DB_BYTES_PER_EVAL) + DB_BYTES_PER_CAND}
        B = {"candidates_dir": cb["rtl"], "llm": cb["llm"],
             "eq": (1 - p_keep) * full["eq_slim"] + p_keep * full["eq"],
             "fitness": p_prov * ((p_acc + (1 - p_acc) * rej_sample) * fit + (1 - p_acc - (1 - p_acc) * rej_sample) * fits),
             "envelope": env_slim, "hidden": A["hidden"], "queue_db": A["queue_db"]}
        extras = {"hidden_all_e4": p_prov * (1 - p_acc) * (1 - rej_sample) * h_e4only,     # deferred question of PLAN Phase 5: H1 / H3 / H5 on every E4-evaluated candidate
                  "ladder_accepted": p_prov * p_acc * ladder}                              # the Phase 4 ladder repeated on the accepted candidates (final map, PLAN 6.2)
        return A, B, extras, {"p_dup": p_dup, "p_proven": p_prov, "p_acc": p_acc, "verdicts": v, "e4": e4, "e4_slim": e4s, "hidden_full": hidden_full, "ladder": ladder, "m6": cb["m6"], "llm": cb["llm"], "common": common}

    rows, totA, totB, totX = [], defaultdict(float), defaultdict(float), defaultdict(float)
    detail = {}
    for (t, family, model), calls in sorted(work.items()):
        A, B, X, info = per_call(t, family, model)
        detail[(t, family, model)] = info
        a, b = sum(A.values()), sum(B.values())
        rows.append((t, family, model, calls, a, b, X["hidden_all_e4"], X["ladder_accepted"], info))
        for k, vv in A.items():
            totA[k] += vv * calls
        for k, vv in B.items():
            totB[k] += vv * calls
        for k, vv in X.items():
            totX[k] += vv * calls
    total_calls = sum(work.values())

    # ---- existing footprint and the retroactive application of the tiered policy to Phase 3 / 4 records
    kept_ids = {r[0] for r in conn.execute("SELECT cand_id FROM candidates WHERE accepted=1 OR in_archive=1")}
    kept_ids |= {r[0] for r in conn.execute("SELECT c.cand_id FROM candidates c JOIN runs r USING(run_id) WHERE r.arm='literature'")}
    retro = defaultdict(float)
    for r in m["per_record"]:
        cats = r.get("cats") or {}
        if r["obj"] != "cand" or not r.get("cand_id") or r["cand_id"] in kept_ids or r["status"] in ("failed", "eval_failed", "error", "timeout"):
            continue
        keep = EQ_KEEP_SLIM if r["kind"] == "eq" else DC_KEEP_SLIM
        prunable = sum(b for c, b in cats.items() if c not in keep)
        retro[r["kind"] + "_" + (r["status"] if r["kind"] == "eq" else "records")] += prunable
    m6_bytes = sum(v["bytes"] for k, v in m["candidates_by_suffix"].items() if "/" in k)
    raw_total = sum(b["bytes"] for b in m["bytes"])
    other = m["other_dirs"]
    retro_total = sum(retro.values()) + m6_bytes

    # ---- report
    L = []
    L.append("# Phase 5 storage footprint (G5 decisions item 5; generated by scripts/phase5_footprint.py project)\n")
    L.append(f"Measured on {m.get('measured_at', 'the measurement file')} from {len(m['per_record'])} record directories under results/raw (apparent bytes; the hidden tree never read, its size is the difference between `du results/` and the visible subtrees).\n")
    L.append("## 1. Existing footprint (apparent bytes)\n")
    L.append("| Tree | GB | Note |\n|---|---|---|")
    L.append(f"| results/raw | {_gb(raw_total):.1f} | {len(m['per_record'])} records: equivalence {sum(b['bytes'] for b in m['bytes'] if b['kind']=='eq') / 1e9:.1f} GB, DC {sum(b['bytes'] for b in m['bytes'] if b['kind']=='dc') / 1e9:.1f} GB, Yosys {sum(b['bytes'] for b in m['bytes'] if b['kind']=='yosys') / 1e9:.1f} GB |")
    L.append(f"| results/candidates | {_gb(other['candidates']['bytes']):.1f} | of which M6 classifier workdirs (Yosys stats of C and of D per candidate, regenerable) {_gb(m6_bytes):.1f} GB |")
    for k in ("llm", "queue", "db", "snapshots", "scratch"):
        if k in other:
            L.append(f"| results/{k} | {_gb(other[k]['bytes']):.2f} | |")
    L.append("")
    L.append("## 2. Measured record sizes by tier (MB per record, mean; the reference designs of `exp5.projection_reference_tiers`)\n")
    L.append("| Tier | EQ proven | EQ sim_fail | EQ falsified | EQ inconclusive | EQ rejected | EQ slim (proven / sim_fail) | E4 record | E4 slim | K_asap7 | K_sky130hd | Y | ladder (5 DC + 5 Yosys) | M6 workdir per candidate | LLM log per call |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for t in ("small", "medium", "large"):
        f = lambda kind, c, s, keep=None: sizes.mean(t, kind, c, s, keep=keep)[0] / 1e6
        cb = cand_bytes.get(t) or {"m6": 0, "llm": 0}
        lad = sum(sizes.mean(t, "dc", c, "ok")[0] for c in LADDER_DC) + sum(sizes.mean(t, "yosys", c, "ok")[0] for c in LADDER_YOSYS)
        L.append(f"| {t} | {f('eq','EQ','proven'):.1f} | {f('eq','EQ','sim_fail'):.1f} | {f('eq','EQ','falsified'):.1f} | {f('eq','EQ','inconclusive'):.1f} | {f('eq','EQ','rejected'):.2f} | {f('eq','EQ','proven',EQ_KEEP_SLIM):.2f} / {f('eq','EQ','sim_fail',EQ_KEEP_SLIM):.2f} | {f('dc','E4','ok'):.2f} | {f('dc','E4','ok',DC_KEEP_SLIM):.2f} | {f('dc','K_asap7','ok'):.2f} | {f('dc','K_sky130hd','ok'):.2f} | {f('yosys','Y','ok'):.2f} | {lad / 1e6:.1f} | {cb['m6'] / 1e6:.2f} | {cb['llm'] / 1e6:.3f} |")
    L.append("\nFallbacks: a (tier, verdict) cell without records takes the medium tier's value (small-tier falsified / inconclusive; large-tier E4 candidate records take the perturbation records of the same designs).\n")
    L.append("## 3. Rates used (Phase 4 B0 by tier; Phase 3 M for the acceptance of arm M)\n")
    L.append("| Tier | candidates | duplicate (no evaluation) | proven | sim_fail | falsified | rejected | inconclusive | accepted of proven (B arms) |\n|---|---|---|---|---|---|---|---|---|")
    for t in ("small", "medium", "large"):
        r = rates[t]
        v = r["verdicts"]
        L.append(f"| {t} | {r['n']} | {100 * r['p_dup']:.0f} % | {100 * v['proven']:.0f} % | {100 * v['sim_fail']:.0f} % | {100 * v['falsified']:.0f} % | {100 * v['rejected']:.0f} % | {100 * v['inconclusive']:.0f} % | {'-' if r['p_acc_b'] is None else f'{100 * r[chr(112) + chr(95) + chr(97) + chr(99) + chr(99) + chr(95) + chr(98)]:.0f} %'} |")
    L.append(f"\nArm M accepts {100 * p_acc_m:.0f} % of its proven candidates (Phase 3, {m3[0]} proven; retained or trade-off {100 * p_ret_m:.0f} %); spread / offset designs are {100 * p_spread:.0f} % of the designs with an E4 floor, and only their retained / trade-off M candidates get the {n_env} envelope runs. The large tier's proven rate for the models of the correctness probe and the second model is an assumption: {100 * large_proven:.0f} % (luna proved 0 of 562; `--large-proven-rate`). Hidden layer per accepted candidate: {', '.join(hidden_cfgs)} plus a {100 * rej_sample:.0f} % sample of the rejected proven candidates (spec 06 §3). Prescreen not applied (upper bound).\n")
    L.append("## 4. Workload (G5: 30 starting points = 18 medium / 6 small / 6 large; 5 arms × 3 seeds with luna; terra on M and B2; Sky130 sub-experiment 8 modules × 2 arms; correctness probe)\n")
    L.append("| Tier | arm family | runs of | LLM calls | MB per call, current rules | MB per call, tiered policy | GB current | GB tiered | + H1/H3/H5 on all E4-evaluated (GB) | + ladder on accepted (GB) |\n|---|---|---|---|---|---|---|---|---|---|")
    for t, family, model, calls, a, b, x1, x2, info in rows:
        L.append(f"| {t} | {family} | {model} | {calls} | {a / 1e6:.1f} | {b / 1e6:.2f} | {_gb(a * calls):.1f} | {_gb(b * calls):.1f} | {_gb(x1 * calls):.1f} | {_gb(x2 * calls):.1f} |")
    A_total, B_total = sum(totA.values()), sum(totB.values())
    L.append(f"| **total** | | | **{total_calls}** | | | **{_gb(A_total):.0f}** | **{_gb(B_total):.1f}** | {_gb(totX['hidden_all_e4']):.1f} | {_gb(totX['ladder_accepted']):.1f} |")
    L.append("\nComponents of the totals (GB):\n")
    L.append("| Component | current rules | tiered policy |\n|---|---|---|")
    for k in ("eq", "candidates_dir", "fitness", "hidden", "envelope", "llm", "queue_db"):
        L.append(f"| {k} | {_gb(totA[k]):.1f} | {_gb(totB[k]):.1f} |")
    L.append("\n## 5. Retroactive application of the tiered policy to the Phase 3 / Phase 4 records (regenerable artifacts of non-accepted candidates; records, accepted candidates, literature objects, perturbations and failed records untouched)\n")
    L.append("| What | GB freed |\n|---|---|")
    for k, v in sorted(retro.items(), key=lambda kv: -kv[1]):
        L.append(f"| {k} | {_gb(v):.1f} |")
    L.append(f"| M6 workdirs under results/candidates | {_gb(m6_bytes):.1f} |")
    L.append(f"| **total** | **{_gb(retro_total):.1f}** |")
    L.append("")
    L.append("## 6. Free space required\n")
    import shutil as _sh
    free_root = _sh.disk_usage(str(results)).free
    L.append(f"Root filesystem free now: {free_root / 1e9:.1f} GB. /hdd1 free: {_sh.disk_usage('/hdd1').free / 1e9:.1f} GB.\n")
    margin = 1.25
    L.append(f"| Scenario | projected growth (GB) | with a 25 % margin (GB) | fits in {free_root / 1e9:.0f} GB? | fits after the retroactive prune (+{_gb(retro_total):.0f} GB)? | fits after freeing ~/.cache (+63 GB)? |\n|---|---|---|---|---|---|")
    for name, g in (("current rules", A_total), ("tiered policy", B_total), ("tiered + H1/H3/H5 on all E4-evaluated", B_total + totX["hidden_all_e4"]), ("tiered + ladder on accepted", B_total + totX["ladder_accepted"]), ("tiered + both", B_total + totX["hidden_all_e4"] + totX["ladder_accepted"])):
        need = g * margin
        L.append(f"| {name} | {_gb(g):.0f} | {_gb(need):.0f} | {'yes' if need < free_root else 'no'} | {'yes' if need < free_root + retro_total else 'no'} | {'yes' if need < free_root + retro_total + 63e9 else 'no'} |")
    L.append("")
    out = Path(args.out)
    out.write_text("\n".join(L) + "\n")
    if not getattr(args, "quiet", True):
        print("\n".join(L))
        print(f"written {out}")
    return {"current": A_total, "tiered": B_total, "hidden_all_e4": totX["hidden_all_e4"], "ladder_accepted": totX["ladder_accepted"], "retro": retro_total}


def _add_project(sub):
    s = sub.add_parser("project")
    s.add_argument("--measured", default=str(ROOT / "reports/data/phase5_footprint_measured.json"))
    s.add_argument("--out", default=str(ROOT / "reports/data/phase5_footprint.md"))
    s.add_argument("--large-proven-rate", default=0.10, type=float, help="assumed proven rate of the large tier for the probe / second models (luna: 0)")
    s.add_argument("--quiet", action="store_true")
    s.set_defaults(fn=lambda a: (project(a) and 0))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("measure")
    s.add_argument("--out", default=str(ROOT / "reports/data/phase5_footprint_measured.json"))
    s.set_defaults(fn=measure)
    s = sub.add_parser("summarize")
    s.add_argument("--measured", default=str(ROOT / "reports/data/phase5_footprint_measured.json"))
    s.set_defaults(fn=summarize)
    _add_project(sub)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
