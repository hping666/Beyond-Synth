-- Beyond-Synth results database schema (docs/spec/07-results-db.md).
-- Idempotent (CREATE ... IF NOT EXISTS only). Every table carries created_at, git_sha, cfg_hash.
-- The hidden DB (results/hidden/hidden.sqlite) reuses `evaluations` and `audits`; it is created and written
-- only by scripts/hidden_worker.py and read only by scripts/report_hidden.py.

CREATE TABLE IF NOT EXISTS designs (
  design_id TEXT PRIMARY KEY,
  suite TEXT NOT NULL, name TEXT, path TEXT, loc INTEGER, ports_hash TEXT,
  tb_available INTEGER, sdc_available INTEGER, e4_synthesizable INTEGER, e4_fail_reason TEXT,
  phi_main_ns_nangate45 REAL, phi_main_ns_asap7 REAL, phi_main_ns_sky130hd REAL, knee_table_json TEXT,
  split TEXT CHECK (split IN ('dev', 'held') OR split IS NULL),
  tags TEXT, source_url TEXT, source_commit TEXT, license TEXT,
  created_at TEXT NOT NULL, git_sha TEXT NOT NULL, cfg_hash TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS perturbations (
  pert_id TEXT PRIMARY KEY,
  design_id TEXT NOT NULL, ptype TEXT NOT NULL CHECK (ptype IN ('P0_roundtrip', 'P1_rename', 'P2_reorder', 'P3_expr', 'P4_ctrl')),
  path TEXT NOT NULL, seq_status TEXT,
  created_at TEXT NOT NULL, git_sha TEXT NOT NULL, cfg_hash TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS evaluations (
  eval_id INTEGER PRIMARY KEY AUTOINCREMENT,
  design_id TEXT NOT NULL, cand_id TEXT, pert_id TEXT, is_baseline INTEGER NOT NULL DEFAULT 0,
  config TEXT NOT NULL, lib TEXT, clock_ns REAL,
  area_um2 REAL, cells INTEGER, wns_ns REAL, tns_ns REAL, crit_delay_ns REAL,
  power_saif_mw REAL, power_default_mw REAL, saif_coverage REAL, power_confidence TEXT,
  hist_json TEXT, log_summary_json TEXT, resources_json TEXT, crit_path_json TEXT,
  dc_seconds REAL, tool_version TEXT,
  status TEXT NOT NULL CHECK (status IN ('ok', 'failed', 'eval_failed')),
  raw_dir TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL, git_sha TEXT NOT NULL, cfg_hash TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_evaluations_design_config ON evaluations (design_id, config);
CREATE INDEX IF NOT EXISTS ix_evaluations_cand ON evaluations (cand_id);

CREATE TABLE IF NOT EXISTS noise_floor (
  design_id TEXT NOT NULL, config TEXT NOT NULL, metric TEXT NOT NULL,
  sigma_robust REAL, sigma_std REAL, q95_abs REAL, max_abs REAL, n INTEGER, abs_unit_value REAL,
  created_at TEXT NOT NULL, git_sha TEXT NOT NULL, cfg_hash TEXT NOT NULL,
  PRIMARY KEY (design_id, config, metric, cfg_hash));

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  exp TEXT NOT NULL CHECK (exp IN ('phase3', 'phase4', 'phase5', 'ablation', 'smoke')),
  arm TEXT NOT NULL, skeleton TEXT, design_id TEXT NOT NULL, seed INTEGER, llm_model TEXT, prompt_version TEXT,
  screening_enabled INTEGER, e_s TEXT,
  budget_dc_hours REAL, spent_dc_hours REAL NOT NULL DEFAULT 0, spent_vcf_hours REAL NOT NULL DEFAULT 0,
  spent_usd REAL NOT NULL DEFAULT 0, llm_calls INTEGER NOT NULL DEFAULT 0, gens_done INTEGER NOT NULL DEFAULT 0,
  status TEXT, started_at TEXT, finished_at TEXT,
  created_at TEXT NOT NULL, git_sha TEXT NOT NULL, cfg_hash TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS candidates (
  cand_id TEXT PRIMARY KEY,
  run_id TEXT, design_id TEXT NOT NULL, gen INTEGER, parent_id TEXT, arm TEXT,
  class_rule TEXT, class_llm TEXT, class_final TEXT, subtags_json TEXT, confidence REAL,
  prompt_hash TEXT, llm_model TEXT, tokens_in INTEGER, tokens_cached INTEGER, tokens_out INTEGER, cost_usd REAL,
  rtl_path TEXT,
  v1_status TEXT, v2_status TEXT, v2_cycles INTEGER, latency_offset_json TEXT,
  v3_status TEXT, v3_seconds REAL, v4_status TEXT, counterexample_path TEXT,
  in_archive INTEGER NOT NULL DEFAULT 0, accepted INTEGER NOT NULL DEFAULT 0,
  proven_by TEXT CHECK (proven_by IN ('seq', 'dpv') OR proven_by IS NULL),
  created_at TEXT NOT NULL, git_sha TEXT NOT NULL, cfg_hash TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_candidates_run ON candidates (run_id, gen);

CREATE TABLE IF NOT EXISTS screening (
  cand_id TEXT PRIMARY KEY,
  e_s TEXT, g_es_json TEXT, fp_converged_es INTEGER, p_retained REAL, tau REAL, promoted INTEGER, audited INTEGER,
  created_at TEXT NOT NULL, git_sha TEXT NOT NULL, cfg_hash TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS diagnoses (
  cand_id TEXT PRIMARY KEY,
  label TEXT NOT NULL CHECK (label IN ('retained', 'absorbed', 'noise', 'harmful', 'tradeoff', 'nonequiv', 'screened_out')),
  rung TEXT, capability TEXT,
  attribution TEXT CHECK (attribution IN ('measured', 'prior') OR attribution IS NULL),
  fp_jaccard REAL, evidence_json TEXT, feedback_json TEXT, credit INTEGER,
  created_at TEXT NOT NULL, git_sha TEXT NOT NULL, cfg_hash TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS gen_summary (
  run_id TEXT NOT NULL, gen INTEGER NOT NULL,
  archive_json TEXT, bandit_probs_json TEXT, tau REAL, e_s TEXT,
  spent_dc_hours_cum REAL, spent_usd_cum REAL, retained_count_cum INTEGER,
  created_at TEXT NOT NULL, git_sha TEXT NOT NULL, cfg_hash TEXT NOT NULL,
  PRIMARY KEY (run_id, gen));

CREATE TABLE IF NOT EXISTS budget_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL, phase TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('dc', 'pt', 'vcf', 'llm')),
  amount REAL NOT NULL, unit TEXT NOT NULL CHECK (unit IN ('hours', 'usd')),
  run_id TEXT, note TEXT,
  created_at TEXT NOT NULL, git_sha TEXT NOT NULL, cfg_hash TEXT NOT NULL);

-- job queue (scripts/queue/); one row per submitted job, states per docs/spec/07-results-db.md
CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL, pool TEXT NOT NULL,
  design_id TEXT, cand_id TEXT, config TEXT,
  priority INTEGER NOT NULL DEFAULT 0,
  state TEXT NOT NULL CHECK (state IN ('queued', 'running', 'done', 'failed', 'backoff')),
  attempts INTEGER NOT NULL DEFAULT 0,
  host_pid INTEGER, log_path TEXT, done_path TEXT,
  payload_json TEXT NOT NULL, timeout_sec REAL,
  exit_code INTEGER, error TEXT,
  submitted_at TEXT NOT NULL, started_at TEXT, finished_at TEXT,
  created_at TEXT NOT NULL, git_sha TEXT NOT NULL, cfg_hash TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_jobs_state_pool ON jobs (state, pool, priority);

CREATE TABLE IF NOT EXISTS queue_state (
  pool TEXT PRIMARY KEY,
  backoff_until REAL NOT NULL DEFAULT 0, backoff_level INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL);

-- hidden DB only (kept here so both databases share one schema file)
CREATE TABLE IF NOT EXISTS audits (
  cand_id TEXT PRIMARY KEY,
  reason TEXT NOT NULL CHECK (reason IN ('accepted', 'rejected_sample')),
  created_at TEXT NOT NULL, git_sha TEXT NOT NULL, cfg_hash TEXT NOT NULL);
