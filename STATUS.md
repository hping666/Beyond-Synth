# STATUS — Beyond the Synthesizer

Written 2026-09-15 at the session handoff (the session of 2026-09-14/15 ends here; a fresh session continues). Read this file, then `docs/PLAN.md` Phase 5 and `reports/phase4.md`.

## Current phase and the next action

**Phase 4 complete; G5 decided; the storage decision of 2026-09-15 (option A) executed; the approved re-runs (pilot latency mapping, LLM review, RTL-OPT authors' setting) are done and reported. The next action is the user's: review the B1@E4 static complement text and the B1 prefix assembly (decision 2026-09-15 item 6, pasted in the session's final message and reproducible with the snippet below); after that review the large-design correctness probe starts (`python3 scripts/phase5_probe.py create --submit`, 12 runs, cap 120 USD).**

State of the decisions of 2026-09-15 (DECISIONS, verbatim entry + implementation entries):
1. Storage (option A + the sim_fail VCD amendment): done. `prune_scratch.py --tiered --apply` freed 40.36 GB of record artifacts and 11.06 GB of M6 workdirs; root filesystem **86.8 GB free** (26.4 before); results/raw 35.9 GB; db_check 0 problems. The seeded 5 % sim_fail VCD sample (`retention.sim_fail_vcd_sample`) applies at record time and in the prune. ~/.cache (63.4 GB) untouched — the user's separate call (option B).
2. Phase 5 scenarios: `exp5.hidden_scope` H1 / H3 / H5 on every E4-evaluated candidate, H2a / H2b / H4 on accepted + audit sample; `exp5.ladder_on_accepted: phase6` unless option B happens.
3. Pilot latency re-run: done — 28 class-(c2) candidates × 2 seeds: 26 proven on both seeds, 2 falsified (rtllm_multi_16bit); reports/phase2.md §4b. (c2) enters the map row only.
4. gpt-5.6-sol prices: the live page (developers.openai.com/api/docs/pricing, 2026-09-15) shows 4.00 / 0.40 / 20.00 standard and 2.00 / 0.20 / 10.00 Flex, not the 5.00 / 0.50 / 30.00 and 2.50 / 0.25 / 15.00 of the decision; config corrected per item 4 (DECISIONS entry with URL and date).
5. LLM review: done — 23 Phase 4 objects, 8 class changes (b→a 2, c1→a 1, c1→c2 5), B0 map rows untouched, shape concentrated, predictor AUROC 0.717 → 0.710; snapshot phase4-20260915-review; 0.007 USD. RTL-OPT authors' setting: done — E2_1ns on the 34 proven pairs: 13 better / 4 same / 16 worse / 1 not linkable by area; the paper's 35 of 36 is not reproduced; the authors' released reports are `compile` at 0.1 ns (all 34 better there); reports/phase4.md §4d.
6. Pre-probe review: the static complement text and the B1 prefix assembly were pasted for the user; the probe has not been created.

To reproduce the review material: `python3 - <<'EOF'` with the snippet in reports/data/b1_prefix_review_snippet.md (or read src/search/prompts/static_complement.md directly); the probe command afterwards: `python3 scripts/phase5_probe.py create --submit`, then `status`.

**Still to do before Phase 5 (engineering, no user decision needed):** the Phase 5 hidden-layer certification loop in `scripts/hidden_worker.py` (accepted candidates + the audit sample by `retention.is_audit_sample`, H1 / H3 / H5 on all E4-evaluated per `exp5.hidden_scope`); `scripts/phase5_sets.py` (18 medium / 6 small / 6 large held starting points, `exp5.tiers`); the Phase 5 run creation for five arms × 30 × 3 seeds and terra on M / B2; `vcf_seats_target` 50 in bulk mode (config, on the user's word); the DPV phase mapping only if time remains (G5 item 2 (v)).

G5 report: `reports/phase4.md` (regenerated 2026-09-15 after the review; §4c duplicates, §4d RTL-OPT setting), `reports/phase4_conclusions.md`; snapshots `phase4-20260915-1115` (the G5 submission) and `phase4-20260915-review`. Headline numbers unchanged: map shape **concentrated** (B0: (a) 6 %, (b) 49 %, (c1) 100 %, (d) 94 %; all objects 16 / 43 / 88 / 73 %); rule R 37 % / 6 %; B0 proven rate 24 % (0 on the three largest designs).

## Pending STOP gates

| Gate | Status | Report | User decision |
|---|---|---|---|
| G0 | closed 2026-09-12 | reports/phase0.md | recorded in DECISIONS |
| G1 | closed 2026-09-13 | reports/phase2.md | rule A floors, floor classes, pooled minimum (DECISIONS 2026-09-14 G1.x) |
| G2 | closed 2026-09-13 | reports/phase2.md §4 | SEQ protocol with the all-zero initial state (G2.2); the latency mapping G2.1(b) implemented and confirmed on the pilot (26 of 28 proven, §4b) |
| G3 | closed 2026-09-14 | reports/phase3.md | screening stays out of the main method unless AUROC ≥ 0.75 (final Phase 3 AUROC 0.721: M_noscreen dropped) |
| G4 | closed 2026-09-14 | reports/phase3.md §7 | luna main model, terra second model on M and B2, C1 scope, floor versioning |
| G5 | closed 2026-09-15 (decided) | reports/phase4.md, reports/phase4_conclusions.md | Phase 5 go with four adjustments; engineering order; map paper; four additional tasks; tiered storage policy (DECISIONS 2026-09-15 "G5 decisions") |
| Storage decision | closed 2026-09-15 (option A executed) | reports/data/phase5_footprint.md | 86.8 GB free; ~/.cache the user's call |
| Pre-probe review | **open** | src/search/prompts/static_complement.md, the B1 prefix assembly | the probe starts after the user's review (decision 2026-09-15 item 6) |
| G6+ | not reached | — | — |

## In-flight work

- **Queue daemon**: running, pid 945587; pools dc cap 50 / target 24, vcf cap 50 / target 24, pt 8, local 16. Queue empty after the E2_1ns runs (68 done, 1 failed: the mux_dead reference, LINK-3), the pilot re-run (56 done) and the review job (done).
- **Hidden worker**: no persistent process; Phase 5 certification loop not written yet.
- No session-bound monitors or chains.

## Budget and hours (to the cent, 2026-09-15 17:15)

| Item | Spent | Cap (config) | Note |
|---|---|---|---|
| LLM phase3_calibration | 41.85 USD | 60 | closed |
| LLM phase4_generation | 4.02 USD | 40 | closed (+0.007 USD for the review of the Phase 4 objects) |
| LLM phase5_probe | 0.00 USD | 120 | not started (waits for the pre-probe review) |
| LLM phase5_main | 0.00 USD | 600 | not started |
| LLM phase6_ablation | 0.00 USD | 200 | not started |
| LLM total | 45.86 USD | 1 000 | `budget_ledger` |
| DC hours (visible evaluations, cumulative) | ≈ 541 h | reported, not budgeted | + 68 E2_1ns runs today |
| VC Formal hours (search runs, cumulative) | 399.4 h | reported, not budgeted | the pilot re-run (56 jobs, ≈ 0.7 h) is not a run |
| PT hours | 0 | — | PT not used yet |

`scripts/status.py` prints "DC / PT / VCF hours cumulative 0.00" because those counters read `budget_ledger` rows of kind dc / vcf that nobody writes — a known gap (open item).

## Data state

- Results database `results/db/results.sqlite` (append-only): 23 956 evaluations (+68 E2_1ns), 1 951 perturbations, 265 designs, 3 035 candidates; `db_check.py`: 0 problems, 0 warnings after the prune. Schema additions of 2026-09-15: `candidates.repair_of`, `candidates.scope_json`, diagnoses label `scope_violation`, runs exp `phase5_probe` (older databases rebuilt on connect).
- Snapshots: `phase4-20260915-review` (after the LLM review), `phase4-20260915-1115` (the G5 submission).
- `noise.floor_version: phase4` in force. Hidden results only in the hidden database (rule 3).
- Records slimmed under the tiered policy carry a `slimmed` marker; accepted candidates, the 10 % audit sample, literature objects and failed records keep their full artifacts.
- Tests: `pytest tests/` → **349 passed, 15 skipped**.
- Disk: root filesystem 86.8 GB free; `results/raw` 35.9 GB; `/hdd1` 53 GB free; `~/.cache` 63.4 GB.

## Open questions and known risks

- Pre-probe review pending (decision 2026-09-15 item 6); the probe needs it. gpt-5.6-sol prices differ from the decision's figures (config follows the live page; see DECISIONS).
- The large tier's proven rate for terra / sol is unknown until the probe (the footprint projection assumes 10 %).
- RTL-OPT's Table 1 count (35 of 36 under compile_ultra 1 ns) is not reproduced (13 of 33 better); a run of the authors' exact script would isolate the remaining differences (68 DC runs) — proposal, not scheduled.
- Scope-limited rewriting on single-module designs restricts the model to the always blocks of the critical endpoints; the violation rate is a Phase 5 metric (`exp5.correctness_aids.scope.single_module: module` widens it, a recorded config change).
- `scripts/status.py` hour counters show 0 (ledger rows of kind dc / vcf never written) — engineering item.
- Hidden registration completion counts for Phase 3 / Phase 4 objects not yet reported (counts only).

## Resume checklist (run first, in this order)

```bash
cd /home/hping/Beyond-Synth && source .venv/bin/activate
python3 scripts/status.py            # healthy: "daemon: running", every pool running=0 waiting=0, LLM total 45.86 USD, key configured, 0 orphan EDA processes
python3 scripts/queue/daemon.py status   # healthy: "daemon: running pid=945587" (if not running: python3 scripts/queue/daemon.py start)
python3 scripts/db_check.py          # healthy: "0 problems, 0 warnings"
pytest tests/ -x -q                  # healthy: 349 passed, 15 skipped
git status --short && git log --oneline -3   # healthy: clean tree
df -h / | tail -1                    # ≈ 87 GB free after the prune of 2026-09-15
python3 scripts/phase5_probe.py status   # no runs until the user's review; afterwards `create --submit`
```
Then: `docs/DECISIONS.md` (tail, the 2026-09-15 entries after "Decisions on the storage estimate"), `reports/phase4.md` §4b–§4d, `docs/PLAN.md` Phase 5.

## Done on 2026-09-15 after the gate (chronological; details in DECISIONS)

- Resume checklist green; G5 decisions recorded verbatim; config `scale.starting_points` 30, `exp5` section.
- Phase 5 storage footprint measured and projected; B1@E4 static complement prompt; SEQ latency mapping; scope-limited rewriting and the repair call; tiered retention mechanism; G5 item 4 (b) (c) (d).
- Decisions of 2026-09-15 recorded and implemented: sim_fail VCD 5 % sample, sol prices from the live page, E2_1ns, hidden scope, probe script, map prior for arm M.
- Tiered prune applied (86.8 GB free); pilot latency re-run (26 / 28 proven); LLM review of 23 Phase 4 objects; E2_1ns on the 34 RTL-OPT pairs (13 better); reports regenerated; snapshot phase4-20260915-review.


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
