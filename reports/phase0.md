# reports/phase0.md — Phase 0: environment and skeleton (STOP G0)

- Phase 0 · 2026-09-12 · git 9be4676 (report committed on top) · snapshot: none (Phase 0 produces no experimental tables; `scripts/snapshot.py` is written in Phase 1)

## Goal

A runnable project skeleton on the cinnamon EDA environment: bootstrap, environment facts, guard rules, job queue, evaluation service for every DC rung and hidden configuration, equivalence stack, power path and license check; one small design run end-to-end through every tool with reference artifacts; every decision rule tested in both directions (CLAUDE.md rule 2). G0 answers: environment self-check results; whether VC Formal SEQ and DPV are usable; one successful run each of `-spg`, ASAP7 and sky130hd; whether the license permits publishing cross-tool comparisons.

## What was done (PLAN task numbers)

- 0.0 Bootstrap: git repository on `main`, `.gitignore`, deploy key `~/.ssh/id_ed25519_beyond_synth` with ssh alias `github-beyond-synth`, remote `hping666/Beyond-Synth` (GitHub's auto-generated README merged), `OPENAI_API_KEY` placed by the user in `~/.config/beyond-synth/env.sh` (mode 600, sourced by `~/.bashrc` and by the queue daemon) and verified with one models-list call (HTTP 200; the four candidate models and the review model are visible).
- 0.1 Environment: eda-knowledge read in the prescribed order; `selfcheck.py` 22/22 and `e2e.py` 11/11 re-run from this project (detached, 06:57–07:09); environment section of STATUS.md filled; tool versions and library paths written into `config/experiments.yaml` (`tools`, `libs`). Finding: `flow/synth.tcl` offers none of `-retime`, `-timing_high_effort_script`, `-gate_clock`, `-no_autoungroup`, `set_host_options`, `report_resources`, `report_clock_gating`, `read_saif`, so every rung except E1/E2 needs project-owned DC Tcl (spec 01 §2); `flow/` is called, never modified.
- 0.2 Layout, `.venv` (Python 3.13.12), pinned `requirements.txt`.
- 0.3 `.claude/settings.json`: 20 deny rules plus a PreToolUse guard (`scripts/hooks/guard.py`, shell-aware parsing of commands, heredocs and `-c` strings) enforcing rules 1/3/5/10/12; 125 bidirectional cases.
- 0.4 Job queue `src/jobqueue/` (SQLite `jobs` table, pools dc 50 / pt 8 / vcf 4 / local 16, exit-75 license backoff 60→900 s, one retry, timeouts kill the process group, per-attempt logs and done markers, recovery after daemon restart, detached daemon sourcing the secrets file and the EDA env once), CLIs `scripts/queue/{daemon,submit}.py`, `scripts/status.py`; 11 tests; detached end-to-end smoke (job saw `dc_shell` and the key).
- 0.5 Evaluation service `src/eval/`: `templates/dc_eval.tcl` (every command through the double-checked `step`, SDC section bracketed by markers, `set_host_options -max_cores 4`, full report set incl. `report_reference`, `report_resources -hierarchy`, `report_clock_gating`, `report_power` with and without SAIF, ddc/netlist/applied SDC), `dc.py`, `parse.py`, `sdc.py` (one OpenSTA-native SDC convention; DC copy via `sdc_compat.tcl` and unit scaling), `yosys.py` (Y, O0–O2), `pt.py` (H4 through `flow/sta.py` + `flow/power.py`), `knee.py`, `service.py` (content-addressed `results/raw/<design>/<config>/<hash>/`, cache, `-rN` reruns, `meta.json`, ingest), `src/db/{schema.sql,core.py,ingest.py}` (all spec 07 tables), queue runner `src/eval/run_dc.py`; reference artifacts for 14 configurations in `tests/fixtures/rtllm_accu/`.
- 0.6 Equivalence stack `src/equiv/`: V1 interface check (Yosys JSON), V2 lock-step VCS harness with deterministic random stimulus, per-output latency-offset detection and VCD of both instances, V3 VC Formal SEQ through `flow/vcf.py`, V4 VC Formal DPV through the project's `dpv.py`, verdict logic in `stack.py`, queue runner `run_equiv.py`.
- 0.7 Power path: lock-step VCD → `vcd2saif` (ships with DC) → DC `read_saif` and PrimePower on the same SAIF.
- 0.8 License check: no Synopsys license agreement text exists on this machine; recorded as `unclear` (DECISIONS).

## Key numbers

Environment (measured 2026-09-12): DC W-2024.09-SP5-3 (DC Ultra, DC-Graphical, Power Compiler features present), PrimeTime/PrimePower V-2023.12-SP5-4, VC Formal Y-2026.03-SP1-1 with bundled VCS, Yosys 0.63 + OpenROAD 26Q1-2754 (ORFS df27ce67); libraries nangate45 (+ Milkyway for topographical/`-spg`), asap7 (ps units), sky130hd; license `1720@viterbi-lic01.vlab.usc.edu`; `selfcheck.py` 22/22, `e2e.py` 11/11.

RTLLM accu (`verified_accu`, 13 registers) through every configuration; clocks 2.0 ns nangate45 / 0.5 ns asap7 / 5.0 ns sky130hd (smoke values, not knee points); `dc_s` = whole `dc_shell` wall time:

| Config | Tool / setting | Area | Cells | WNS ns | TNS ns | ICG | Power (default toggles) mW | dc_s |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| E1 | `compile` | 141.246 | 54 | +0.683 | 0 | – | 0.1014 | 4.4 |
| E2 | `compile_ultra` | 138.852 | 59 | +0.711 | 0 | – | 0.1029 | 56.0 |
| E3 | E2 `-retime` | 138.852 | 59 | +0.711 | 0 | – | 0.1029 | 53.7 |
| E4 | E3 `-timing_high_effort_script -gate_clock` | 131.138 | 50 | +0.760 | 0 | 1 | 0.1081 | 53.7 |
| E2r / E2t | E2 + single flag | 138.852 | 59 | +0.711 | 0 | – | 0.1029 | 56 / 55.7 |
| E2g | E2 `-gate_clock` | 131.138 | 50 | +0.760 | 0 | 1 | 0.1081 | 54.1 |
| H1 | E4 @ 0.1 ns | 185.934 | 128 | −0.348 | −4.411 | 1 | 2.710 | 57.5 |
| H2a | E4, ASAP7 | 9.390 | 66 | +0.045 | 0 | 1 | 0.0606 | 118.3 |
| H2b | E4, sky130hd | 655.629 | 53 | +0.877 | 0 | 1 | 0.1878 | 66.7 |
| H3 | E4 `-spg` (topographical) | 135.128 | 57 | +0.942 | 0 | 1 | 0.1067 | 56.8 |
| H5 | `compile_ultra -no_autoungroup -gate_clock` | 131.138 | 50 | +0.760 | 0 | 1 | 0.1081 | 53.7 |
| Y | Yosys+ABC+OpenSTA | 155.344 | 85 | +1.170 | 0 | – | – | 0.8 |
| H4 | PrimeTime on the E4 netlist | – | 51 | +0.760 | 0 | – | 0.0143 (explicit 0.1 toggle) | 9.7 |

Determinism: two E4 runs of the same input are identical in area, cells, WNS, TNS, critical-path delay, ICG count, register count, cell histogram and critical-path endpoint (`tests/test_eval_eda.py::test_e4_is_deterministic`; the full 14-configuration rerun also reproduced every number).

Equivalence, DPV, power (`tests/test_equiv_eda.py`, `test_dpv_eda.py`, `test_power_eda.py`):

| Check | Positive case | Negative case |
|---|---|---|
| V1 interface | renaming perturbation: ports identical | `data_out` 10→12 bits: rejected before simulation |
| V2 lock-step (2000 cycles, VCS) | perturbation identical every cycle, offsets `{data_out: 0, valid_out: 0}` | injected bug (`count == 2`): mismatch on `valid_out`, first cycle recorded |
| V3 SEQ | perturbation proven (2 registers mapped, ~30 s) | bug falsified (~35 s), work dir kept as counterexample |
| V4 DPV (multi_8bit) | direct-multiplication rewrite proven (~50 s) | dropped partial product falsified (~50 s) |
| Power, same SAIF | DC `read_saif` 0.0405 mW vs PrimePower 0.0373 mW (ratio 0.92) | DC default toggles 0.1081 mW (2.7× higher: activity data is mandatory) |

Tests: 170 offline (guard 125, fixtures 17, queue 11, equivalence 8, knee 6, SDC 3) and 13 EDA-backed (evaluation 7, equivalence 3, power 1, DPV 2), all passing on 2026-09-12; EDA tests run with `BS_EDA_TESTS=1` after sourcing `env.sh`.

Footprint: 42 raw evaluation directories = 125 MB (≈3 MB per DC job, two thirds of it `dc_work` intermediates); `/` has 154 GB free, `/hdd1` 50 GB.

## Figures

None in Phase 0 (no experimental data). Knee-point curves start in Phase 1.

## Anomalies and handling

- New traps appended to `eda-knowledge/05-traps.md`: #28 VCS compiles fail under dash (`csrc/rmapats.sh` bashisms; fixed with a bash-as-/bin/sh mount namespace, plus a `dc` calculator shim), #29 DPV start-up (`-no_ui` rejected, `TERMINFO=/lib/terminfo` needed, BASE→ELITE license fallback looks like an error, `solveNB`/`proofwait` sequence, console echo of script lines). Both verified bidirectionally by the tests named above.
- DPV was briefly recorded as unlicensed (FlexNet -5 on `VC-FORMAL-DPV-BASE-SH`); the correction (ELITE feature checked out, proofs run) is in DECISIONS. Rule 8 kept the wrong path from doing harm: the driver returned `unavailable`, never `proven`.
- The first smoke rows (rtllm_accu) were ingested with `icg_count` 0 (table-format `report_clock_gating`) and `dc_seconds` = compile time only; superseded by reruns, all Phase 0 rows are engineering artifacts excluded from analysis (DECISIONS).
- Topographical `report_power` prints only the group table (no "Total Dynamic Power =" lines); `report_saif` has no `-nosplit`; `report_timing` repeats "data arrival time" negated in the slack block. Parsers handle all three; fixtures cover them.
- The E1 run costs 4.4 s in total while every `compile_ultra` configuration costs 54–57 s on a 50-cell design (ASAP7 118 s): the fixed cost sits in `compile_ultra`, not in `dc_shell` start-up. Relevant to screening economics (E1 is ~12× cheaper than E4 on tiny designs; the ratio will shrink on large designs).
- Y (COEVO caliber) reports 155 area / 85 cells against E1's 141 / 54: consistent with the earlier DC-vs-ORFS baselines. COEVO's actual Yosys script differs from the proposal's Y definition (DECISIONS).
- RTLLM testbenches instantiate the unprefixed module name (`accu`) while the design files declare `verified_accu`; Phase 1 staging must canonicalise top names before running testbenches.
- PrimePower's "default" power (explicit 0.1 toggle rate) and DC's default-toggle power are different conventions (0.014 vs 0.108 mW); only SAIF-driven numbers are compared across tools.
- `-gate_clock` needs the Power Compiler feature: present (banner) and working (ICG inserted, 12/13 registers gated).

## Impact on the proposal (questions for the human)

1. G0 answers: SEQ usable (yes, single-worker path); DPV usable (yes, ELITE feature); `-spg` runs (nangate45 only, as asap7/sky130hd have no Milkyway library, consistent with H3's definition); ASAP7 and sky130hd runs succeed; license: **unclear**. Do you agree to close G0 on these facts?
2. Publication of cross-tool (Yosys vs DC) comparisons: no license text is on the machine. Until Viterbi ITS confirms the Synopsys University Program clause, cross-tool tables stay in internal reports and the paper uses within-DC rung differences, the open-source ladder and the reproduction-layer retention fraction (PROPOSAL §5.2). Will you ask ITS, or should the restricted write-up be the plan of record?
3. Raw-artifact retention: at ≈3 MB per DC job the Phase 5 scale (tens of thousands of runs) is 100–300 GB on `/`. Proposal: treat `dc_work/` (DC's own intermediates: `command.log`, `default.svf`, `*.pvl/*.syn/*.mr`) as scratch removed once `meta.json` is written and ingested, keeping reports, netlist, ddc, SDC and logs (~1 MB); results stay append-only. Please confirm before Phase 2 (the only place this is decided).
4. The Y caliber: keep the proposal's `synth -top; dfflibmap; abc; stat` (config) or replace it by COEVO's exact script (flatten + `opt -full`)? The difference is reported either way.
5. Phase-2/3 cost model: `dc_seconds` counts the whole `dc_shell` wall time; the E4 floor of ~55 s per run even for tiny designs makes the per-design DC budget `k_e4_equiv × t_E4(D)` well defined. No change proposed; noted for the E4-runtime measurement of Phase 2.
6. V4 scope: DPV is wired for combinational modules after an inconclusive SEQ; clocked datapath modules need a phase mapping (decided in the Phase 2 SEQ pilot). Acceptable?

## Addendum (G0 follow-up, 2026-09-12): is the E1–E4 ladder real on this DC?

Sources: the man pages of `compile` / `compile_ultra` and the `compile_*` variables shipped with W-2024.09-SP5-3, plus a probe of four RTLLM designs under timing pressure (`scripts/ladder_probe.py`, data in `reports/data/phase0_ladder_probe_{1,2}.json`; wire-load mode, nangate45; E1s = `compile` with the standard synthetic library only; XT = `compile_timing_high_effort` variable + `-retime -gate_clock`).

| Design (clock) | E1s | E1 | E2 | E2t | E3 | E2g | E4 | H5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| div_16bit (3.0 ns, combinational divider) area | 2372 | 2535 | 1609 | =E2 | =E2 | =E2 | =E2 | 1651 |
| multi_pipe_8bit (1.0 ns) area / regs / ICG | 960 / 92 | 929 / 92 | 873 / 92 | =E2 | 857 / 94 | 878 / 92 / 1 | 851 / 97 / 1 | 878 / 92 / 1 |
| adder_pipe_64bit (0.9 ns) area / regs / ICG | 2562 / 360 | 2510 / 360 | 2530 / 360 | =E2 | 2532 / 368 | 2383 / 360 / 4 | 2359 / 360 / 4 | 2380 / 360 / 4 |
| traffic_light (1.0 ns, FSM) area | 136.5 | 137.5 | 129.5 | =E2 | =E2 | =E2 | =E2 | =E2 |

Findings:
- `-timing_high_effort_script` (and `-area_high_effort_script`) are documented as "available for backward compatibility with existing scripts and ignored for optimization purposes"; E2t is bit-identical to E2 on all four designs. The replacement, the `compile_timing_high_effort` variable, is not an application variable in wire-load mode ("not supported in WLM mode. Ignoring", OPT-1346, XT identical to E4) and exists only in topographical mode; `compile_high_effort_area` is DC NXT only. In the wire-load ladder of this version there is no timing-high-effort capability to enable.
- E1 → E2 is the large step everywhere (−6% to −37% area; datapath blocks appear; DesignWare Foundation auto-added; ungrouping; boundary optimisation; area strategy).
- E2 → E3 (`-retime`) acts only on near-critical pipelined designs (register counts change, area ±2%) and not on combinational or slack-rich designs; H1's 0.1 ns constraint or a knee-point constraint is what makes E3 differ from E2.
- `-gate_clock` is the dominant E3 → E4 effect where enable registers exist (adder_pipe_64bit −6%, 4 ICGs); Power Compiler licence present.
- `compile` with DesignWare Foundation (the E1 of the smoke) differs from `compile` with only the standard synthetic library by 3–6% on every design, in both directions (for the divider DW makes `compile` worse); the DesignWare architecture choice is therefore a capability of its own.
- H5 (`-no_autoungroup -gate_clock`) differs from E2/E4 on three of four designs.

Recommendation (decision for the human, DECISIONS 2026-09-12): E1 = `compile` with the standard synthetic library only; E2 = `compile_ultra`; E3 = `compile_ultra -retime`; E4 = `compile_ultra -retime -gate_clock`; attribution rungs E1d (`compile` + dw_foundation), E2r, E2g; E2t dropped; H3 = E4 `-spg` in topographical mode, optionally with `compile_timing_high_effort true` as the physical-aware full-effort configuration. CktEvo's commercial setting `compile_ultra -retime -timing_high_effort_script` equals E3 on this version.

## Next steps

- Phase 1: dataset acquisition (Dr.RTL 20, RTL-OPT 36 pairs, CktEvo modules, RTLRewriter; RTLLM v2.0 is local), inventory with canonical top names, E4 synthesizability, knee-point sweeps per library (`src/eval/knee.py`), dev/held split, `designs` table, `reports/phase1.md`.
- Engineering unrelated to G0 (allowed while waiting): SAIF coverage parsing (`report_saif -hier`), queue runners for `pt` / `yosys`, `src/db/query.py`, `scripts/snapshot.py`, `scripts/db_check.py`, SEQ timeout → inconclusive test on a large design.
