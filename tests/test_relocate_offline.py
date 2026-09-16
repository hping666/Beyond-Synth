"""Storage contingency (storage decision 2026-09-15 item 3): the hidden raw tree moves behind a symlink in two passes without
losing what jobs write meanwhile; the trigger needs the switch, the threshold and a not-yet-relocated tree (both directions)."""
import copy
import importlib.util
import os
from pathlib import Path

from src import config as C


def load():
    spec = importlib.util.spec_from_file_location("relocate_hidden_raw", str(Path(C.ROOT) / "scripts" / "relocate_hidden_raw.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_relocate_two_passes_symlink_and_trigger(tmp_path):
    mod = load()
    cfg = copy.deepcopy(C.load())
    cfg["project"]["results_dir"] = str(tmp_path / "results")
    src = Path(mod.raw_dir(cfg))
    (src / "d1" / "H1" / "r1").mkdir(parents=True)
    (src / "d1" / "H1" / "r1" / "meta.json").write_text("{}")
    dst = tmp_path / "hdd1" / "hidden_raw"
    cfg["retention"]["relocate_hidden_raw"] = {"enabled": True, "dest": str(dst)}
    cfg["retention"]["min_free_gb"] = 15
    assert mod.should_relocate(cfg, free=10.0) and not mod.should_relocate(cfg, free=20.0)
    cfg_off = copy.deepcopy(cfg); cfg_off["retention"]["relocate_hidden_raw"]["enabled"] = False
    assert not mod.should_relocate(cfg_off, free=10.0)
    written = []

    def rsync_fn(s, d):
        mod.rsync(s, d)
        if not written:   # a job writes a record between pass 1 and the swap
            (Path(s) / "d1" / "H1" / "r2").mkdir(parents=True)
            (Path(s) / "d1" / "H1" / "r2" / "meta.json").write_text("{}")
            written.append(1)
    old = mod.relocate(str(src), str(dst), log=lambda m: None, rsync_fn=rsync_fn, now="T")
    assert os.path.islink(src) and os.path.realpath(src) == os.path.realpath(dst) and old.endswith(".moved-T")
    assert (dst / "d1" / "H1" / "r1" / "meta.json").exists() and (dst / "d1" / "H1" / "r2" / "meta.json").exists()   # pass 2 carried the late record
    assert (src / "d1" / "H1" / "r2" / "meta.json").exists()                                                          # visible through the link
    assert mod.state(cfg)["is_link"] and not mod.should_relocate(cfg, free=1.0)                                        # never twice
    (Path(old) / "d1" / "H1" / "r3").mkdir(parents=True)                                                              # a job that held the old directory
    (Path(old) / "d1" / "H1" / "r3" / "meta.json").write_text("{}")
    from src.db import core as db
    db.connect(path=str(tmp_path / "results" / "db" / "results.sqlite"))                                              # an empty jobs table: nothing running
    assert mod.finalize(cfg, log=lambda m: None) == 0
    assert (dst / "d1" / "H1" / "r3" / "meta.json").exists() and not os.path.exists(old)
    assert mod.finalize(cfg, log=lambda m: None) == 0                                                                  # idempotent
