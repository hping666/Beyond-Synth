"""SAIF activity for the noise runs (spec 02 §3–§4, spec 03): every design D and every usable perturbation gets a
SAIF file from the lock-step VCD of its equivalence record (vcd2saif, instance bs_lockstep/u_d for D from the
round-trip run, bs_lockstep/u_c for a perturbation), stored under data/perturbations/<design_id>/saif/ with a
saif.json manifest; the noise DC jobs pass them as `saif` / `saif_instance` so that power_saif_mw exists for the
power floor. After the SAIF exists the VCD and the VCS build of that record are scratch (config
`retention.prune_eq_scratch_after_saif`): reproducible from the recorded random seed."""
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src import config as C
from src.equiv.saif import vcd_to_saif
from src.noise import gate as GT
from src.noise import generate as G

D_INSTANCE = "bs_lockstep/u_d"
C_INSTANCE = "bs_lockstep/u_c"
EQ_SCRATCH = ("csrc", "simv.daidir")
EQ_SCRATCH_FILES = ("simv", "sim.vcd", "ucli.key")


def latest_records(cfg, design_id):
    """cand_id -> latest equiv record (with its directory), like the gate collector."""
    raw = Path(C.results_dir(cfg)) / "raw" / design_id / "EQ"
    by = {}
    for eq in raw.glob("*/equiv.json"):
        try:
            rec = json.loads(eq.read_text())
        except json.JSONDecodeError:
            continue
        rec["_dir"] = str(eq.parent)
        cid = rec.get("cand_id")
        if cid:
            by.setdefault(cid, []).append((eq.stat().st_mtime, rec))
    return {cid: sorted(v)[-1][1] for cid, v in by.items()}


def proven_ids(conn, design_id):
    return {r[0] for r in conn.execute("SELECT pert_id FROM perturbations WHERE design_id=? AND seq_status IN ('proven','proven_rename')", (design_id,))}


def build_for_design(design, proven, cfg, out_root=None, convert=vcd_to_saif):
    """proven: pert_ids with a proven / proven_rename verdict (proven_ids); -> saif.json dict
    {'design': {saif, instance, source_record}, 'perturbations': {pert_id: {...}}, 'missing': [...]}."""
    did = design["design_id"]
    m = GT.manifest_of(did)
    out = Path(out_root or G.PERT_DIR) / did / "saif"
    out.mkdir(parents=True, exist_ok=True)
    recs = latest_records(cfg, did)
    result = {"design_id": did, "design": None, "perturbations": {}, "missing": []}
    entries = []
    if m and m.get("roundtrip"):
        entries.append(("design", m["roundtrip"]["pert_id"], D_INSTANCE, out / "D.saif"))
    for pid in sorted(proven):
        entries.append((pid, pid, C_INSTANCE, out / f"{pid}.saif"))
    for key, cid, instance, path in entries:
        rec = recs.get(cid)
        vcd = rec.get("vcd_path") if rec else None
        if path.exists() and path.stat().st_size > 0:
            info = {"saif": str(path), "instance": instance, "source_record": rec.get("_dir") if rec else None, "status": "exists"}
        elif vcd and Path(vcd).exists():
            r = convert(vcd, path, instance, cfg)
            info = {"saif": r.get("saif"), "instance": instance, "source_record": rec["_dir"], "status": r["status"]}
        else:
            info = {"saif": None, "instance": instance, "source_record": rec.get("_dir") if rec else None, "status": "no_vcd"}
            result["missing"].append(key)
        if key == "design":
            result["design"] = info
        else:
            result["perturbations"][key] = info
    (out.parent / "saif.json").write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    return result


def load_saif(design_id, root=None):
    p = Path(root or G.PERT_DIR) / design_id / "saif.json"
    return json.loads(p.read_text()) if p.exists() else None


def prune_eq_scratch(cfg, design_id):
    """Remove the scratch of the equivalence records of one design whose SAIF exists: the VCS build (csrc/, simv,
    simv.daidir/) under retention.prune_eq_build_after_saif, the lock-step VCD only under
    retention.prune_eq_vcd_after_saif (off until the user decides). -> bytes freed."""
    ret = cfg.get("retention") or {}
    prune_build = bool(ret.get("prune_eq_build_after_saif", False))
    prune_vcd = bool(ret.get("prune_eq_vcd_after_saif", False))
    if not (prune_build or prune_vcd):
        return 0
    have = set()
    s = load_saif(design_id)
    if s:
        for info in [s.get("design") or {}] + list((s.get("perturbations") or {}).values()):
            if info.get("saif") and info.get("source_record"):
                have.add(info["source_record"])
    freed = 0
    raw = Path(C.results_dir(cfg)) / "raw" / design_id / "EQ"
    for d in raw.glob("*"):
        if not d.is_dir():
            continue
        sim = d / "v2_sim"
        if not sim.is_dir() or str(d) not in have:
            continue
        if prune_build:
            for name in EQ_SCRATCH:
                p = sim / name
                if p.is_dir():
                    freed += sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                    shutil.rmtree(p, ignore_errors=True)
        for name in EQ_SCRATCH_FILES:
            p = sim / name
            if p.is_file() and ((name == "sim.vcd" and prune_vcd) or (name != "sim.vcd" and prune_build)):
                freed += p.stat().st_size
                p.unlink()
    return freed


def build_all(designs, conn, cfg, workers=8, log=print):
    proven = {d["design_id"]: proven_ids(conn, d["design_id"]) for d in designs}  # SQLite: main thread only

    def one(d):
        try:
            return d["design_id"], build_for_design(d, proven[d["design_id"]], cfg)
        except Exception as e:
            return d["design_id"], {"error": f"{type(e).__name__}: {e}"}
    out = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for did, r in ex.map(one, designs):
            out[did] = r
            n = len(r.get("perturbations") or {})
            log(f"{did:45s} D={'ok' if (r.get('design') or {}).get('saif') else '-'} perturbations={n} missing={len(r.get('missing') or [])} {r.get('error') or ''}")
    return out
