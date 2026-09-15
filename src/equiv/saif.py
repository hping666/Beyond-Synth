"""VCD -> SAIF for the power path (docs/spec/01-eval-service.md §4) with Synopsys vcd2saif (ships with DC)."""
import hashlib
import subprocess
from pathlib import Path


def vcd_to_saif(vcd, saif, instance, cfg, timeout=600):
    """instance: hierarchical path of the DUT inside the VCD, e.g. bs_lockstep/u_d; the SAIF keeps that hierarchy
    and DC / PrimePower read it with read_saif -instance <same path>."""
    tool = cfg["tools"]["vcs"]["vcd2saif"]
    p = subprocess.run([tool, "-input", str(vcd), "-output", str(saif), "-instance", instance],
                       capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    ok = p.returncode == 0 and Path(saif).exists() and Path(saif).stat().st_size > 0
    return {"status": "ok" if ok else "failed", "instance": instance, "saif": str(saif) if ok else None,
            "log": (p.stdout + p.stderr)[-800:]}


D_INSTANCE = "bs_lockstep/u_d"
C_INSTANCE = "bs_lockstep/u_c"


def keep_vcd(cfg, record_dir, verdict):
    """Retention (DECISIONS 2026-09-14, operations 1): VCDs of sim_fail / falsified records are kept, plus a deterministic
    random sample (`retention.vcd_keep_sample_frac`, by record directory name); every other VCD is scratch once the SAIFs exist."""
    ret = cfg.get("retention") or {}
    if verdict in set(ret.get("vcd_keep_verdicts") or []):
        return True
    frac = float(ret.get("vcd_keep_sample_frac") or 0.0)
    h = int(hashlib.sha1(Path(record_dir).name.encode()).hexdigest()[:8], 16) % 10000
    return h < frac * 10000


def compress_vcd(path):
    """gzip a VCD in place (lossless; `gzip -6`, Python's gzip as the fallback) -> the .gz path; the original is removed."""
    path = Path(path)
    gz = path.with_suffix(path.suffix + ".gz")
    if gz.exists():
        if path.exists():
            path.unlink()
        return gz
    try:
        p = subprocess.run(["gzip", "-6", str(path)], capture_output=True, text=True, timeout=3600)
        if p.returncode == 0 and gz.exists():
            return gz
    except (OSError, subprocess.TimeoutExpired):
        pass
    import gzip
    import shutil
    with open(path, "rb") as src, gzip.open(gz, "wb", compresslevel=6) as dst:
        shutil.copyfileobj(src, dst)
    path.unlink()
    return gz


def finalize_vcd(job_dir, rec, cfg, convert=vcd_to_saif):
    """After the equivalence stack: turn the lock-step VCD into the two SAIFs of the record (saif_d.saif for D, saif_c.saif
    for the candidate) and delete the VCD unless keep_vcd says otherwise (`retention.vcd_to_scratch`). Updates rec in place:
    saif_d, saif_c, vcd_path (None once deleted), vcd_deleted."""
    if not (cfg.get("retention") or {}).get("vcd_to_scratch", False):
        return rec
    vcd = rec.get("vcd_path")
    if not vcd or not Path(vcd).exists():
        return rec
    job_dir = Path(job_dir)
    ok = True
    for key, inst, name in (("saif_d", D_INSTANCE, "saif_d.saif"), ("saif_c", C_INSTANCE, "saif_c.saif")):
        r = convert(vcd, job_dir / name, inst, cfg)
        rec[key] = r.get("saif")
        ok = ok and r.get("status") == "ok"
    if ok and not keep_vcd(cfg, job_dir, rec.get("verdict")):
        Path(vcd).unlink()
        rec["vcd_path"] = None
        rec["vcd_deleted"] = True
    else:
        rec["vcd_deleted"] = False
        if (cfg.get("retention") or {}).get("vcd_compress_kept", False) and Path(vcd).exists():   # 2026-09-14 (user): kept VCDs are stored gzip-compressed
            rec["vcd_path"] = str(compress_vcd(vcd))
            rec["vcd_compressed"] = True
    return rec


def retain_vcd(job_dir, rec, cfg):
    """Retention for a record that ends before the SAIF stage (a rejected / error / sim_fail verdict from V1 or V2): the
    candidate is never power-evaluated, so no SAIF is made; the VCD of a kept verdict (`retention.vcd_keep_verdicts`,
    sim_fail) is gzip-compressed when `retention.vcd_compress_kept`, a `falsified` VCD is deleted, every other VCD stays
    (`retention.keep_scratch_on_failure`). Same bookkeeping keys as finalize_vcd (vcd_path, vcd_deleted, vcd_compressed).
    Defect found 2026-09-15: sim_fail records returned before finalize_vcd and left their VCDs uncompressed (45 GB)."""
    ret = cfg.get("retention") or {}
    vcd = rec.get("vcd_path")
    if not vcd or not Path(vcd).exists():
        return rec
    keep = set(ret.get("vcd_keep_verdicts") or [])
    verdict = rec.get("verdict")
    if verdict == "falsified" and verdict not in keep:
        Path(vcd).unlink()
        rec.update(vcd_path=None, vcd_deleted=True)
    elif verdict in keep and ret.get("vcd_compress_kept", False):
        rec["vcd_deleted"] = False
        rec["vcd_path"] = str(compress_vcd(vcd))
        rec["vcd_compressed"] = True
    return rec
