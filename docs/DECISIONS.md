# docs/DECISIONS.md — Decision log

Format: date · decision · basis · affected files/config · decided by (human / Claude Code)

- 2026-09-12 · Main library Nangate45; hidden libraries ASAP7 + sky130hd; Sky130 additionally serves as the visible caliber of the CktEvo sub-experiment · PROPOSAL §2 and PLAN Phase 5 · config/experiments.yaml · human
- 2026-09-12 · Main skeleton = parallel-candidate hill climbing + small archive; COEVO / REvolution only as skeleton-independence supplementary experiments · PROPOSAL §4.9 · src/search/skeletons · human
- 2026-09-12 · All arms use the same OpenAI model, chosen by the Phase 3 calibration; the original Dr.RTL runs only as a reference row · PLAN Phase 3/5 · human
- 2026-09-12 · The project only calls the scripts in /hdd1/hping/eda/flow/ and never modifies them; any unavoidable change requires re-running selfcheck.py and e2e.py · CLAUDE.md hard rule 1 · human
- 2026-09-12 · STOP gates G0–G5 always "write the report, stop, wait for confirmation" · CLAUDE.md · human
- 2026-09-12 · All project files are written in English · CLAUDE.md · human
- 2026-09-12 · Provisional: `results/db/` and `results/snapshots/` are excluded from git by `.gitignore` until the git-vs-LFS decision for the results database is made in Phase 0.2 · PLAN 0.2 · .gitignore · Claude Code
- 2026-09-12 · Queue caps filled in config (`queue`): `pt_seats_max: 8` (a PrimeTime run takes ≈5 s, 100 seats licensed), `vcf_seats_max: 4` (SEQ runs single-worker, seat count unknown until the Phase 2 pilot), new `local_max: 16` for sim / yosys / orfs / llm / shell jobs on the 64-core host, `poll_sec: 5`; `dc_seats_max: 50` stays the license ceiling and the daemon backs off on exit code 75 (EX_TEMPFAIL) instead of relying on a fixed safe concurrency · eda-knowledge 01-environment.md, 07-deployment.md, 05-traps.md #4 · config/experiments.yaml, scripts/queue/ · Claude Code
- 2026-09-12 · Tool versions and library paths measured in Phase 0.1 written into config (`tools`, `libs`); `dpv_app_ok` and `vcd2saif` remain TBD until Phase 0.6 / 0.7 · STATUS.md environment section · config/experiments.yaml · Claude Code
