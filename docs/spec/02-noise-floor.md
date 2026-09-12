# spec 02 — Noise floor `src/noise/`

Responsibility: for each original design D, measure "how sensitive the synthesizer is to semantics-preserving surface rewrites", yielding σ_D per configuration and metric, and produce D's baseline records under every configuration.

## 1. Perturbation types (Pyverilog AST transforms, rule-based, no LLM)

| Type | Transform | Constraint |
|---|---|---|
| P1 rename | internal signals, registers, parameter names (ports and module names untouched) | names from a fixed word list + index, deterministic |
| P2 reorder | independent `assign` statements, independent `always` blocks, statements without data dependence inside an `always` | dependence analysis guarantees semantics; never across blocking-assignment dependences |
| P3 equivalent expressions | De Morgan; constant notation (decimal <-> hexadecimal <-> sized); bit-select notation (`x[3:0]` <-> concatenation) | widths kept explicit |
| P4 control structure | `if-else` chain <-> `case` (when mutually exclusive and complete); ternary <-> `if` | only when exclusivity and completeness are provable |

Per design, generate `config: noise.n_per_type` per type (default 4; 8 for the 10 map designs). If a type has no applicable location, record "type not applicable".

## 2. Gating

Every perturbation first passes V1 + V3 (SEQ) of the equivalence stack; perturbations that are not proven are **discarded** and counted — the generator's non-equivalence rate is itself reported (it measures generator quality and supplies positive test cases for SEQ).

## 3. Runs

D and all proven perturbations run under E1, E2, E3, E4, H1, H2a, H2b, H5; H3 only for D and one perturbation per type (`config: noise.configs_light`). H4 has no separate floor: the speculation test under H4 uses σ_D(E4), because PrimeTime re-times the same E4 netlists. All runs go through `src/eval/` and the queue and are recorded in `evaluations` (`pert_id` set).

## 4. Statistics

For each (design, config, metric ∈ {area, wns, tns, power_saif}):
- relative deviation δ_i = (m_i − m_D) / m_D (for wns use (wns_i − wns_D) / T_clk to avoid division by zero);
- σ_D = 1.4826 × MAD(δ) (robust standard deviation); also store std(δ), q95(|δ|), max(|δ|), n;
- decision threshold t = 2σ_D (config: `noise.k_sigma`), with a 1σ/2σ/3σ sensitivity report; for small designs also store an absolute threshold (area in cell count).
Write to the `noise_floor` table.

## 5. Baselines

D's record under each configuration (the unperturbed one) is marked `is_baseline = 1`; its cell histogram, log summary, resource report and critical path are the references for the fingerprint-convergence test and the diagnoser.

## 6. Report content

σ_D distribution per configuration; per-design "minimum reportable gain" table (2σ_D, three metrics); monotonicity statistics of D itself from E1 to E4 (how many designs are non-monotone in area, in WNS); perturbation non-equivalence rate; σ_D under H1/H2/H5 compared with E4.

## 7. Tests

- Positive: a legal renaming perturbation -> SEQ proven, E4 area delta within 2σ.
- Negative: a "perturbation" that deliberately changes a bit width -> SEQ falsified, discarded and counted.
- Statistics functions: numeric tests of MAD/q95 on known distributions.
