# spec 02 — Noise floor `src/noise/`

Responsibility: for each original design D, measure "how sensitive the synthesizer is to semantics-preserving surface rewrites", yielding σ_D per configuration and metric, and produce D's baseline records under every configuration.

## 1. Perturbation types (Pyverilog AST transforms, rule-based, no LLM)

| Type | Transform | Constraint |
|---|---|---|
| P1 rename | internal signals, registers, parameter names (ports and module names untouched) | names from a fixed word list + index, deterministic |
| P2 reorder | independent `assign` statements, independent `always` blocks, statements without data dependence inside an `always` | dependence analysis guarantees semantics; never across blocking-assignment dependences |
| P3 equivalent expressions | De Morgan; constant notation (decimal <-> hexadecimal <-> sized); bit-select notation (`x[3:0]` <-> concatenation) | widths kept explicit |
| P4 control structure | `if-else` chain <-> `case` (when mutually exclusive and complete); ternary <-> `if` | only when exclusivity and completeness are provable |

Per design, generate `config: noise.n_per_type` per type (default 4; `noise.n_per_type_spread_offset` = 8 for the Exp1 map designs and for every design whose floor class is spread or offset, DECISIONS 2026-09-14 G1.3). If a type has no applicable location, record "type not applicable". The unmodified re-print P0 is itself a member of the noise set (ptype `P0_roundtrip`, DECISIONS 2026-09-13). Designs whose AST perturbations exist but none is SEQ-proven (the re-print does not compile or its round trip fails) get text-level P1 renamings instead (`src/noise/rename_text.py`: regex renaming of the identifiers listed by Pyverilog's parse, the printer bypassed; ptype `P1_text`; DECISIONS 2026-09-14 G1.2), so that at least a P1 floor exists.

## 2. Gating

Every perturbation first passes V1 + V3 (SEQ) of the equivalence stack; perturbations that are not proven are **discarded** and counted — the generator's non-equivalence rate per type is reported as a generator-quality metric (it also supplies positive test cases for SEQ).

## 3. Runs

D and all proven perturbations run under E1, E2, E3, E4, H1, H2a, H2b, H5; H3 only for D and one perturbation per type (`config: noise.configs_light`). H4 has no separate floor: the speculation test under H4 uses σ_D(E4), because PrimeTime re-times the same E4 netlists. All runs go through `src/eval/` and the queue and are recorded in `evaluations` (`pert_id` set).

## 4. Statistics

For each (design, config, metric ∈ {area, wns, tns, power_saif}):
- relative deviation δ_i = (m_i − m_D) / m_D over D's proven perturbations including P0 (for wns and tns use (m_i − m_D) / T_clk to avoid division by zero);
- σ_robust = 1.4826 × MAD(δ); also store std(δ), q95(|δ|), max(|δ|), n;
- **threshold rule A** (DECISIONS 2026-09-14, G1.1): t_D = max(k_sigma × σ_robust, max|δ| over D's own proven perturbations including P0, pooled q90 of |δ| over all perturbation records of that configuration and metric; `noise.k_sigma` = 2, `noise.pooled_quantile` = 0.90). The pooled quantile is the minimum: it is the floor of designs whose perturbations never change the netlist. σ_robust and the 1σ / 2σ / 3σ sensitivity (`noise.k_sigma_sensitivity`) stay in the report;
- **floor class** per design and configuration (`noise.floor_classes`): quiet (every |δ_area| ≤ `noise.quiet_max_abs`), offset (median |δ| above that and MAD ≈ 0: every perturbation shifted together), spread otherwise; stored next to the floor. A retained gain on an offset design is flagged in every table and in the map;
- **floor_source**: `measured` (n ≥ 2) or `pooled` (a design without a measured floor uses the pooled minimum, `noise.pooled_floor_for_missing`; Exp1 map designs must have a measured floor);
- **materiality sensitivity** (`noise.materiality`): every headline number is reported a second time under a fixed threshold (area 1 %, power 2 %, WNS 1 % of the period) as a sensitivity row;
- for small designs also store an absolute threshold (area in cell count).
Write to the `noise_floor` table (columns in spec 07).

## 5. Baselines

D's record under each configuration (the unperturbed one) is marked `is_baseline = 1`; its cell histogram, log summary, resource report and critical path are the references for the fingerprint-convergence test and the diagnoser.

## 6. Report content

σ_robust and t_D distribution per configuration; floor-class counts (quiet / spread / offset) and the number of pooled floors; per-design "minimum reportable gain" table (t_D, three metrics) with the 1/2/3 σ and the materiality sensitivity rows; monotonicity statistics of D itself from E1 to E4 (how many designs are non-monotone in area, in WNS); perturbation non-equivalence rate per type; σ_D under H1/H2/H5 compared with E4 (hidden report).

## 7. Tests

- Positive: a legal renaming perturbation -> SEQ proven, E4 area delta within 2σ.
- Negative: a "perturbation" that deliberately changes a bit width -> SEQ falsified, discarded and counted.
- Statistics functions: numeric tests of MAD/q95 on known distributions.

## 8. Implementation notes (2026-09-12)

- Generator: `src/noise/vast.py` (Pyverilog front end, text normalisation), `src/noise/perturb.py` (P1–P4), `src/noise/generate.py` (files under data/perturbations/<design_id>/, manifest.json, gitignored RTL). The unmodified Pyverilog re-print is written as `roundtrip.v` (P0) and gated like a perturbation: it isolates re-print defects from transform defects. Designs Pyverilog cannot parse, or that declare registers with initial values (re-printed as continuous assignments), get no AST perturbations; both are recorded in the manifest and in reports/data/phase2_perturbations.json.
- Gate (§2): `scripts/phase2_perturb.py gate` submits one `vcf` job per perturbation; `collect` fills `perturbations.seq_status` with the stack verdict; only `proven` enters the floor. A Yosys timeout in V1 is an `error` verdict, never a rejection.
- Runs (§3): visible configurations through `scripts/phase2_noise.py submit` (E1–E4 at Φ_main); hidden configurations through `scripts/hidden_worker.py --submit-noise` (queue kind `dc_hidden`, records in the hidden database only). Statistics (§4): `src/noise/stats.py`; visible rows by `scripts/phase2_noise.py collect`, hidden rows by `scripts/hidden_worker.py --noise-floor` (counts only). The §6 comparison of σ_D under H1 / H2 / H5 with E4 is therefore part of the hidden report (scripts/report_hidden.py, after Phase 5).
- SAIF (§3–§4, 2026-09-13): the switching activity of every run comes from the lock-step VCD of the latest equivalence record (`src/noise/saif.py`, `scripts/phase2_saif.py build`): `vcd2saif -instance bs_lockstep/u_d` for D (round-trip record) and `bs_lockstep/u_c` for a perturbation, files under data/perturbations/<design_id>/saif/ with saif.json; the DC job carries `saif` / `saif_instance` (part of the evaluation hash) and DC reads it with `read_saif -instance <same path> -auto_map_names`. `power_saif_mw` is null only for the designs whose round trip never simulated (no usable perturbations either). σ_D collection (`src/noise/stats.pick_records`) prefers a SAIF-backed record over a SAIF-less one of the same (design, config, clock) and takes the latest among equals.
- Round trip as a perturbation (2026-09-13, DECISIONS): the SEQ-gated re-print P0 is stored in `perturbations` (ptype `P0_roundtrip`) and evaluated under every noise configuration; its deviation from D measures the re-print's own effect (layout, declaration order, constant formats), which for some designs is the largest surface effect of all. Report §2a classifies each design as quiet / spread / offset (all perturbations shifted together).
- Rule A, floor classes, pooled floors and the materiality sensitivity (2026-09-14, DECISIONS): computed by `src/noise/stats.py` (`floor_rows` with the pooled minimum passed in, `floor_class`), written by `scripts/phase2_noise.py collect` and `scripts/hidden_worker.py --noise-floor`; the pooled minimum per (configuration, metric) is computed over the set designs' perturbation records first, then every design row gets `t_d`, `floor_class`, `floor_source`, `pooled_min`; designs without a measured floor get a `pooled` row with n = 0.
