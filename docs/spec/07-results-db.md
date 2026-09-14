# spec 07 — Results database `results/db/results.sqlite` (the hidden DB `results/hidden/hidden.sqlite` uses the same `evaluations` schema)

Every table carries `created_at`, `git_sha`, `cfg_hash`. Writes go only through `src/db/ingest.py`; reads for analysis only through `src/db/query.py`. At the end of each phase, `scripts/snapshot.py` exports parquet files to `results/snapshots/<phase>-<date>/`.

## designs
design_id, suite, name, path, loc, ports_hash, tb_available, sdc_available, e4_synthesizable, e4_fail_reason, phi_main_ns_nangate45, phi_main_ns_asap7, phi_main_ns_sky130hd, knee_table_json, split (dev|held), tags (e.g. cktevo_sky130), source_url, source_commit, license

## perturbations
pert_id, design_id, ptype (P0_roundtrip, P1_rename, P1_text, P2_reorder, P3_expr, P4_ctrl), path, seq_status, created_at

## evaluations
eval_id, design_id, cand_id (nullable), pert_id (nullable), is_baseline, config (E1…H5, Y, O0–O2, O, PT), lib, clock_ns, area_um2, cells, wns_ns, tns_ns, crit_delay_ns, power_saif_mw, power_default_mw, saif_coverage, power_confidence, hist_json (cell-type histogram), log_summary_json (datapath_blocks, retimed_regs, icg_count, ungrouped_modules, shared_resources), resources_json (DesignWare components and implementations), crit_path_json (endpoints, RTL lines traversed), dc_seconds, tool_version, status (ok|failed|eval_failed), raw_dir

## noise_floor
design_id, config, metric, sigma_robust, sigma_std, q95_abs, max_abs, n, abs_unit_value, t_d (rule-A threshold), floor_class (quiet|spread|offset), floor_source (measured|pooled), pooled_min (the pooled q90 of the configuration and metric) — DECISIONS 2026-09-14 G1.1 / G1.2

## runs
run_id, exp (phase3|phase4|phase5|ablation), arm, skeleton, design_id, seed, llm_model, prompt_version, screening_enabled, e_s, budget_llm_calls (primary caliber), llm_calls, budget_dc_hours (reporting), spent_dc_hours, spent_vcf_hours, spent_usd, gens_done, status, started_at, finished_at

## candidates
cand_id (content hash), run_id, design_id, gen, parent_id, arm, class_requested, class_rule, class_llm, class_final (the produced class), subtags_json, confidence, prompt_hash, llm_model, tokens_in, tokens_cached, tokens_out, cost_usd, rtl_path, prescreened (0|1), v1_status, v2_status, v2_cycles, latency_offset_json, v3_status, v3_seconds, seq_cap_min, time_to_verdict_s, v4_status, counterexample_path, proven_by, in_archive (0|1), accepted (0|1)

## screening
cand_id, e_s, g_es_json, fp_converged_es, p_retained, tau, promoted (0|1), audited (0|1)

## diagnoses
cand_id, label (retained|absorbed|absorbed_identical|duplicate|noise|harmful|tradeoff|fragile|nonequiv|prescreened|screened_out), rung, capability, attribution (measured|prior), fp_jaccard, offset_design (0|1), duplicate_of (cand_id), envelope_json (the acceptance-envelope runs of C2.1(d)), seq_audit (0|1), seq_audit_result (proven|falsified|inconclusive|null), evidence_json, feedback_json, credit (0|1), credited_class — DECISIONS 2026-09-14 C2.4

## gen_summary
run_id, gen, archive_json, bandit_probs_json, tau, e_s, spent_dc_hours_cum, spent_usd_cum, retained_count_cum

## budget_ledger
ts, phase, kind (dc|pt|vcf|llm), amount, unit (hours|usd), run_id, note

## jobs (queue)
job_id, kind, design_id, cand_id, config, priority, state (queued|running|done|failed|backoff), attempts, host_pid, log_path, submitted_at, started_at, finished_at

## Hidden DB hidden.sqlite
`evaluations` (as above, config ∈ {H1,H2a,H2b,H3,H4,H5}), `audits` (cand_id, reason ∈ {accepted, rejected_sample}). Written only by `scripts/hidden_worker.py`, read only by `scripts/report_hidden.py`.

## Consistency checks (`scripts/db_check.py`, run before every phase report)
- Every candidate with `accepted=1` has records for all configurations in the hidden DB (Phase 5).
- Every `evaluations.status=ok` record has `raw_dir/meta.json.status == ok`.
- `runs.spent_*` agree with the `budget_ledger` totals.
- No duplicate ok records for the same (design_id, cand_id, config) (a re-run must produce a new hash directory and be explained in DECISIONS).
