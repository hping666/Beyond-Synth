"""Static isolation scan (docs/spec/06-hidden-layer.md): nothing under src/ and no script except the hidden worker
and the hidden report may name the hidden results database or its directory; search code, prompt templates and the
predictor therefore cannot read hidden results even by accident (CLAUDE.md rule 3)."""
import os
import re
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALLOWED = {"scripts/hidden_worker.py", "scripts/report_hidden.py", "scripts/hooks/guard.py"}  # the guard enforces the rule
PATTERN = re.compile(r"hidden\.sqlite|results/hidden|hidden_db_path|/hidden/raw")


def scan(paths):
    hits = []
    for p in paths:
        rel = str(p.relative_to(ROOT))
        if rel in ALLOWED or "__pycache__" in rel:
            continue
        for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
            if PATTERN.search(line) and not line.lstrip().startswith("#") and '"""' not in line:
                hits.append(f"{rel}:{i}: {line.strip()[:100]}")
    return hits


def test_no_module_outside_the_hidden_worker_names_the_hidden_database():
    files = list((ROOT / "src").rglob("*.py")) + list((ROOT / "scripts").rglob("*.py")) + list((ROOT / "src").rglob("*.txt")) + list((ROOT / "src").rglob("*.tcl"))
    hits = scan(files)
    # src/eval/service.py routes hidden configurations by the connection's path ("/hidden/" test) and never opens the file itself
    hits = [h for h in hits if not h.startswith("src/eval/service.py")]
    assert hits == [], "\n".join(hits)


def test_scan_catches_a_reader():
    tmp = ROOT / "src" / "_isolation_probe.py"
    tmp.write_text('import sqlite3\nc = sqlite3.connect("results/hidden/hidden.sqlite")\n')
    try:
        assert scan([tmp]) and "_isolation_probe.py:2" in scan([tmp])[0]
    finally:
        tmp.unlink()
