"""Equivalence gate for perturbations (docs/spec/02-noise-floor.md §2): every generated perturbation (and the
round-trip re-print it inherits from) must be proven equivalent to the original by V1 + V2 + V3 (SEQ) before it
enters the noise floor; V4 is not used here. The checks run as `vcf` queue jobs (src/equiv/run_equiv.py) whose
records land in results/raw/<design_id>/EQ/<hash>/equiv.json; collect() reads those records and fills the
`perturbations` table (seq_status = proven / falsified / inconclusive / error / rejected / sim_fail / pending).
The generator's non-equivalence rate is itself a reported number."""
import json
import re
from pathlib import Path

from src import config as C
from src.db import core as db
from src.designs import catalog as K
from src.noise import generate as G


def manifest_of(design_id, root=None):
    p = Path(root or G.PERT_DIR) / design_id / "manifest.json"
    return json.loads(p.read_text()) if p.exists() else None


def gate_jobs(design, manifest, cfg, priority=0):
    """One vcf job per perturbation plus one for the round trip; the perturbation is the 'candidate' side."""
    d_rtl = [str(p) for p in K.abs_paths(design, design["files"])]
    incdirs = [str(p) for p in K.abs_paths(design, design["incdirs"])]
    common = {"design_id": design["design_id"], "d_rtl": d_rtl, "top": design["top"],
              "clk": (design["clk_ports"] or [None])[0], "rst": design.get("rst_port"), "rst_sense": design.get("rst_sense"),
              "sverilog": bool(design["sverilog"]), "incdirs": incdirs}
    jobs = []
    entries = []
    if manifest.get("roundtrip"):
        entries.append({"pert_id": manifest["roundtrip"]["pert_id"], "path": manifest["roundtrip"]["path"], "ptype": "P0_roundtrip"})
    entries += manifest.get("perturbations") or []
    for e in entries:
        payload = dict(common, cand_id=e["pert_id"], c_rtl=[str(Path(C.ROOT) / p) for p in (e.get("paths") or [e["path"]])], note=f"perturbation {e['ptype']}")
        jobs.append({"kind": "vcf", "design_id": design["design_id"], "cand_id": e["pert_id"], "config": "EQ",
                     "priority": int(priority), "payload": payload})
    return jobs


def recorded_cand_ids(cfg, design_id):
    """cand_ids that already have an equivalence record (any verdict) under results/raw/<design_id>/EQ/."""
    raw = Path(C.results_dir(cfg)) / "raw" / design_id / "EQ"
    ids = set()
    for eq in raw.glob("*/equiv.json"):
        try:
            cid = json.loads(eq.read_text()).get("cand_id")
        except json.JSONDecodeError:
            continue
        if cid:
            ids.add(cid)
    return ids


def error_cand_ids(cfg, design_id):
    """cand_ids whose latest equivalence record carries the verdict `error` (a tool failure: retried, never a verdict)."""
    latest = {}
    for eq in (Path(C.results_dir(cfg)) / "raw" / design_id / "EQ").glob("*/equiv.json"):
        try:
            rec = json.loads(eq.read_text())
        except json.JSONDecodeError:
            continue
        cid = rec.get("cand_id")
        if cid and (cid not in latest or eq.stat().st_mtime > latest[cid][0]):
            latest[cid] = (eq.stat().st_mtime, rec.get("verdict"))
    return {cid for cid, (_, v) in latest.items() if v == "error"}


def _verdict(rec):
    """The stack's verdict (spec 03 vocabulary): proven / falsified / inconclusive / rejected / sim_fail /
    proven_sim_only / error; only `proven` (SEQ) admits a perturbation into the noise floor."""
    v = rec.get("verdict")
    if v:
        return str(v)
    for key in ("v3_status", "v2_status", "v1_status"):
        if rec.get(key):
            return str(rec[key])
    return "unknown"


def rename_is_alpha(manifest, entry, root=None):
    """A P1 perturbation is a pure alpha-renaming when substituting every new name back gives the round trip text
    byte for byte; together with a SEQ-proven round trip that is a proof of equivalence that does not depend on
    VC Formal's name-based register matching (which fails for renamed registers without reset, DECISIONS 2026-09-12)."""
    if entry.get("ptype") != "P1_rename" or not manifest.get("roundtrip"):
        return False
    base = Path(root or C.ROOT)
    try:
        text = (base / entry["path"]).read_text() if not Path(entry["path"]).is_absolute() else Path(entry["path"]).read_text()
        rt = (base / manifest["roundtrip"]["path"]).read_text() if not Path(manifest["roundtrip"]["path"]).is_absolute() else Path(manifest["roundtrip"]["path"]).read_text()
    except OSError:
        return False
    back = text
    for mapping in ((entry.get("details") or {}).get("renamed") or {}).values():
        for old_name, new_name in mapping.items():
            back = re.sub(rf"(?<![A-Za-z_0-9$]){re.escape(new_name)}(?![A-Za-z_0-9$])", old_name, back)
    # the re-printer wraps lines by identifier length, so only the token stream is compared (whitespace-insensitive)
    squash = lambda s: re.sub(r"\s+", " ", s).strip()
    return squash(back) == squash(rt)


def collect(conn, cfg, designs=None, root=None):
    """Read every equiv.json of the perturbation gate and upsert the perturbations table; -> summary per design."""
    raw = Path(C.results_dir(cfg)) / "raw"
    summary = {}
    for d in designs or K.load_all():
        m = manifest_of(d["design_id"], root)
        if not m:
            continue
        entries = ([dict(m["roundtrip"], ptype="P0_roundtrip")] if m.get("roundtrip") else []) + (m.get("perturbations") or [])
        by_cand = {}
        for eq in (raw / d["design_id"] / "EQ").glob("*/equiv.json"):
            try:
                rec = json.loads(eq.read_text())
            except json.JSONDecodeError:
                continue
            cid = rec.get("cand_id")
            if cid:
                by_cand.setdefault(cid, []).append((eq.stat().st_mtime, rec))
        counts = {}
        rt_recs = sorted(by_cand.get(m["roundtrip"]["pert_id"], [])) if m.get("roundtrip") else []
        rt_status = _verdict(rt_recs[-1][1]) if rt_recs else "pending"
        for e in entries:
            recs = sorted(by_cand.get(e["pert_id"], []))
            status = _verdict(recs[-1][1]) if recs else "pending"
            if e["ptype"] == "P0_roundtrip":
                summary.setdefault(d["design_id"], {})["roundtrip"] = status  # the re-print is recorded like any perturbation (DECISIONS 2026-09-13)
            elif status in ("falsified", "inconclusive", "error") and rt_status == "proven" and rename_is_alpha(m, e, root):
                status = "proven_rename"  # alpha-renaming of a SEQ-proven round trip (SEQ could not match the renamed state)
            counts[status] = counts.get(status, 0) + 1
            row = {"pert_id": e["pert_id"], "design_id": d["design_id"], "ptype": e["ptype"], "path": e["path"], "seq_status": status}
            row.update(db.stamp())
            cols = list(row)
            conn.execute(f"INSERT INTO perturbations ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)}) "
                         f"ON CONFLICT(pert_id) DO UPDATE SET seq_status=excluded.seq_status, git_sha=excluded.git_sha, cfg_hash=excluded.cfg_hash",
                         tuple(row.values()))
        summary.setdefault(d["design_id"], {})["counts"] = counts
    return summary
