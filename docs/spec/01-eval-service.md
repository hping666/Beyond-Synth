# spec 01 — Evaluation service `src/eval/`

Responsibility: given (RTL, configuration name, constraint, library), produce one complete evaluation record that has passed bidirectional checks. Commands for all rungs and configurations come from `config/experiments.yaml: configs`; this file defines semantics and checks only.

## 1. Configuration set

| Name | Tool | Command semantics | Library | Constraint | Use |
|---|---|---|---|---|---|
| E1 | DC | `compile` (default map effort), standard synthetic library only | Nangate45 | Φ_main | ladder / candidate screening rung |
| E1d | DC | `compile` + DesignWare Foundation | Nangate45 | Φ_main | attribution: DesignWare architecture choice |
| E2 | DC | `compile_ultra` (DesignWare Foundation added by the command) | Nangate45 | Φ_main | ladder / screening rung |
| E3 | DC | `compile_ultra -retime` | Nangate45 | Φ_main | ladder |
| E4 | DC | `compile_ultra -retime -gate_clock` (wire-load-mode full effort; `-timing_high_effort_script` is a no-op on W-2024.09) | Nangate45 | Φ_main | **main scoring configuration** |
| E2r / E2g | DC | E2 plus `-retime` (E2r is an alias of E3: one run, two roles) / `-gate_clock` | Nangate45 | Φ_main | single-flag attribution |
| H1 | DC | E4 | Nangate45 | 0.1 ns | hidden: constraint shift; visible caliber of the Dr.RTL head-to-head |
| H2a | DC | E4 | ASAP7 | Φ_main(ASAP7) | hidden: technology shift |
| H2b | DC | E4 | sky130hd | Φ_main(sky130hd) | hidden: technology shift; visible caliber of the Sky130 sub-experiment |
| H3 | DC | E4 + `-spg` in topographical mode, `compile_timing_high_effort` enabled | Nangate45 + Milkyway | Φ_main | hidden: physical-aware full effort |
| H4 | PT / PrimePower | read the E4 netlist; `report_timing`; PrimePower reads the same SAIF | Nangate45 | Φ_main | hidden: signoff |
| H5 | DC | `compile_ultra -no_autoungroup -gate_clock` (no retime) | Nangate45 | Φ_main | hidden: production-representative configuration |
| K_asap7 / K_sky130hd | DC | E4 command on ASAP7 / sky130hd | ASAP7 / sky130hd | knee sweep periods | Phase 1 only: knee sweeps of the original designs on the hidden libraries (never candidates or perturbations; DECISIONS 2026-09-12), records stay visible so that Φ_main(lib) can be derived without reading the hidden DB |
| Y | Yosys + OpenSTA | `synth -top; abc -liberty; stat`; OpenSTA with the same SDC | Nangate45 | Φ_main | reference caliber (literature) |
| Ycoevo | Yosys + OpenSTA | COEVO's exact script (`flatten; opt -full; ...`), zero IO delays, `set_max_delay` in→out | Nangate45 | Φ_main | supplementary Exp1 column |
| O0/O1/O2 | Yosys/ABC | O0 = Y; O1 = `synth -flatten` + `opt -full` + `share -aggressive`; O2 = O1 + heavy ABC script (`resyn2` rounds / `dch` / `&deepsyn`) | Nangate45 | Φ_main | supplementary: open-source ladder |
| O | ORFS | Yosys + OpenROAD STA after place/CTS | Nangate45 | Φ_main | open-source reproduction layer; P&R spot checks |

Prerequisite for `-gate_clock`: `set_clock_gating_style` with defaults or as specified in config; if a design has no enable registers, an ICG count of 0 in the log is a normal result, not a failure.

## 2. Mandatory structure of DC scripts

Every DC job's Tcl is generated from templates (`src/eval/templates/dc_*.tcl`) and must contain:

1. Library reads, `analyze`/`elaborate`/`link`, each step checking **both** the Tcl return value and the command output (DC returns 0 on failure: match `Error:` and `*E-` patterns); the error count of `check_design` after `link` goes into meta.
2. After `source` of the SDC, validate: at least one clock was created (`get_clocks` non-empty), and the period equals the expected value.
3. The compile command is injected from config; after compilation: `report_qor`, `report_area -hierarchy`, `report_timing -max_paths 10 -nworst 1 -input_pins -transition_time -capacitance` (for critical-path mapping), `report_reference` (cell-type histogram), `report_resources`, `report_clock_gating` (when `-gate_clock` is on), `report_power` (default toggle rates) and `report_power` after `read_saif` (when a SAIF exists), `write -format verilog -hierarchy`, `write -format ddc`.
4. Compile-log summary: parse and store the number of datapath-extracted blocks, registers moved by retiming, ICGs inserted, list of ungrouped modules, shared-resource report, DesignWare components and implementation choices. Fields in `docs/spec/07-results-db.md`.
5. Before exiting, set `meta.json.status` to `ok` only if: all report files exist and are non-empty, area > 0, a clock exists, and the log has no unhandled Error. Otherwise `status = failed` with the reason.

Determinism: fixed DC version; `set_host_options -max_cores <config>`; two consecutive E4 runs on the same input must be bit-identical (area, WNS, histogram) — `tests/test_determinism.py`.

## 3. Knee-point constraint sweep

For each original design D and each library: under E4, sweep `config: knee.periods_ns` (7 geometrically spaced points from loose to tight), recording (T, area, WNS, TNS). Rule:
- candidate set = periods with WNS ≥ −knee.slack_tol × T;
- among them take the tightest T with area(T) ≤ (1 + knee.area_tol) × area(T_loosest);
- if the candidate set is empty, take the T with minimum TNS and set `knee_fallback = true`.
- Configurations per library: `knee.configs` (E4 on Nangate45, K_asap7 / K_sky130hd on the hidden libraries); designs tagged `multi_clock` (two or more clock ports found by use in the Phase 1 inventory) are trial-synthesized with one clock per port at the same period (`src/eval/sdc.py`: clk, clk_2, ...) but get no knee sweep and enter no search set (DECISIONS 2026-09-12).
Output `designs.phi_main_ns[lib]` and the whole curve (`knee_table_json`); attach the curves to the report. All candidates inherit the Φ_main of their D.

## 4. Power path

- With a testbench: compile D and C (separately) with VCS plus the testbench, run the testbench to completion and then `config: sim.random_cycles` cycles of constrained random stimulus after a `config: sim.reset_cycles` reset sequence; without a testbench: use the lock-step random-stimulus harness of the equivalence stack (spec 03) for `sim.random_cycles` cycles only, and set `power_confidence = low`.
- Dump VCD -> `vcd2saif` -> DC `read_saif -input x.saif -instance <top>` -> `report_power`; also record `report_power` at default toggle rates on the same netlist. PrimePower (H4) reads the same SAIF.
- Record SAIF coverage (annotated fraction from `report_saif` or `report_power`); below the config threshold, set `power_confidence = low`.

## 5. Yosys / OpenSTA / ORFS

- Y, O0–O2: commands from config; ABC scripts contain no randomization; OpenSTA reads the Yosys netlist and the same SDC for WNS/TNS; `stat -liberty` gives area and cell count.
- O: call the ORFS flow (`/home/hping/OpenROAD-flow-scripts/`), generating design directories in the ORFS convention; take STA and area after place/CTS; used for final designs and P&R spot checks.

## 6. Records and failure handling

- Every evaluation writes `results/raw/<design>/<config>/<hash>/`; `meta.json` must contain: design_id, cand_id or pert_id, config, lib, clock_ns, tool_version, git_sha, cfg_hash, start/end time, DC seconds, status, checklist results.
- Only records with `status == ok` are written to `results.sqlite.evaluations` by `src/db/ingest.py` (the evaluation service calls the DB layer; there is no separate ingest module under `src/eval/`).
- Timeout (config: `timeouts`) or crash: `status = failed`, retry once; two failures are recorded as `eval_failed`, do not enter the population, and are counted in reports.
- Seat shortage: queue backoff (config: `queue.backoff`), not counted as a failure.

## 7. Tests

- `tests/test_eval_smoke.py`: one small design through all configurations, comparing key fields against the reference artifacts in `tests/fixtures/` (fixtures may be regenerated when tool versions change; record in DECISIONS).
- `tests/test_eval_negative.py`: RTL with a syntax error, a missing SDC, and a wrong library path must each yield `status = failed` with the correct reason.
- `tests/test_determinism.py`.
- `tests/test_knee.py`: the rule picks the correct point on synthetic area–T curves; an empty candidate set takes the fallback.
