"""SAIF activity for the noise runs (spec 02 §3–§4, spec 03): every design D and every usable perturbation gets a
SAIF file from the lock-step VCD of its equivalence record (vcd2saif, instance bs_lockstep/u_d for D from the
round-trip run, bs_lockstep/u_c for a perturbation), stored under data/perturbations/<design_id>/saif/ with a
saif.json manifest; the noise DC jobs pass them as `saif` / `saif_instance` so that power_saif_mw exists for the
power floor. After the SAIF exists the VCD and the VCS build of that record are scratch (config
`retention.prune_eq_scratch_after_saif`): reproducible from the recorded random seed."""
import datetime
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src import config as C
from src.equiv.saif import C_INSTANCE, D_INSTANCE, keep_vcd, vcd_to_saif
from src.noise import gate as GT
from src.noise import generate as G

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
        local = (rec or {}).get("saif_d" if instance == D_INSTANCE else "saif_c")  # written by the stack itself since 2026-09-14
        if path.exists() and path.stat().st_size > 0:
            info = {"saif": str(path), "instance": instance, "source_record": rec.get("_dir") if rec else None, "status": "exists"}
        elif local and Path(local).exists() and Path(local).stat().st_size > 0:
            shutil.copyfile(local, path)
            info = {"saif": str(path), "instance": instance, "source_record": rec["_dir"], "status": "copied"}
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


def power_ingested(conn, design_id, cand_id, roundtrip_id):
    """True when an ok evaluation with SAIF power exists for the record's role: D (the round-trip record) or the perturbation."""
    if conn is None:
        return False
    if cand_id == roundtrip_id:
        q = "SELECT 1 FROM evaluations WHERE design_id=? AND is_baseline=1 AND status='ok' AND power_saif_mw IS NOT NULL LIMIT 1"
        return conn.execute(q, (design_id,)).fetchone() is not None
    q = "SELECT 1 FROM evaluations WHERE design_id=? AND pert_id=? AND status='ok' AND power_saif_mw IS NOT NULL LIMIT 1"
    return conn.execute(q, (design_id, cand_id)).fetchone() is not None


def prune_eq_scratch(cfg, design_id, conn=None):
    """Remove the scratch of the equivalence records of one design whose SAIF exists: the VCS build (csrc/, simv,
    simv.daidir/) under retention.prune_eq_build_after_saif; the lock-step VCD under retention.prune_eq_vcd_after_saif
    only when power was ingested from that SAIF (status ok, needs conn) and the record is not kept by keep_vcd
    (sim_fail / falsified verdicts, 2 % sample; DECISIONS 2026-09-14). -> bytes freed."""
    ret = cfg.get("retention") or {}
    prune_build = bool(ret.get("prune_eq_build_after_saif", False))
    prune_vcd = bool(ret.get("prune_eq_vcd_after_saif", False))
    if not (prune_build or prune_vcd):
        return 0
    m = GT.manifest_of(design_id)
    roundtrip_id = (m or {}).get("roundtrip", {}).get("pert_id")
    verdict_of = {}
    for eq in (Path(C.results_dir(cfg)) / "raw" / design_id / "EQ").glob("*/equiv.json"):
        try:
            r = json.loads(eq.read_text())
        except json.JSONDecodeError:
            continue
        verdict_of[str(eq.parent)] = (r.get("verdict"), r.get("cand_id"))
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
        verdict, cid = verdict_of.get(str(d), (None, None))
        vcd_ok = prune_vcd and power_ingested(conn, design_id, cid, roundtrip_id) and not keep_vcd(cfg, d, verdict)
        for name in EQ_SCRATCH_FILES:
            p = sim / name
            if p.is_file() and ((name == "sim.vcd" and vcd_ok) or (name != "sim.vcd" and prune_build)):
                freed += p.stat().st_size
                p.unlink()
    return freed


PROVEN = ("proven", "proven_sim_only")


def prune_nonproven_scratch(cfg, design_id, log=None):
    """Retention of 2026-09-14 (user decision, DECISIONS): for the equivalence records of one design that are NOT proven —
    the VCD of a `falsified` record is deleted (no mismatch in it; the SEQ counterexample is the evidence), the VCD of a
    kept verdict (`retention.vcd_keep_verdicts`, sim_fail) is gzip-compressed when `retention.vcd_compress_kept`, and the
    VCS build (csrc/, simv, simv.daidir/) of every non-proven record is removed when `retention.prune_eq_build_nonproven`.
    Every other file stays; equiv.json records what happened (vcd_deleted / vcd_deleted_reason / vcd_compressed / vcd_path).
    -> {"freed": bytes, "vcd_deleted": n, "vcd_compressed": n, "builds": n}"""
    from src.equiv.saif import compress_vcd
    ret = cfg.get("retention") or {}
    keep = set(ret.get("vcd_keep_verdicts") or [])
    compress = bool(ret.get("vcd_compress_kept", False))
    prune_build = bool(ret.get("prune_eq_build_nonproven", False))
    out = {"freed": 0, "vcd_deleted": 0, "vcd_compressed": 0, "builds": 0}
    raw = Path(C.results_dir(cfg)) / "raw" / design_id / "EQ"
    if not raw.is_dir():
        return out
    for eq in raw.glob("*/equiv.json"):
        try:
            rec = json.loads(eq.read_text())
        except json.JSONDecodeError:
            continue
        verdict = rec.get("verdict")
        if verdict in PROVEN or not verdict:
            continue   # proven records follow the SAIF-and-power rule; records without a verdict are still running
        d = eq.parent
        changed = False
        vcds = [p for p in d.rglob("*.vcd") if p.is_file()]
        if verdict not in keep and verdict == "falsified":
            for p in vcds:
                out["freed"] += p.stat().st_size
                p.unlink()
                out["vcd_deleted"] += 1
                changed = True
            if vcds:
                rec.update(vcd_path=None, vcd_deleted=True, vcd_deleted_reason="falsified: the lock-step VCD holds no mismatch, the SEQ counterexample is the evidence (DECISIONS 2026-09-14)")
        elif verdict in keep and compress:
            for p in vcds:
                before = p.stat().st_size
                gz = compress_vcd(p)
                out["freed"] += before - gz.stat().st_size
                out["vcd_compressed"] += 1
                changed = True
                if rec.get("vcd_path") == str(p) or len(vcds) == 1:
                    rec["vcd_path"] = str(gz)
                rec["vcd_compressed"] = True
        if prune_build:
            for p in list(d.rglob("csrc")) + list(d.rglob("simv.daidir")):
                if p.is_dir():
                    out["freed"] += sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                    shutil.rmtree(p, ignore_errors=True)
                    out["builds"] += 1
                    changed = True
            for p in d.rglob("simv"):
                if p.is_file():
                    out["freed"] += p.stat().st_size
                    p.unlink()
                    changed = True
        if changed:
            rec.setdefault("retention_log", []).append({"at": datetime.datetime.now().isoformat(timespec="seconds"), "rule": "nonproven_scratch_2026-09-14"})
            eq.write_text(json.dumps(rec, indent=1, default=str))
    if log and any(out[k] for k in ("vcd_deleted", "vcd_compressed", "builds")):
        log(f"{design_id}: freed {out['freed'] / 1e9:.2f} GB (vcd deleted {out['vcd_deleted']}, compressed {out['vcd_compressed']}, builds {out['builds']})")
    return out


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
