# STATUS.md — current state (read first at the start of every session; update before the end)

Last updated: 2026-09-12 · Phase 0 complete, STOP G0 (reports/phase0.md)

## Current phase

Phase: 0 (see docs/PLAN.md)
Current task: Phase 0 tasks 0.0–0.5 done. 0.4 = job queue (`src/jobqueue/`, CLIs in `scripts/queue/`, `scripts/status.py`; 11 tests). 0.5 = evaluation service `src/eval/`: project-owned DC template (`templates/dc_eval.tcl`, step-checked, SDC markers, `set_host_options -max_cores 4`), `dc.py` driver, `parse.py`, `sdc.py` (one OpenSTA-native SDC convention, DC copy rewritten and unit-scaled), `yosys.py` (Y / O0–O2), `pt.py` (H4 via flow/sta.py + power.py), `knee.py`, `service.py` (content-addressed `results/raw/<design>/<config>/<hash>/`, cache, `-rN` reruns, ingest), `src/db/ingest.py`, queue runner `src/eval/run_dc.py`. Measured on RTLLM accu (2.0 ns nangate45, 0.5 ns asap7, 5.0 ns sky130hd): all 14 configurations ok (E1–E4, E2r/E2t/E2g, H1, H2a, H2b, H3 `-spg` in topographical mode, H5, Y, H4); E4 `-gate_clock` works (Power Compiler feature present: 1 ICG, 12/13 registers gated); two E4 runs bit-identical (area, WNS, TNS, histogram, critical path); reference artifacts in `tests/fixtures/rtllm_accu/`. Next: 0.6 equivalence stack.
Stopped at: **STOP G0** — `reports/phase0.md` written 2026-09-12, waiting for human confirmation. Daemon stopped; start it with `.venv/bin/python scripts/queue/daemon.py start` before submitting real jobs.
0.6 V4: `src/equiv/dpv.py` (project-owned vcf command line: `-batch`, system terminfo, bash-as-/bin/sh namespace, `solveNB`/`proofwait`, lemma per output): multi_8bit rewrite proven / bug falsified in ~50 s each (`tests/test_dpv_eda.py`); the stack runs V4 on combinational modules after an inconclusive SEQ. 0.7: lock-step VCD → vcd2saif → DC `read_saif` 0.0405 mW vs PrimePower (same SAIF) 0.0373 mW vs DC default toggles 0.1081 mW (`tests/test_power_eda.py`). 0.8: no license text on the machine → `unclear` (DECISIONS).
0.6 so far: `src/equiv/` = ports.py (Yosys JSON interface check, clock/reset inference), rename.py (candidate module suffix `__cand`), harness.py (Verilog-2001 lock-step harness, VCS in a bash-as-/bin/sh mount namespace, trace comparison with constant latency offsets, VCD of both instances, testbench runner), seq.py (VC Formal SEQ via flow/vcf.py, single worker), saif.py (vcd2saif), stack.py (V1→V2→V3 orchestration, verdicts). Bidirectional EDA tests pass on 2026-09-12 (`tests/test_equiv_eda.py`: accu renaming perturbation identical + proven in ~30 s; injected-bug mutant sim_fail + falsified; width change rejected at V1). New trap #28 appended to eda-knowledge (VCS under dash).
Next steps (by priority):
1. `reports/phase0.md` (G0 content per CLAUDE.md) and STOP G0
2. While waiting at G0 (engineering unrelated to the gate): SAIF coverage parsing from `report_saif -hier`, queue runner for `pt` / `yosys` kinds, `src/db/query.py`, `scripts/snapshot.py`, `scripts/db_check.py`, SEQ timeout → inconclusive test on a large design, raw-artifact retention policy
3. Phase 1 preparation: dataset download plan (Dr.RTL, RTL-OPT, CktEvo, RTLRewriter; RTLLM v2.0 is local), canonical top-name staging for RTLLM (`verified_*` vs testbench names)
Open items from 0.5: RTL-line mapping of the critical path is not yet implemented (records carry pin/cell names of the path; PROPOSAL §4.9 borrows CktEvo/Dr.RTL's path-to-RTL mapping in Phase 3); `results/raw` retention policy still to be decided (each DC job dir ≈ 1–2 MB incl. dc_work).

## Pending STOP gates

| Gate | Submitted on | Report path | Human decision |
|---|---|---|---|
| G0 | 2026-09-12 | reports/phase0.md | pending (questions 1–6 in the report: close G0, license/publication, raw retention, Y caliber, cost model, V4 scope) |

## Environment (filled by Claude Code in Phase 0 after reading eda-knowledge; afterwards updated only when the environment changes)

- Verification runs (this project's own record): `selfcheck.py` 22/22 and `e2e.py` 11/11 on 2026-09-12 (06:57–07:09 PDT, detached job; result JSONs `/hdd1/hping/eda/work/selfcheck.json` 07:06 and `e2e_result.json` 07:09; no orphan EDA processes afterwards). Host: cinnamon, Xeon Gold 5218 64 cores, 503 GB RAM, Ubuntu 20.04.
- Design Compiler version / path: W-2024.09-SP5-3 (DC Ultra; features DC-Ultra-Opt, DC-Expert, HDL-Compiler, DC-Graphical) at `/hdd1/hping/eda/synopsys/syn/W-2024.09-SP5-3`, `dc_shell` on PATH after `source /hdd1/hping/eda/setup/env.sh`. Reads only `.db` libraries. Determinism knob `set_host_options -max_cores` (config `tools.dc.max_cores: 4`) is not set by `flow/synth.tcl`; the project's own templates must set it.
- PrimeTime / PrimePower version: V-2023.12-SP5-4 at `/hdd1/hping/eda/synopsys/prime/V-2023.12-SP5-4` (`pt_shell`); driven by `flow/sta.py` (`sign_off`) and `flow/power.py` (`analyze`, activity = explicit | saif | vcd). PT single run ≈ 5 s.
- VC Formal version; SEQ app usable? DPV app usable? (measured, with job path): Y-2026.03-SP1-1 at `/hdd1/hping/eda/synopsys/vc_formal/Y-2026.03-SP1-1`; deliberately not on PATH; SEQ through `flow/vcf.py` (`seq_equiv`), DPV through the project's `src/equiv/dpv.py`. SEQ usable: yes, bidirectional (selfcheck 2026-09-12 07:06; project test `tests/test_equiv_eda.py`: accu renaming perturbation proven in ~30 s, injected-bug mutant falsified); single-worker path only, ASCII workdir, timeout kills the process tree. DPV usable: yes (2026-09-12, `tests/test_dpv_eda.py`: multi_8bit rewrite proven, bug falsified, ~50 s each; features VC-FORMAL-DPV-ELITE-SH + Hector; the BASE feature reports FlexNet -5 first, which is a benign fallback); needs `-batch` without `-no_ui`, `TERMINFO=/lib/terminfo`, and the bash-as-/bin/sh namespace for its RTL frontend.
- VCS version; vcd2saif available?: VCS bundled in the VC Formal tree (`vcs-mx/bin/{vcs,vlogan}`, Y-2026.03-SP1-1, license VCS_UnifiedCompile, 400 seats); works stand-alone with `VCS_HOME` set per `eda-knowledge/01-environment.md`, never in `env.sh` (toolchain clash with DC). The flow's current SAIF path uses Icarus (`/usr/local/bin/iverilog`, `vvp`). `vcd2saif`: not yet measured (Phase 0.7).
- Yosys / OpenROAD / ORFS versions: Yosys 0.63 + OpenROAD 26Q1-2754, ORFS git df27ce67 (2026-04-01) at `/home/hping/OpenROAD-flow-scripts`; binaries `tools/install/yosys/bin/{yosys,yosys-abc}`, `tools/install/OpenROAD/bin/{openroad,sta}`; ORFS platforms nangate45 / asap7 / sky130hd present; `flow/designs/nangate45/rtllm_*` design dirs exist from the earlier baselines.
- Technology libraries: nangate45 `/hdd1/hping/eda/libs/nangate45/NangateOpenCellLibrary_typical.db` (+ `fakeram45_*.db` macros; Milkyway physical reference `libs/nangate45/mw/` 135 CEL / 134 FRAM for topographical and `-spg`); asap7 `/hdd1/hping/eda/libs/asap7/RVT_TT.list` → 5 `.db` (time unit **ps**, `time_scale=1000`, user API in ns); sky130hd `/hdd1/hping/eda/libs/sky130hd/sky130_fd_sc_hd__tt_025C_1v80.db`. All compiled from the ORFS Liberty files. Physical libraries for `-spg`: nangate45 only (asap7 / sky130hd wireload only), so H3 is nangate45-only, as in config.
- License: server `1720@viterbi-lic01.vlab.usc.edu` (USC Viterbi site 4940, research use confirmed by ITS). Seats per `eda-knowledge/01-environment.md` (not re-measured; no `lmutil` on this machine): DC-Ultra-Opt / DC-Expert / HDL-Compiler / DC-Graphical 50 each, PrimeTime 100, VCS 400, Formality 50 (not installed); one `dc_shell` holds DC-Ultra-Opt + HDL-Compiler + DesignWare seats. Measured day / night DC seats: not measured; seats are site-shared with no fixed safe number (e2e batch `-j 16` passed 32/32 today; daily recommendation `-j 6–8`; config `queue.dc_seats_max: 50` is the license ceiling, not a safe concurrency). VC Formal seats: not listed; SEQ takes an SEQ runtime license; measure in the Phase 2 pilot.
- Summary of the `flow/` script API (inputs, output directories, exit codes, concurrency parameters): all `.py` importable and `--help`-able, `.tcl` driven only by their `.py` (env-var parameters). `synth.synthesize(verilog, top, clk, lib, clk_port, effort∈{ultra, ultra_area, ultra_spg(topo only), simple}, mode∈{wireload, topo}, sdc, dont_use, load_ff, sverilog, incdirs, workdir, keep, timeout, license_retries)` → dict `{status, error, runtime_s, area{total,…}, timing, qor, power, netlist, workdir}`; status ∈ ok / analyze_failed / elaborate_failed / link_failed / constraint_failed / constraint_incomplete (results untrustworthy) / compile_failed / empty_netlist / report_missing / license_failed (auto-retry 15/45/90 s) / timeout / dc_crashed / driver_error; each run in its own workdir (`keep=False` keeps only `reports/` with `netlist.v`, `design.sdc`, `default.svf`). `sta.sign_off(reports_dir, top, lib, netlist, sdc, timeout)`; `power.analyze(reports_dir, top, lib, netlist, sdc, mode, saif, vcd, toggle, prob, timeout, strip_path)`; `vcf.seq_equiv(spec_files, impl_files, spec_top, impl_top, clk, rst, rst_sense, workdir, max_time, timeout, sverilog, workers=1)` → proven / falsified / inconclusive; `equiv.check(gold, gate, top, lib, timeout, workdir, incdirs, sverilog)` → equivalent / not_proven / error; `batch.py -j N`; `bench_common.run_all(...)` (staging, clock inference, license repair round). `selfcheck.py` / `e2e.py` exit 0 iff all items pass. **Gap for this project**: `synth.tcl` offers no `-retime`, `-timing_high_effort_script`, `-gate_clock`, `-no_autoungroup`, `set_host_options`, `report_resources`, `report_clock_gating`, `read_saif`; E1 and E2 map to `simple` / `ultra`, but E3, E4, E2r/E2t/E2g, H1, H2a/H2b (E4 on other libs) and H5 need project-owned DC Tcl templates (`src/eval/templates/`) that copy the `step` proc, `sdc_compat.tcl` and the license-signature classification of `synth.py` without modifying `flow/`.
- Known boundaries (from 06-boundaries.md, relevant to this project): RTL↔netlist commercial equivalence needs Formality (not installed; not needed here, the protocol is RTL↔RTL SEQ); VC Formal multi-worker shutdown deadlock (use `workers=1`, speed on large designs unmeasured); non-ASCII workdir hangs VC Formal; Yosys `equiv.py` returns `inconclusive` on large designs (inconclusive ≠ non-equivalent); asap7 / sky130hd have no Milkyway library (wireload only); synthesis-stage timing and sequential/combinational area splits are not comparable across tools (only total area is); PrimeTime vs OpenSTA differ by 0.14–0.79 ns on the same netlist; DC returns 0 on failure (every step checked twice); license failure under concurrency masquerades as `compile_failed` (DCSH-1); orphan Milkyway / VC Formal process trees hold seats (check after every batch); RTLLM designs with `initial` blocks, delay controls, directory names with spaces, or mixed blocking/non-blocking assignments (VER-134) synthesize differently or fail and must be flagged in the Phase 1 inventory; DC startup ≈ 60 s per run regardless of design size.
- Disk: `/` (holds `/home/hping`, this project and `results/`) 155 GB free of 1.8 TB (91% used); `/hdd1` 50 GB free (98% used) on 2026-09-12. Raw-artifact retention policy to be decided in Phase 0.2 (DECISIONS).
- Python: system `python3` = miniconda 3.13.12 (no pyverilog / pandas / openai); project venv `/home/hping/Beyond-Synth/.venv` (Python 3.13.12) with pyverilog 1.3.0, pandas 3.0.5, pyarrow 25.0.1, PyYAML 6.0.3, scikit-learn 1.9.1, openai 3.13.0, pytest 9.1.1 (`requirements.txt`); sqlite3 from the standard library.
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
