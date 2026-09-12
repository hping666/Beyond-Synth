# spec 08 — Analysis and reporting `src/analysis/`, `scripts/report_*.py`, `scripts/paper_tables.py`

Read only the results database and snapshots; every plotting function takes a snapshot path and writes to `reports/figs/` or `paper/`, with file names containing the snapshot name and git sha.

## 1. Map (C1)

- Cell: class_final (with sub-tags) × configuration (E1, E2, E3, E4, single flags, H1, H2a, H2b, H5).
- Per cell: number of candidates; fraction with g > 2σ_D(that configuration) (retention rate); distribution of retained magnitude (median, IQR); distribution of absorption rung (permanent-absorption definition); distribution of capability attribution (measured and prior separately).
- Retention curves: per class, the retention rate from E1 to E4 as a line, with the H columns appended.
- Non-monotone cases: list and fraction of candidates whose g re-exceeds the band at a higher rung.
- Literature settings re-evaluation: for the RTL-OPT 36 pairs and RTLRewriter 20 pairs, the number of pairs where the optimized version is better under each rung, side by side with the papers' original numbers.
- Static-rule misclassification rates: define rule set R (forbidden: syntactic rewrites, state re-encoding, explicit sharing, hand-written gating; allowed: everything else); report P(retained | forbidden by R) and P(absorbed | allowed by R).

## 2. Predictor

- Training set: all Phase 4 objects; target: E4 retention; features per spec 05 §3.
- Evaluation: leave-one-design-out cross-validation; AUROC, precision/recall curves, precision at the τ giving recall ≥ 85%; class-blind control.
- Output the model file and feature importances; report performance on held-out designs.

## 3. Search comparison (C2)

- Main figure: per arm, retained gain (geometric mean, three metrics separately) vs cumulative DC hours, mean and band over 3 seeds; one figure for E4 and one per hidden configuration.
- Table: final retained gain, speculation rate, retained candidates per DC hour, SEQ pass rate per class, inconclusive rate per class, operator-distribution drift (last vs first generation), fraction of expert gain recovered on RTL-OPT, Dr.RTL head-to-head (ratio of DC hours at equal gain, or ratio of gain at equal DC hours).
- Significance: paired (same design, same seed) Wilcoxon; report the fraction of designs on which M exceeds B2, and M exceeds B1@E4, by more than 2σ_D (target ≥ 60%).

## 4. Ablations

Per variant, mean ± standard deviation over 3 seeds; difference relative to M with a paired test; one separate table.

## 5. Report scripts

- `report_phase.py <phase>`: generate `reports/<phase>.md` from snapshots (template `reports/TEMPLATE.md`), with key-number tables and figure links.
- `report_hidden.py`: runs only after Phase 5 is complete; produces the hidden-layer part (speculation rates, hidden curves, reverse error).
- `paper_tables.py`: generates all paper tables (LaTeX) and figures (PDF), each annotated with snapshot and git sha.

## 6. Conventions for numbers

- Gains are always relative to that design's D under the same configuration; convert to ratios before geometric means.
- Small designs are also reported in absolute units (cell counts, ps).
- Any cross-tool (Yosys vs DC) side-by-side table goes to internal reports by default; inclusion in the paper follows the license conclusion in DECISIONS.
