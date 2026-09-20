"""Perturbation generation for one design (docs/spec/02-noise-floor.md §1): parse the staged RTL once, apply
`config: noise.n_per_type` perturbations per type, write them under data/perturbations/<design_id>/ with a
manifest (the round-trip re-print of the unmodified AST is written as well: the equivalence gate checks it first,
because every perturbation inherits the codegen's normalisation). Perturbation ids are content hashes."""
import hashlib
import json
from pathlib import Path

from src import config as C
from src.designs import catalog as K
from src.noise import perturb as P
from src.noise import vast as V

PERT_DIR = Path(C.ROOT) / "data" / "perturbations"


def pert_id_for(text):
    return "p" + hashlib.sha256(text.encode()).hexdigest()[:14]


def _rel(path):
    try:
        return str(Path(path).relative_to(C.ROOT))
    except ValueError:  # outside the project (tests)
        return str(path)


def generate(design, cfg, n_per_type=None, types=None, seed=None, out_root=None):
    """-> manifest dict (also written to <out>/manifest.json); files roundtrip.v and <ptype>_<k>.v."""
    noise = cfg["noise"]
    n = int(n_per_type or noise["n_per_type"])
    types = list(types or noise["types"])
    seed = seed if seed is not None else f"{design['design_id']}:{noise.get('seed', 1)}"
    out = Path(out_root or PERT_DIR) / design["design_id"]
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"design_id": design["design_id"], "top": design["top"], "seed": str(seed), "n_per_type": n,
                "git_sha": C.git_sha(), "cfg_hash": C.cfg_hash(), "perturbations": [], "not_applicable": {}, "error": None}
    try:
        ast, directives, notes = V.parse_files(K.abs_paths(design, design["files"]), incdirs=K.abs_paths(design, design["incdirs"]),
                                               workdir=out / "normalised")
        manifest["notes"] = notes
    except V.Unsupported as e:
        manifest["error"] = f"unsupported: {e}"
        (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
        return manifest
    except Exception as e:  # Pyverilog cannot read the design: no AST perturbations for it
        manifest["error"] = f"parse: {type(e).__name__}: {str(e)[:300]}"
        (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
        return manifest
    roundtrip = V.emit(ast, directives)
    (out / "roundtrip.v").write_text(roundtrip)
    manifest["roundtrip"] = {"path": _rel(out / "roundtrip.v"), "pert_id": pert_id_for(roundtrip)}
    for ptype in types:
        fn = P.TRANSFORMS[ptype]
        seen = {roundtrip}
        for k in range(n):
            try:
                new_ast, details = fn(ast, seed, k)
            except P.NotApplicable as e:
                manifest["not_applicable"][ptype] = str(e)
                break
            except Exception as e:  # a transform bug on this design: recorded, never silently skipped
                manifest["not_applicable"][ptype] = f"transform error: {type(e).__name__}: {str(e)[:200]}"
                break
            text = V.emit(new_ast, directives)
            if text in seen:
                continue  # the same rewrite came out twice (few sites): not a new perturbation
            seen.add(text)
            path = out / f"{ptype}_{k}.v"
            path.write_text(text)
            manifest["perturbations"].append({"pert_id": pert_id_for(text), "ptype": ptype, "k": k,
                                              "path": _rel(path), "details": details})
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True, default=str) + "\n")
    return manifest


def _text_entries(design, cfg, module, n_per_type, seed, out_root, make_variants):
    """Shared by the text-level generators: the manifest's entries of the module's ptype are KEPT (their SEQ records and
    evaluations stay valid) and topped up to n with new variants (k continues after the highest existing k); a variant whose text
    equals an existing one is not a new perturbation. -> manifest dict (written)."""
    noise = cfg["noise"]
    n = int(n_per_type or noise["n_per_type"])
    seed = seed if seed is not None else f"{design['design_id']}:{noise.get('seed', 1)}"
    out = Path(out_root or PERT_DIR) / design["design_id"]
    out.mkdir(parents=True, exist_ok=True)
    mp = out / "manifest.json"
    manifest = json.loads(mp.read_text()) if mp.exists() else {"design_id": design["design_id"], "top": design["top"], "seed": str(seed), "n_per_type": n,
                                                                "perturbations": [], "not_applicable": {}, "error": None}
    existing = [e for e in manifest.get("perturbations") or [] if e.get("ptype") == module.PTYPE]
    seen = set()
    for e in existing:
        try:
            paths = [Path(C.ROOT) / p for p in (e.get("paths") or [e["path"]])]
            seen.add("\n".join(pp.read_text() for pp in paths) if len(paths) > 1 else paths[0].read_text())
        except OSError:
            pass
    start = 1 + max([int(e.get("k", -1)) for e in existing] or [-1])
    want = n - len(existing)
    files = K.abs_paths(design, design["files"])
    variants = []
    if want > 0:
        try:
            variants = make_variants(files, seed, want, start)
        except P.NotApplicable as e:
            manifest["not_applicable"][module.PTYPE] = str(e)
        except Exception as e:
            manifest["not_applicable"][module.PTYPE] = f"text {module.PTYPE} error: {type(e).__name__}: {str(e)[:200]}"
    for k, details, texts in variants:
        # one file per variant when the design is a single file; multi-file designs get a directory per variant
        if len(texts) == 1:
            text = next(iter(texts.values()))
            if text in seen:
                continue
            seen.add(text)
            path = out / f"{module.PTYPE}_{k}.v"
            path.write_text(text)
            manifest["perturbations"].append({"pert_id": pert_id_for(text), "ptype": module.PTYPE, "k": k, "path": _rel(path), "details": details})
        else:
            vdir = out / f"{module.PTYPE}_{k}"
            vdir.mkdir(exist_ok=True)
            joined = "\n".join(texts[f] for f in sorted(texts))
            if joined in seen:
                continue
            seen.add(joined)
            paths = []
            for f, text in texts.items():
                p = vdir / Path(f).name
                p.write_text(text)
                paths.append(_rel(p))
            manifest["perturbations"].append({"pert_id": pert_id_for(joined), "ptype": module.PTYPE, "k": k, "path": paths[0], "paths": paths, "details": details})
    n_text = len([e for e in manifest["perturbations"] if e["ptype"] == module.PTYPE])
    if n_text:
        manifest["not_applicable"].pop(module.PTYPE, None)
    manifest[module.PTYPE.lower()] = {"n": n_text, "git_sha": C.git_sha(), "cfg_hash": C.cfg_hash()}
    mp.write_text(json.dumps(manifest, indent=1, sort_keys=True, default=str) + "\n")
    return manifest


def generate_text_p1(design, cfg, n_per_type=None, seed=None, out_root=None):
    """DECISIONS 2026-09-14 G1.2: text-level P1 renamings (src/noise/rename_text.py) appended to the design's manifest
    (ptype P1_text, files P1_text_<k>.v). Since REQUEST 2026-09-20 (e) 3 the identifier table comes from the text scanner
    (no Pyverilog parse: the step that fails on 7 of the 13 pooled-floor designs) and existing entries are kept and topped up
    to n. -> manifest dict."""
    from src.noise import rename_text as RT
    return _text_entries(design, cfg, RT, n_per_type, seed, out_root,
                         lambda files, sd, n, start: [(k, {"renamed": mapping}, texts) for k, mapping, texts in RT.text_variants(files, None, sd, n, start=start)])


def generate_text_p2(design, cfg, n_per_type=None, seed=None, out_root=None):
    """REQUEST 2026-09-20 (e) item 3 (PLAN 6.9): text-level P2 statement reorders (src/noise/reorder_text.py) appended to the
    design's manifest (ptype P2_text, files P2_text_<k>.v); existing entries kept and topped up to n. -> manifest dict."""
    from src.noise import reorder_text as RO
    return _text_entries(design, cfg, RO, n_per_type, seed, out_root, lambda files, sd, n, start: RO.text_variants(files, sd, n, start=start))
