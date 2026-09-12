# STATUS.md — current state (read first at the start of every session; update before the end)

Last updated: 2026-09-12 · after bootstrap commit 6578583 (Phase 0.0 done)

## Current phase

Phase: 0 (see docs/PLAN.md)
Current task: 0.0 first-time bootstrap: done (git init on main, .gitignore, deploy key, remote, OPENAI_API_KEY verified with one models-list call)
Stopped at: end of task 0.0; task 0.1 not started
Next steps (by priority):
1. 0.1: read eda-knowledge in order, run selfcheck.py and e2e.py, fill the environment section below, define how src/eval/flow_adapter.py wraps the flow/ scripts (note: synth.py has no -retime / -timing_high_effort_script / -gate_clock / -no_autoungroup modes, so E3/E4/E2x/H1/H2/H5 need project-owned DC Tcl templates per spec 01 §2)
2. 0.2: repository layout, .venv, requirements.txt; record the results-DB git/LFS decision in DECISIONS
3. 0.3: .claude/settings.json deny rules (rm -rf results, results/hidden reads, exfiltration) and hooks; then 0.4 queue daemon, 0.5 evaluation service

## Pending STOP gates

| Gate | Submitted on | Report path | Human decision |
|---|---|---|---|

## Environment (filled by Claude Code in Phase 0 after reading eda-knowledge; afterwards updated only when the environment changes)

- Design Compiler version / path:
- PrimeTime / PrimePower version:
- VC Formal version; SEQ app usable? DPV app usable? (measured, with job path):
- VCS version; vcd2saif available?:
- Yosys / OpenROAD / ORFS versions:
- Technology libraries: nangate45 .db path / asap7 .db path / sky130hd .db path; physical libraries required by `-spg` (which libraries are available):
- License: server; measured DC seats (day / night); PT seats; VC Formal seats:
- Summary of the `flow/` script API (inputs, output directories, exit codes, concurrency parameters):
- Known boundaries (from 06-boundaries.md, relevant to this project):
- Disk: `/home/hping` free / `/hdd1` free:
- Python: version; venv path; key package versions (pyverilog, pandas, sqlite):
- Network: GitHub reachable (deploy key ~/.ssh/id_ed25519_beyond_synth via ssh alias github-beyond-synth; ssh -T authenticated as hping666/Beyond-Synth on 2026-09-12) / OpenAI API reachable (GET /v1/models HTTP 200 on 2026-09-12; the four candidate models gpt-5.6-luna, gpt-5.4-mini, gpt-5.6-terra, gpt-5.4 and the review model are all visible to the key)
- OpenAI API key: configured (2026-09-12) in ~/.config/beyond-synth/env.sh (mode 600, outside the project, sourced by ~/.bashrc; the queue daemon must source the same file; non-interactive shells must source it explicitly)

## Design-set inventory (filled in Phase 1)

| Suite | Source URL | Count | Synthesizable under DC E4 | With testbench | dev / held split | Notes |
|---|---|---|---|---|---|---|
| Dr.RTL 20 | | | | | | |
| RTL-OPT 36 pairs | | | | | | |
| CktEvo modules | | | | | | |
| RTLLM v2.0 | | | | | | |
| RTLRewriter 20 pairs + 12 LLM samples | | | | | | |

## Budget usage

| Item | Cap | Used | Updated |
|---|---|---|---|
| LLM total (USD) | 1000 | | |
| LLM Phase 3 calibration | | | |
| LLM Phase 4 generation | | | |
| LLM Phase 5 main experiment | | | |
| LLM Phase 6 ablations | | | |
| DC hours (cumulative) | — | | |
| VC Formal hours (cumulative) | — | | |

## Open questions / known risks

-

## Decision summary (details in docs/DECISIONS.md)

-
