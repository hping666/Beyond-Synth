# spec 06 — Hidden layer and certification `scripts/hidden_worker.py`, `scripts/report_hidden.py`

## 1. Configurations

H1 (0.1 ns), H2a (ASAP7, its own knee constraint), H2b (sky130hd, its own knee constraint), H3 (`-spg`), H4 (PrimeTime timing + PrimePower power, reading the E4 netlist and the same SAIF), H5 (`compile_ultra -no_autoungroup -gate_clock`). Definitions in spec 01.

H4 as wired (2026-09-15, config `noise.configs_signoff`): a signoff configuration has no perturbation runs (σ_D(H4) := σ_D(E4), §3); the hidden worker registers one PrimeTime / PrimePower job for D (the E4 baseline record at Φ_main, never a knee-sweep record at another period) and one for every accepted or archived candidate and every audit-sample candidate of an experiment — in every experiment, since the speculation rate is defined on accepted candidates — provided the object's E4 record still holds `netlist.v` and `design.sdc` (the tiered retention removes them for the other candidates; those are counted as skipped, not failed). The jobs run as the `dc_hidden` kind of the hidden worker in the queue's `pt` pool (`queue.pt_seats_max`, `timeouts.pt`); the record carries PrimeTime's WNS / TNS and PrimePower's power on the same SAIF as E4, no area of its own (the E4 netlist's area is E4's).

## 2. Isolation

- `hidden_worker.py` is a separate process: it reads "candidates awaiting certification" from the queue table (the search process registers cand_id when a candidate enters the archive and passes no results), runs H1–H5, and writes `results/hidden/hidden.sqlite`.
- Search code (`src/search/`, prompt templates, predictor) never imports any module that reads `hidden.sqlite`; `tests/test_isolation.py` asserts this by static scanning.
- `.claude/settings.json` denies reads of `results/hidden/`, with `scripts/report_hidden.py` as the only exception.
- Until all Phase 5 runs are finished, no analysis, report, or prompt change may use hidden results; `report_hidden.py` may run only after the Phase 5 completion marker appears in `STATUS.md` (checked inside the script).

## 3. Metrics

- Speculation rate(H) = fraction of visible-layer accepted candidates (proven and E4-retained) whose gain under H is ≤ 2σ_D(H) or negative, per configuration (σ_D(H4) := σ_D(E4); σ_D(H3) comes from the reduced perturbation set); combined = fraction vetoed by any configuration; reported per generation, per arm, per rewrite class.
- Reverse error: a random 10% of visible-layer rejected candidates also run the hidden layer to estimate "rejected visibly, acceptable hidden".
- Retained-gain-vs-DC-hour curves under hidden configurations per arm are produced by `report_hidden.py` and shown side by side with the visible-layer curves.

## 4. Physical layer and P&R spot checks

- H3 uses DC `-spg` (verified usable in Phase 0).
- Final-design spot checks: sample final candidates and their D per suite, run ORFS through place & route and signoff STA, report the shrinkage from E4 to post-layout area/timing; also report the retention fraction under the open-source reproduction layer O (Yosys+ABC+OpenROAD). Spot-check results are a separate table, never mixed with the hidden layer.

## 5. Tests

- Isolation static scan; `report_hidden.py` must refuse to run when the completion marker is absent.
- Negative: a synthetic case with a gain only under Φ_main and none at 0.1 ns must be counted as speculation by H1.
