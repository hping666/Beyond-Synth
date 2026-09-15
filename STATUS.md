# STATUS — Beyond the Synthesizer

Written 2026-09-15 at the session handoff (the session of 2026-09-14/15 ends here; a fresh session continues). Read this file, then `docs/PLAN.md` Phase 5 and `reports/phase4.md`.

## Current phase and the next action

**Phase 4 (Exp1: ladder and map) is complete. STOP G5 was submitted on 2026-09-15 11:30 and is waiting for the user.** No G5 decision has been received yet: the user's last decisions on record are the block of 2026-09-14 (DECISIONS) and the deletion of the 145 test directories on 2026-09-15. Do not start Phase 5 before the user's G5 decisions are recorded verbatim in `docs/DECISIONS.md`.

Next action for the new session, in order:
1. `python3 scripts/status.py` — expect the daemon running, every pool idle, LLM 45.86 USD total.
2. If the user has answered G5: record the decisions verbatim and dated in `docs/DECISIONS.md` (Phase 5 go and any adjustments, the engineering order before Phase 5, the paper form, extra tasks), update this file, then follow `docs/PLAN.md` Phase 5 (5.1 onwards) — starting, as the user decided on 2026-09-14, with the SEQ latency mapping (G2.1(b)) on the critical path before Phase 5 and the DPV phase mapping after it.
3. If the user has not answered: engineering only, nothing that presumes the gate — the pre-Phase-5 items listed under "Open questions" (SEQ latency mapping, DPV phase mapping, B1@E4 static-complement prompt, hidden registration counts, a second `phase2_saif.py prune` pass), each small-before-large with bidirectional tests.

G5 report: `reports/phase4.md` (§1–§8 generated, §9 diagnoser check, §10 motivating figure, §11 conclusions); the conclusions file `reports/phase4_conclusions.md`; the manual check `reports/data/phase4_diagnoser_check.md`; snapshot `results/snapshots/phase4-20260915-1115/`. Headline numbers: map shape **concentrated** (B0 objects: (a) 6 %, (b) 49 %, (c1) 100 %, (d) 94 % E4 retention; all 255 diagnosed objects 15 / 43 / 88 / 73 %; materiality row 21 / 39 / 88 / 69 %); rule R misclassification P(retained | forbidden) 37 %, P(absorbed | allowed) 6 %; predictor LODO AUROC 0.717 with class / 0.733 class-blind; non-monotone 17.6 %; diagnoser check 187 / 187; literature: RTL-OPT 20 better at E1 → 11 retained at E4 of 34 proven pairs, RTLRewriter 24 → 10 of 43; B0 proven rate 24 % (1 357 candidates, 320 proven, none on spikeLayer8_H7 / drrtl_datapath / drrtl_pcie); 28 proven B0 candidates and 2 references rejected by DC (evaluation failed, rule 8).

## Pending STOP gates

| Gate | Status | Report | User decision |
|---|---|---|---|
| G0 | closed 2026-09-12 | reports/phase0.md | recorded in DECISIONS |
| G1 | closed 2026-09-13 | reports/phase2.md | rule A floors, floor classes, pooled minimum (DECISIONS 2026-09-14 G1.x) |
| G2 | closed 2026-09-13 | reports/phase2.md §4 | SEQ protocol with the all-zero initial state (G2.2); the latency mapping G2.1(b) is a pre-Phase-5 item |
| G3 | closed 2026-09-14 | reports/phase3.md | screening stays out of the main method unless AUROC ≥ 0.75 (final Phase 3 AUROC 0.721: M_noscreen dropped) |
| G4 | closed 2026-09-14 | reports/phase3.md §7 | luna main model, terra second model on M and B2, C1 scope (Exp1 = CktEvo 5 + Dr.RTL 3 + RTL-OPT 2, RTLLM as contrast), floor versioning |
| G5 | **submitted 2026-09-15 11:30 — waiting** | reports/phase4.md, reports/phase4_conclusions.md | none received yet. Asked of the user: Phase 5 go (and whether the zero proven rate of luna on the three largest designs changes the Phase 5 design set or projection); which pre-Phase-5 items to do first; the paper form (map paper, see §11) |
| G6+ | not reached | — | — |

## In-flight work

- **Queue daemon**: running, pid 945587, started with `python3 scripts/queue/daemon.py start` (setsid; it sources `~/.config/beyond-synth/env.sh` itself for `OPENAI_API_KEY`; restart with `python3 scripts/queue/daemon.py stop` then `start`). Pools: dc cap 50 / target 24, vcf cap 50 / target 24 (`queue.dc_seats_target`, `queue.vcf_seats_target`; 50 only for bulk Phase 5–6 runs on the user's confirmation), pt 8, local 16, `per_design_max {vcf: 16}`. The queue is empty (no queued or running job); nothing is waiting on the daemon.
- **Hidden worker**: no persistent process; `scripts/hidden_worker.py` is invoked per submission and its runner per job. Every E4-evaluated Phase 3 and Phase 4 object has its H1 / H2a / H2b / H3 / H5 registrations submitted; completion counts (`python3 scripts/hidden_worker.py --coverage-candidates --exp phase3` and `--exp phase4`, counts only) have not been reported yet.
- **Session-bound monitors and chains**: none survive. All of the day's chains finished before the handoff (B0 top-up chain 10:53, final collection chain 11:09, hourly progress monitor 11:44, chain monitor). Nothing needs re-creating. If a collection has to be redone: `python3 scripts/phase4_exp1.py verdicts`, `ladder --hidden --submit --priority 2` (idempotent, deterministic failures skipped), then after the queue drains `diagnose --force`, `hygiene`, `collect`, `snapshot`, `diag-sample`, `diag-verify`, `motivating`, `python3 scripts/report_phase.py phase4`.
- Hourly monitors of the old sessions were `Monitor` tasks of the Claude session (not daemon jobs); the new session creates its own if it needs them.

## Budget and hours (to the cent, 2026-09-15 12:00)

| Item | Spent | Cap (config) | Note |
|---|---|---|---|
| LLM phase3_calibration | 41.85 USD | 60 | closed |
| LLM phase4_generation | 4.01 USD | 40 | closed (28 B0 runs, 1 400 calls, plus the M6 review 0.31 USD booked to phase3_calibration) |
| LLM phase5_main | 0.00 USD | 600 | not started |
| LLM phase6_ablation | 0.00 USD | 200 | not started |
| LLM total | 45.86 USD | 1 000 | `budget_ledger` |
| DC hours (visible evaluations, cumulative) | 539.4 h | reported, not budgeted | `SUM(evaluations.dc_seconds)`; hidden-configuration hours are in the hidden database (counts only via the hidden worker) |
| VC Formal hours (search runs, cumulative) | 399.4 h | reported, not budgeted | `runs.spent_vcf_hours`: phase3 335.5, phase4 63.8, smoke 0.1; the Phase 2 pilot and noise equivalence jobs are not in `runs` |
| PT hours | 0 | — | PT not used yet |

`scripts/status.py` prints "DC / PT / VCF hours cumulative 0.00" because those counters read `budget_ledger` rows of kind dc / vcf that nobody writes — a known gap (open item), the numbers above come from the tables named.

## Data state

- Results database `results/db/results.sqlite` (append-only): 23 888 evaluations, 1 951 perturbations, 265 designs, 11 560 failed jobs (all with records or known causes), 0 active jobs; `python3 scripts/db_check.py`: 0 problems, 0 warnings (2026-09-15 12:00).
- Last snapshot: `results/snapshots/phase4-20260915-1115/` (candidates 1 474, evaluations 7 579, diagnoses 1 418, runs 122, noise_floor 7 235). Earlier: `phase4-20260915-1108` (provisional, before the band rule), `phase4-20260915-0748` (premature chain firing, superseded).
- `noise.floor_version: phase4` in force (frozen 2026-09-14 19:15); Phase 3 rows keep `phase3`.
- Hidden results only in `results/hidden/hidden.sqlite` (rule 3; read only by `scripts/report_hidden.py` after Phase 5).
- Last commit before the handoff: c4a9d3a (the handoff commit follows it; `git log -1` shows it). Working tree clean, remote `origin/main` up to date after the handoff commit.
- Tests: `pytest tests/` → **311 passed, 14 skipped (EDA tools)** on 2026-09-15 12:00 (the Yosys async-load trap test included).
- Disk: root filesystem **25 GB free of 1.8 TB (99 %)** — shared host; this project's `results/` is 83 GB after the retention prune of 2026-09-15 (38.6 GB freed); `~/.cache` of this account is 60 GB (Hugging Face model weights, the user's, not touched); the other accounts hold the rest. `/hdd1` 50 GB free.

## Open questions and known risks

- G5 decisions pending (Phase 5 go, adjustments, engineering order, paper form); nothing that presumes them may start.
- Disk: 25 GB free on a shared root filesystem; the project's own growth is controlled (retention rules of 2026-09-14, `phase2_saif.py prune` after the last runs), the rest is outside the project — tell the user before any bulk run.
- luna proved 0 of 562 candidates on spikeLayer8_H7, drrtl_datapath and drrtl_pcie (syntax errors, lock-step mismatches, SEQ counterexamples); Phase 5 projections must use the measured proven rates per design (24 % overall).
- Class (c2) has one Phase 4 object: pipelining rewrites are not on the map until the SEQ latency mapping (G2.1(b)) is implemented (pre-Phase-5, user decision 2026-09-14).
- 28 proven B0 candidates and 2 literature references are rejected by DC (25 `!|` reductions VER-294, VER-262, VER-134, ELAB-366, LINK-3); they stay `evaluation failed` and are listed in reports/phase4.md §4a; ladders skip such deterministic failures unless `--retry-failed`.
- Phase 3 search-time diagnoses were left unchanged after the diagnoser-input fixes of 2026-09-15 (power basis, band); the re-derivation changes ≤ 15 of 906 labels (addendum in reports/phase3_conclusions.md); Phase 4 / 5 use the corrected rules.
- `scripts/status.py` hour counters show 0 (ledger rows of kind dc / vcf never written) — engineering item.
- Hidden registration completion counts for Phase 3 / Phase 4 objects not yet reported (counts only).
- DPV phase mapping for fixed-latency arithmetic pipelines, the B1@E4 static-complement prompt, and whether the M6 LLM review (spec 04 A.2) is applied to Phase 4 / 5 objects (`phase3_calibrate.py m6-review --exp phase4`) are open pre-Phase-5 items.
- Traps: 2026-09-15 Yosys async-load flip-flops (`if (rst) q <= <signal>`) stay behavioural in the netlist — the runner's structural check rejects them (eda-knowledge/05-traps.md, test in tests/test_yosys_netlist_offline.py).

## Resume checklist (run first, in this order)

```bash
cd /home/hping/Beyond-Synth && source .venv/bin/activate
python3 scripts/status.py            # healthy: "daemon: running", every pool running=0 waiting=0, LLM total 45.86 USD, key configured, 0 orphan EDA processes
python3 scripts/queue/daemon.py status   # healthy: "daemon: running pid=945587" (if not running: python3 scripts/queue/daemon.py start)
python3 scripts/db_check.py          # healthy: "0 problems, 0 warnings"
pytest tests/ -x -q                  # healthy: 311 passed, 14 skipped (EDA tests skipped without the tool environment on PATH)
git status --short && git log --oneline -3   # healthy: clean tree, HEAD = the handoff commit
df -h / | tail -1                    # watch the shared root filesystem (25 GB free at the handoff)
python3 scripts/phase4_exp1.py status | tail -3   # 28 B0 runs done, phase4 spend 4.007 USD
```
Then: `docs/DECISIONS.md` (tail, 2026-09-15 entries), `reports/phase4.md` §11, `docs/PLAN.md` Phase 5.

## Done on 2026-09-15 (this session, chronological; details in DECISIONS)

- Night audit: 328 failed queue jobs were candidate-RTL faults rejected by the synthesizer; `phase4_exp1.py hygiene` lists them (report §4a).
- Retention defect fixed: sim_fail records skipped the VCD rules (`retain_vcd`); the approved prune freed 38.6 GB.
- Search-driver run directory now follows `project.results_dir` (test isolation; the flaky B0 test); the user approved deleting the 145 test directories.
- Ladders skip deterministic evaluation failures (`--retry-failed` to force), visible and hidden.
- PLAN 4.6 / 4.9 tooling: `diag-sample`, `diag-verify` (independent re-derivation from the raw DC reports), `motivating`; the collection chain re-run with a strict completion condition.
- Three diagnoser-input defects found by the check and fixed: mixed SAIF / default power bases, zero band for missing floor components (pooled minimum now), convergence test on sigma_robust (rule-A band now); every Phase 4 object re-diagnosed; Phase 3 impact estimated (addendum).
- D baselines of the 76 literature designs under E1d / E2g / Y / O0–O2 / Ycoevo added (`baselines --objects`).
- Phase 4 completed: final collect, diagnoser check 187 / 187, motivating figure, conclusions, STOP G5 submitted.


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
