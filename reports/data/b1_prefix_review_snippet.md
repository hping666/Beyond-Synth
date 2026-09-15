# Reproducing the B1@E4 prefix assembly shown for the pre-probe review (decision 2026-09-15 item 6)

```python
import sqlite3; from pathlib import Path
from src import config as C; from src.designs import catalog as K; from src.search import prompts as PR
cfg = C.load(); did = "drrtl_pcie"; d = K.load_design(did)
conn = sqlite3.connect(f"file:{C.results_dir(cfg)}/db/results.sqlite?mode=ro", uri=True); conn.row_factory = sqlite3.Row
phi = float(conn.execute("select phi_main_ns_nangate45 from designs where design_id=?", (did,)).fetchone()[0])
base = conn.execute("SELECT * FROM evaluations WHERE design_id=? AND config='E4' AND is_baseline=1 AND pert_id IS NULL AND cand_id IS NULL AND status='ok' AND abs(clock_ns-?)<1e-6 ORDER BY (power_saif_mw IS NOT NULL) DESC, eval_id DESC LIMIT 1", (did, phi)).fetchone()
system, classes, version = PR.load_templates(caliber="E4"); static, sv = PR.load_static_complement()
print(PR.prefix(d, system, base, {}, phi, None, caliber="E4", static_text=static))   # arm B1_E4: floor none, static block instead of the map prior
```

The suffix of a call: `PR.suffix(classes[cls], cls, parent_rtl, feedback_blocks, d["top"], scope_text=...)` with the scope block from `src/search/scope.py` (`select_region` / `region_text`).
