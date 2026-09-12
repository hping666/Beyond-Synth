# STATUS.md — current state (read first at the start of every session; update before the end)

Last updated: (date · git sha)

## Current phase

Phase: 0 / 1 / 2 / 3 / 4 / 5 / 6 (see docs/PLAN.md)
Current task:
Stopped at:
Next steps (by priority):
1.
2.
3.

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
- Network: GitHub reachable / OpenAI API reachable:
- OpenAI API key: configured / not configured (never the value)

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
