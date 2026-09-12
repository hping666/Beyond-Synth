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
