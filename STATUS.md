# STATUS — Beyond the Synthesizer

Written 2026-09-15 at the session handoff (the session of 2026-09-14/15 ends here; a fresh session continues). Read this file, then `docs/PLAN.md` Phase 5 and `reports/phase4.md`.

## Current phase and the next action

**Phase 5 running (2026-09-16 14:10): large tier 25 of 108 runs done, 14 running, 68 waiting (the VC Formal backpressure and the admission rate hold fresh runs while the proof queue exceeds 50; seats 50 / 50 busy); medium and small tiers not started. 2 396 of 36 540 calls (6.6 %), 84 USD of 600, 2 324 candidates, 396 proven, 149 accepted by the arms' own criteria; free disk 60 GB. ETA: large tier ≈ 2026-09-17 evening (stage A report), medium ≈ 2026-09-18 end (B), small ≈ 2026-09-19 (C), hidden part (D) after the completion marker. Early interim observation (stage A interim of 14:02): on the large tier arm M (terra) has 0 proven of 172 verdicts while B1_E4 / B2 / DrRTL_reimpl / B0 reach 14–23 % per call — M's map prior pushes the bandit to classes c1 / d (76 % of its requests) and its rewrites are large restructurings that break equivalence at cycle ≈ 300; to be interpreted in the stage A report (only 2 of 18 M runs done). Guards added overnight: VC Formal backpressure, admission rate (3 fresh runs per minute), round-robin across designs with the fewest-seats-first rule, whole-queue scan under the per-design cap, an 8 GB file limit for simulation jobs (a runaway 36 GB VCD), quota pause (exit 75) after the credit outage of 03:50–03:55 (DECISIONS of 2026-09-16).** Watch with `python3 scripts/phase5_main.py status` and `scripts/status.py`; the staged reports come from `scripts/phase5_stages.py` (interim stage A every 3 h in reports/phase5_stage_A.md) and `report_hidden.py`.

What the launch did (21:48): 609 runs per `exp5.model_assignment` (large tier: terra on every arm = 90, luna on M as the contrast = 18; medium / small: luna on every arm = 360, terra on M / B2 = 144), large tier first; `queue.vcf_seats_target` and `dc_seats_target` set to 50 and the daemon restarted; `scripts/hidden_loop.py` registering the hidden configurations of the Phase 5 and probe candidates every 30 minutes (accepted + audit sample; 20 % audit for H1 / H3 / H5) and running the relocation check (`scripts/relocate_hidden_raw.py auto`) every pass. Stamps: equiv_version phase5, floor_version phase4.

**Arm `DrRTL_reimpl` (PLAN 5.2) implemented at 17:55 (commit a00c7d4; DECISIONS "Arm DrRTL_reimpl implemented"):** Dr. RTL's optimizer role, the released skill library in the prefix, per call the ten worst E4 paths with slack and the critical path's cells plus a rotating diversity strategy, and one skill-extraction call per built round charged to the equal-call budget; B2's fitness and archive. The driver still refuses an arm without a definition. **H4 (PrimeTime / PrimePower) wired into the hidden worker at 18:12 (DECISIONS "H4 ... wired"):** signoff records for D baselines and accepted / audit-sample candidates in the queue's pt pool; the hidden loop covers it for Phase 5.

**Deviation to know about (DECISIONS "Probe launched, stopped after 10 minutes, and the scope aid amended"):** the first probe launch produced only scope violations and unusable answers because both models return the named module alone on multi-module designs; the scope aid now splices the omitted modules from D and the prompt says the model may return only the region module. Its 12 runs are `superseded` (6.7 USD of the probe cap); the second launch produces proven candidates (terra and sol 10 each on drrtl_pcie within 10 minutes; repairs of lock-step mismatches 3 of 4 proven so far).

Done since the previous STATUS: decisions of 2026-09-15 recorded and implemented (disk guard `retention.min_free_gb` 15; B0's tool-neutral prefix with the Y-caliber summary only; the normalised E4 log line; `E1_authors`: 25 better / 1 same / 7 worse of 33 against `E2_1ns` 13 / 4 / 16 and the released reports 34 / 0 / 0, reports/phase4.md §4d, PROPOSAL §3.2 row); the Phase 5 starting points drawn (`exp5.starting_points`, seed 1: 6 small / 18 medium / 6 large); the launch tooling and the hidden-layer scope; arm DrRTL_reimpl; tests 361 passed.

G5 report: `reports/phase4.md` (§4b–§4d added today), `reports/phase4_conclusions.md`; snapshots `phase4-20260915-review`, `phase4-20260915-1115`.

## Pending STOP gates

| Gate | Status | Report | User decision |
|---|---|---|---|
| G0 | closed 2026-09-12 | reports/phase0.md | recorded in DECISIONS |
| G1 | closed 2026-09-13 | reports/phase2.md | rule A floors, floor classes, pooled minimum (DECISIONS 2026-09-14 G1.x) |
| G2 | closed 2026-09-13 | reports/phase2.md §4 / §4b | SEQ protocol with the all-zero initial state; the latency mapping implemented and confirmed (26 of 28 proven) |
| G3 | closed 2026-09-14 | reports/phase3.md | screening stays out of the main method (AUROC 0.721) |
| G4 | closed 2026-09-14 | reports/phase3.md §7 | luna main model, terra second model on M and B2, C1 scope, floor versioning |
| G5 | closed 2026-09-15 | reports/phase4.md, reports/phase4_conclusions.md | Phase 5 go with four adjustments; engineering order; map paper; additional tasks; tiered storage (DECISIONS "G5 decisions") |
| Storage decision | closed 2026-09-15 | reports/data/phase5_footprint.md | option A executed (86.8 GB free after the prune); ~/.cache stays (the user's) |
| Pre-probe review | closed 2026-09-15 | static_complement.md v1 approved; prefix fixes applied | probe go; Phase 5 launch pre-authorised under the caps |
| Evening decisions 2026-09-15 | items 2–6 done | DECISIONS "Implementation of the evening decisions" | recorded verbatim |
| Storage decision 2026-09-15 | closed | DECISIONS "User storage decision" / "Implementation of the storage decision" | option D + 20 % audit, 5 GB reserve, relocation contingency |
| Phase 5 launch | **launched 21:48** (609 runs; 21:05 and 21:40 attempts aborted before submission: missing Y baselines, run-id collision) | reports/data/phase5_prelaunch.md, reports/data/phase5_probe_report.md | the B0 / thresholds_128x4096 exclusion is an operator deviation the user may reverse |
| G6+ | not reached | — | — |

## In-flight work

- **Probe runs** (exp phase5_probe, 12 runs, search jobs on the local pool): gpt-5.6-terra and gpt-5.6-sol × 3 designs × 2 seeds, K 6 × N 5, cap 120 USD (10 USD spent at 17:42 including the 6.7 USD of the superseded first launch). `python3 scripts/phase5_probe.py status`.
- **Autolaunch watcher**: no longer needed (launch done); its launched-before guard stops it at once.
- **Phase 5 runs**: `python3 scripts/phase5_main.py status`; a killed run (e.g. a transient API error beyond the retry budget) keeps its state and is resubmitted as a `search` job with `{"run_id": ...}` (see the sol probe run of 19:22 in DECISIONS).
- **Queue daemon**: restarted at 18:26 (pid 591986) so that it knows the new `search` pool (`queue.search_max` 16, DECISIONS "Search runs get their own queue pool"): search runs no longer share the local pool with the yosys fitness jobs that arm B0 runs wait for (a deadlock at the Phase 5 scale). Targets 24 / 24 until the launch sets 50 / 50 and restarts it again.
- **Smoke runs before the launch (rule 7, exp `smoke`, luna, K 2 × N 3)**: `DrRTL_reimpl` on drrtl_controller finished 18:23 — the arm works end to end (timing block with the 10 worst paths and the critical cells, rotating strategy, skill-extraction call parsed into two [avoid] entries fed to round 2; 0.03 USD) but 3 of its 4 first-round answers were **scope violations** (the path list points at endpoints outside the block-level region, and the model rewrote those blocks too). Two arm M smoke runs at block-level scope (drrtl_controller, rtllm_traffic_light) were submitted at 18:26 to measure the base rate of the aid itself; the probe never exercised block-level scope (its designs are multi-module → module-level regions, 0 violations).
- **Hidden loop**: running since 21:47 (`python3 scripts/hidden_loop.py status`; registers Phase 5 and probe candidates every 30 min, relocation check first).
- **Stages loop**: `python3 scripts/phase5_stages.py status` (stage reports A / B / C when their tiers complete; ANOMALY lines in its log).
- **Hidden registrations submitted 18:12**: 616 H4 signoff jobs (pt pool, 8 seats: 179 D baselines, 257 Phase 3 + 155 Phase 4 + 25 probe candidates; 257 duplicates of the Phase 3 set return cached records) and 220 DC jobs for the 44 rtllm_multi_pipe_8bit candidates of Phase 3 that had no hidden record (priority 0). `python3 scripts/queue/daemon.py status`; coverage counts: `python3 scripts/hidden_worker.py --coverage-candidates --exp phase3|phase4|phase5_probe`.
- Session-bound: a Monitor of this session prints the probe's progress every 5 minutes; nothing else.

## Budget and hours (2026-09-15 17:45)

| Item | Spent | Cap (config) | Note |
|---|---|---|---|
| LLM phase3_calibration | 41.85 USD | 60 | closed |
| LLM phase4_generation | 4.02 USD | 40 | closed |
| LLM phase5_probe | ≈ 10 USD and rising | 120 | 6.7 USD of it in the superseded first launch |
| LLM phase5_main | 0.00 USD | 600 | projected 355 USD for the 630 runs |
| LLM phase6_ablation | 0.00 USD | 200 | not started |
| DC seat-hours (jobs table, cumulative, all phases, failed and hidden runs included) | 1 076.6 h at 18:25 | reported, not budgeted | `scripts/status.py` |
| VC Formal seat-hours (jobs table, cumulative) | 524.3 h at 18:25 | reported, not budgeted | |
| PrimeTime seat-hours | 0.35 h at 18:25 (H4 batch running) | reported, not budgeted | |

## Data state

- Results database: 24 059 evaluations (+E1_authors), 3 035 + probe candidates; `db_check.py` 0 problems at the last check (17:00). Schema additions today: `candidates.repair_of`, `scope_json`, `features_json` at issue time; diagnoses label `scope_violation`; runs exp `phase5_probe`.
- Snapshots: `phase4-20260915-review`, `phase4-20260915-1115`.
- Retention: tiered policy on (`retention.tiered`), kept records slimmed of their regenerable equivalence artifacts (`tiered_eq_delete_kept`, storage decision 2026-09-15), sim_fail VCD 5 % seeded sample, disk guard 15 GB with the relocation contingency; the retroactive prune of 2026-09-15 freed 60 GB of disk (78.5 GB free at 19:22).
- Tests: `pytest tests/` → **386 passed, 15 skipped**.

## Open questions and known risks

- `DrRTL_reimpl` arm: implemented offline (tests) but not yet run end-to-end against the API before the launch; its first Phase 5 runs are its smoke test (watch its unusable-answer and skill-call counts in `phase5_main.py status`).
- H4 wired (18:12); the first Phase 5 H4 records come from the hidden loop; 13 kept Phase 4 candidates have no E4 netlist any more (pruned) and get no H4 record.
- The large tier's proven rate: the probe shows terra and sol proving on drrtl_pcie and drrtl_datapath (≥ 13 each) and near zero on spikeLayer8_H7.
- **Block-level scope**: amended per the evening decision (item 2): out-of-scope edits are restored from D and flagged, never discarded. Smoke rates under the canonical verifier: DrRTL_reimpl / drrtl_controller 3 of 4 (round 1), M / drrtl_controller 3 of 3, M / rtllm_traffic_light 0 of 3 — real edits of the FSM block outside the output-decode region.
- **Disk**: the storage decision (option D + 20 % audit) brings the projection to 44.0 GB against 53.5 GB (free − 20 − 5). Contingency: when free space on / drops below 15 GB the hidden loop moves the hidden raw tree to /hdd1 (53 GB free) behind a symlink (`scripts/relocate_hidden_raw.py`; then `finalize` once no hidden job runs). Kept-record reading: the decision's list (equiv.json, logs, seq.tcl, counterexamples, candidate copy) plus the SAIF; the lock-step VCD / trace / ports of proven candidates go (keeping them would project 66.9 GB).
- **Runaway simulations**: a candidate's lock-step VCD reached 36 GB in 18 minutes (a zero-delay loop, 2026-09-16 04:50; DECISIONS "Runaway lock-step simulation"); `queue.max_file_gb` now caps simulation / equivalence jobs at 8 GB per file (ulimit -f) — such a job fails cleanly.
- **LLM rate limits**: `llm.retry` waits 15 → 480 s on 429 / 5xx / connection errors (the old 2 / 4 / 6 s backoff killed a sol probe run twice); a run killed anyway keeps its state and can be resubmitted as a search job.
- Transient disk footprint of in-flight proofs: the probe's equivalence records on spikeLayer8_H7 reach ≈ 0.5 GB each (VCS build + VC Formal databases) until the candidate is final and slimmed; 12 probe runs held ≈ 12 GB at 18:20. With 16 concurrent runs on large designs the transient can reach 20–40 GB on top of the retained footprint; the disk guard (15 GB) pauses submissions rather than failing.
- DPV phase mapping (engineering item (v), "only if time remains"): deliberately not started today — a change of the equivalence stack under a pre-authorised launch would make Phase 5 verdicts heterogeneous; proposed for the user's decision as a Phase 6 / post-launch item.
- The DC-hour cap (4 000 h) is an operator derivation (DECISIONS "Phase 5 launch tooling"); the VC Formal cap is the G4-accepted projection.
- `scripts/status.py` seat-hours now come from the jobs table (18:25: DC 1 076.6 h cumulative incl. failed and hidden runs, VC Formal 524.3 h, PT 0.35 h).
- Hidden registration completion counts for Phase 3 / Phase 4 objects not yet reported (counts only); 49 hidden noise records (H1 16, H2a 7, H2b 7, H5 13, H3 6) are still missing per `--submit-noise --missing --dry-run` (not resubmitted today; check whether they are deterministic failures).

## Resume checklist (run first, in this order)

```bash
cd /home/hping/Beyond-Synth && source .venv/bin/activate
python3 scripts/status.py            # daemon running; pools; LLM totals; disk guard line
python3 scripts/queue/daemon.py status
python3 scripts/db_check.py          # 0 problems, 0 warnings
python3 scripts/phase5_autolaunch.py status   # waiting / launched / no-go, with the log tail
python3 scripts/phase5_probe.py status        # per (model, design) proven, verdict, repair yield, scope violations
python3 scripts/phase5_main.py status         # after the launch: runs by model / arm / tier
python3 scripts/hidden_loop.py status
pytest tests/ -x -q                  # 386 passed, 15 skipped
git status --short && git log --oneline -3
df -h / | tail -1
```
Then: `docs/DECISIONS.md` (tail, the entries after "Review and decisions after the pre-probe review"), `reports/data/phase5_prelaunch.md`, `reports/data/phase5_probe_report.md`, `docs/PLAN.md` Phase 5.

## Done on 2026-09-15 after the gate (chronological; details in DECISIONS)

- G5 recorded; storage footprint; B1@E4 prompt; SEQ latency mapping; scope-limited rewriting and repair; tiered retention; G5 item 4 (b) (c) (d).
- Decisions of 2026-09-15: sim_fail VCD sample, sol prices from the live page, E2_1ns, hidden scope, probe script, map prior; prune applied (86.8 GB free); pilot re-run (26 / 28 proven); LLM review (23 objects, map shape unchanged); E2_1ns (13 / 4 / 16).
- Review decisions: disk guard; B0 tool-neutral prefix; normalised E4 log line; E1_authors (25 / 1 / 7); PROPOSAL row; probe launched, stopped, scope splice, probe relaunched; starting points drawn; launch tooling; hidden scope and loop; autolaunch watcher started; arm DrRTL_reimpl implemented (plan 540 → 630 runs); H4 wired and 616 signoff jobs + 220 Phase 3 registrations submitted; seat-hours from the jobs table; search pool; DrRTL smoke run; block-scope smoke runs.


## Environment (filled by Claude Code in Phase 0 after reading eda-knowledge; afterwards updated only when the environment changes)

- Verification runs (this project's own record): `selfcheck.py` 22/22 and `e2e.py` 11/11 on 2026-09-12 (06:57–07:09 PDT, detached job; result JSONs `/hdd1/hping/eda/work/selfcheck.json` 07:06 and `e2e_result.json` 07:09; no orphan EDA processes afterwards). Host: cinnamon, Xeon Gold 5218 64 cores, 503 GB RAM, Ubuntu 20.04.
- Design Compiler version / path: W-2024.09-SP5-3 (DC Ultra; features DC-Ultra-Opt, DC-Expert, HDL-Compiler, DC-Graphical) at `/hdd1/hping/eda/synopsys/syn/W-2024.09-SP5-3`, `dc_shell` on PATH after `source /hdd1/hping/eda/setup/env.sh`. Reads only `.db` libraries. Determinism knob `set_host_options -max_cores` (config `tools.dc.max_cores: 4`) is not set by `flow/synth.tcl`; the project's own templates must set it.
- PrimeTime / PrimePower version: V-2023.12-SP5-4 at `/hdd1/hping/eda/synopsys/prime/V-2023.12-SP5-4` (`pt_shell`); driven by `flow/sta.py` (`sign_off`) and `flow/power.py` (`analyze`, activity = explicit | saif | vcd). PT single run ≈ 5 s.
- VC Formal version; SEQ app usable? DPV app usable? (measured, with job path): Y-2026.03-SP1-1 at `/hdd1/hping/eda/synopsys/vc_formal/Y-2026.03-SP1-1`; deliberately not on PATH; SEQ through `flow/vcf.py` (`seq_equiv`), DPV through the project's `src/equiv/dpv.py`. SEQ usable: yes, bidirectional (selfcheck 2026-09-12 07:06; project test `tests/test_equiv_eda.py`: accu renaming perturbation proven in ~30 s, injected-bug mutant falsified); single-worker path only, ASCII workdir, timeout kills the process tree. DPV usable: yes (2026-09-12, `tests/test_dpv_eda.py`: multi_8bit rewrite proven, bug falsified, ~50 s each; features VC-FORMAL-DPV-ELITE-SH + Hector; the BASE feature reports FlexNet -5 first, which is a benign fallback); needs `-batch` without `-no_ui`, `TERMINFO=/lib/terminfo`, and the bash-as-/bin/sh namespace for its RTL frontend.
- VCS version; vcd2saif available?: VCS bundled in the VC Formal tree (`vcs-mx/bin/{vcs,vlogan}`, Y-2026.03-SP1-1, license VCS_UnifiedCompile, 400 seats); works stand-alone with `VCS_HOME` set per `eda-knowledge/01-environment.md`, never in `env.sh` (toolchain clash with DC). The flow's current SAIF path uses Icarus (`/usr/local/bin/iverilog`, `vvp`); this project simulates with VCS inside a bash-as-/bin/sh mount namespace (`src/equiv/harness.py`, trap #28). `vcd2saif`: available, `/hdd1/hping/eda/synopsys/syn/W-2024.09-SP5-3/bin/vcd2saif` (ships with DC), verified 2026-09-12 in the power path (`tests/test_power_eda.py`).
- Yosys / OpenROAD / ORFS versions: Yosys 0.63 + OpenROAD 26Q1-2754, ORFS git df27ce67 (2026-04-01) at `/home/hping/OpenROAD-flow-scripts`; binaries `tools/install/yosys/bin/{yosys,yosys-abc}`, `tools/install/OpenROAD/bin/{openroad,sta}`; ORFS platforms nangate45 / asap7 / sky130hd present; `flow/designs/nangate45/rtllm_*` design dirs exist from the earlier baselines.
- Technology libraries: nangate45 `/hdd1/hping/eda/libs/nangate45/NangateOpenCellLibrary_typical.db` (+ `fakeram45_*.db` macros; Milkyway physical reference `libs/nangate45/mw/` 135 CEL / 134 FRAM for topographical and `-spg`); asap7 `/hdd1/hping/eda/libs/asap7/RVT_TT.list` → 5 `.db` (time unit **ps**, `time_scale=1000`, user API in ns); sky130hd `/hdd1/hping/eda/libs/sky130hd/sky130_fd_sc_hd__tt_025C_1v80.db`. All compiled from the ORFS Liberty files. Physical libraries for `-spg`: nangate45 only (asap7 / sky130hd wireload only), so H3 is nangate45-only, as in config.
- License: server `1720@viterbi-lic01.vlab.usc.edu` (USC Viterbi site 4940, research use confirmed by ITS). Seats per `eda-knowledge/01-environment.md` (not re-measured; no `lmutil` on this machine): DC-Ultra-Opt / DC-Expert / HDL-Compiler / DC-Graphical 50 each, PrimeTime 100, VCS 400, Formality 50 (not installed); one `dc_shell` holds DC-Ultra-Opt + HDL-Compiler + DesignWare seats. Measured day / night DC seats: not measured; seats are site-shared with no fixed safe number (e2e batch `-j 16` passed 32/32 today; daily recommendation `-j 6–8`; config `queue.dc_seats_max: 50` is the license ceiling, not a safe concurrency). VC Formal seats (corrected 2026-09-14 from eda-knowledge/01-environment.md §license): every SEQ feature (VCF-2-Elite-Compile/Runtime-Pkg, VC-FORMAL-ELITE-RT, RMA-RT, SEQ-RT, ELITE-SH) has 50 seats, not shared with DC's features, so 50 DC + 50 VC Formal runs can hold licenses at once; one runtime license covers up to 12 workers of a run (the project runs single-worker because of the multi-worker shutdown deadlock). The queue cap `vcf_seats_max: 4` was a conservative placeholder set on 2026-09-12 when the seat count was misread as unknown; raising it is a config-cap change (rule 6, user decision).
- Summary of the `flow/` script API (inputs, output directories, exit codes, concurrency parameters): all `.py` importable and `--help`-able, `.tcl` driven only by their `.py` (env-var parameters). `synth.synthesize(verilog, top, clk, lib, clk_port, effort∈{ultra, ultra_area, ultra_spg(topo only), simple}, mode∈{wireload, topo}, sdc, dont_use, load_ff, sverilog, incdirs, workdir, keep, timeout, license_retries)` → dict `{status, error, runtime_s, area{total,…}, timing, qor, power, netlist, workdir}`; status ∈ ok / analyze_failed / elaborate_failed / link_failed / constraint_failed / constraint_incomplete (results untrustworthy) / compile_failed / empty_netlist / report_missing / license_failed (auto-retry 15/45/90 s) / timeout / dc_crashed / driver_error; each run in its own workdir (`keep=False` keeps only `reports/` with `netlist.v`, `design.sdc`, `default.svf`). `sta.sign_off(reports_dir, top, lib, netlist, sdc, timeout)`; `power.analyze(reports_dir, top, lib, netlist, sdc, mode, saif, vcd, toggle, prob, timeout, strip_path)`; `vcf.seq_equiv(spec_files, impl_files, spec_top, impl_top, clk, rst, rst_sense, workdir, max_time, timeout, sverilog, workers=1)` → proven / falsified / inconclusive; `equiv.check(gold, gate, top, lib, timeout, workdir, incdirs, sverilog)` → equivalent / not_proven / error; `batch.py -j N`; `bench_common.run_all(...)` (staging, clock inference, license repair round). `selfcheck.py` / `e2e.py` exit 0 iff all items pass. **Gap for this project**: `synth.tcl` offers no `-retime`, `-timing_high_effort_script`, `-gate_clock`, `-no_autoungroup`, `set_host_options`, `report_resources`, `report_clock_gating`, `read_saif`; E1 and E2 map to `simple` / `ultra`, but E3, E4, E2r/E2t/E2g, H1, H2a/H2b (E4 on other libs) and H5 need project-owned DC Tcl templates (`src/eval/templates/`) that copy the `step` proc, `sdc_compat.tcl` and the license-signature classification of `synth.py` without modifying `flow/`.
- Known boundaries (from 06-boundaries.md, relevant to this project): RTL↔netlist commercial equivalence needs Formality (not installed; not needed here, the protocol is RTL↔RTL SEQ); VC Formal multi-worker shutdown deadlock (use `workers=1`, speed on large designs unmeasured); non-ASCII workdir hangs VC Formal; Yosys `equiv.py` returns `inconclusive` on large designs (inconclusive ≠ non-equivalent); asap7 / sky130hd have no Milkyway library (wireload only); synthesis-stage timing and sequential/combinational area splits are not comparable across tools (only total area is); PrimeTime vs OpenSTA differ by 0.14–0.79 ns on the same netlist; DC returns 0 on failure (every step checked twice); license failure under concurrency masquerades as `compile_failed` (DCSH-1); orphan Milkyway / VC Formal process trees hold seats (check after every batch); RTLLM designs with `initial` blocks, delay controls, directory names with spaces, or mixed blocking/non-blocking assignments (VER-134) synthesize differently or fail and must be flagged in the Phase 1 inventory; DC startup ≈ 60 s per run regardless of design size.
- Disk: `/` (holds `/home/hping`, this project and `results/`) 155 GB free of 1.8 TB (91% used); `/hdd1` 50 GB free (98% used) on 2026-09-12. Raw-artifact retention policy to be decided in Phase 0.2 (DECISIONS).
- Python: system `python3` = miniconda 3.13.12 (no pyverilog / pandas / openai); project venv `/home/hping/Beyond-Synth/.venv` (Python 3.13.12) with pyverilog 1.3.0, pandas 3.0.5, pyarrow 25.0.1, PyYAML 6.0.3, scikit-learn 1.9.1, openai 3.13.0, pytest 9.1.1 (`requirements.txt`); sqlite3 from the standard library.
- Network: GitHub reachable (deploy key ~/.ssh/id_ed25519_beyond_synth via ssh alias github-beyond-synth; ssh -T authenticated as hping666/Beyond-Synth on 2026-09-12) / OpenAI API reachable (GET /v1/models HTTP 200 on 2026-09-12; the four candidate models gpt-5.6-luna, gpt-5.4-mini, gpt-5.6-terra, gpt-5.4 and the review model are all visible to the key)
- OpenAI API key: configured (2026-09-12) in ~/.config/beyond-synth/env.sh (mode 600, outside the project, sourced by ~/.bashrc; the queue daemon must source the same file; non-interactive shells must source it explicitly)

## Design-set inventory (filled in Phase 1)

| Suite | Source URL | Count | Synthesizable under DC E4 | With testbench | dev / held split | Notes |
|---|---|---|---|---|---|---|
| Dr.RTL 20 | https://github.com/hkust-zhiyao/DR_RTL @ 62b95a57 (no license file) | 20 | 19 (cpu_pipe: use before declaration, VER-956) | 2 (DSP, LSTM) | held 18 (FIFO two clocks, cpu_pipe failed) | LSTM is combinational; aes is SystemVerilog |
| RTL-OPT 40 pairs | https://github.com/hkust-zhiyao/RTL-OPT @ 25e4bbe0 (MIT; anonymous repo of the paper expired) | 40 (start = suboptimal, reference = `_ref`) | 40 | 0 | held 39 (mux_encode: Yosys cannot read the unpacked array port) | 29 combinational |
| CktEvo modules | https://github.com/cure-lab/cktevo @ 2f1abe75 (OpenCores headers) | pool 83 → set 30 | 78 of the pool (memory models: empty netlist / timeout; simple_cpu mixed assignments) | 0 | held 30 = the set (≤5 per repository, by size) | 11 multi-clock modules excluded from the set |
| RTLLM v2.0 | https://github.com/hkust-zhiyao/RTLLM @ 41b26896 (MIT), local /home/hping/RTLLM | 50 | **N = 43** (ROM / clkgenerator no cells or paths; float_multi, synchronizer event lists; freq_divbyodd, ring_counter assign-to-reg; sequence_detector mixed assignments) | 50 | dev 20 / held 21 (asyn_fifo two clocks; RAM Yosys crash) | tops renamed to the testbench names |
| RTLRewriter 54 short + 18 long | https://github.com/yaoxufeng/RTLRewriter-Bench @ 96639fe6 (no license file) | 72 (roles: original / expert / tool / llm) | 54 (SystemVerilog constructs, undefined symbols, hierarchical names, constant designs) | 2 | calibration only | file roles by rule (DECISIONS 2026-09-12); Nangate45 knee only |

## Decision summary (details in docs/DECISIONS.md)

-
