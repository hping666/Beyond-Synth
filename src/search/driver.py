"""Residual-guided evolution, one run per design (docs/spec/05-search.md §1, §7; DECISIONS 2026-09-14): parallel-candidate
hill climbing with a small Pareto archive, a class bandit credited by the produced class, a classifier prescreen, the
conventional pipeline V1 → V2 → V3 → E4 → diagnosis through the queue, asynchronous generations and resumption from the
database plus a state file. No synthesis-rung screening. The driver only submits jobs and reads records; it never
touches the hidden database."""
import json
import random
import time
from pathlib import Path

from src import config as C
from src.classify import rules as M6
from src.db import core as db
from src.designs import catalog as K
from src.designs import jobs as J
from src.diagnose import m3
from src.noise import stats as S
from src.search import candidates as CA
from src.search import llm as L
from src.search import prompts as PR
from src.search.archive import Archive
from src.search.bandit import ClassBandit
from src.eval import retention as RET
from src.search import scope as SC
from src.search.prescreen import decide as prescreen_decide

EQ_KEEP = ("v1_status", "v2_status", "v2_cycles", "latency_offset_json", "v3_status", "v3_seconds", "v4_status", "counterexample_path", "verdict", "seconds")
BUDGET_PHASE = {"phase3": "phase3_calibration", "smoke": "phase3_calibration", "phase4": "phase4_generation", "phase5": "phase5_main", "phase5_probe": "phase5_probe", "ablation": "phase6_ablation"}
FINAL_LABELS = {"retained", "absorbed", "absorbed_identical", "duplicate", "noise", "harmful", "tradeoff", "fragile", "nonequiv", "prescreened", "improved", "no_gain", "scope_violation"}
ARM_M = {"fitness": "E4", "feedback": "verdict", "floor": "rule_a", "credit": "retained_tradeoff", "prescreen": True, "envelope": True}


def record_from_row(row):
    """An evaluations row -> the record dict the diagnoser reads (metrics, hist, resources, path_endpoints, log_summary)."""
    r = dict(row)
    def js(k):
        try:
            return json.loads(r.get(k) or "{}")
        except (ValueError, TypeError):
            return {}
    ls = js("log_summary_json")
    counts = ls.get("counts") if isinstance(ls.get("counts"), dict) else ls
    metrics = {"area": r.get("area_um2"), "area_um2": r.get("area_um2"), "cells": r.get("cells"), "wns_ns": r.get("wns_ns"), "tns_ns": r.get("tns_ns"),
               "power_saif_mw": r.get("power_saif_mw"), "power_default_mw": r.get("power_default_mw"),
               "registers": (counts or {}).get("registers") or ls.get("registers"), "icg_count": (counts or {}).get("icg_count") or ls.get("icg_count")}
    cp = js("crit_path_json")
    return {"metrics": metrics, "hist": js("hist_json"), "resources": js("resources_json"), "log_summary": ls,
            "path_endpoints": cp.get("endpoints") or cp.get("path_endpoints") or [], "raw_dir": r.get("raw_dir"), "dc_seconds": r.get("dc_seconds")}


class SearchRun:
    def __init__(self, cfg, conn, run_id, queue=None, transport=None, clock=time.time):
        self.cfg, self.conn, self.run_id = cfg, conn, run_id
        self.clock = clock
        self.row = dict(conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone())
        if self.row["arm"] not in (cfg["search"].get("arms") or {}) and self.row["arm"] != "M":
            raise ValueError(f"arm {self.row['arm']!r} has no definition in config search.arms (2026-09-15: an undefined arm must not run as M by default)")
        self.design = next(d for d in K.load_all() if d["design_id"] == self.row["design_id"])
        drow = conn.execute("SELECT * FROM designs WHERE design_id=?", (self.row["design_id"],)).fetchone()
        self.phi = float(drow["phi_main_ns_nangate45"])
        self.dir = Path(C.results_dir(cfg)) / "candidates" / run_id   # follows project.results_dir (tests run isolated; 2026-09-15)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / "state.json"
        self.queue = queue
        self.client = L.LLMClient(cfg, conn, BUDGET_PHASE.get(self.row["exp"], self.row["exp"]), run_id, transport=transport)
        # arm semantics (spec 05 §5; config search.arms): fitness source (E4 or Y), feedback (verdict | scalar | scalar_static), floor, credit rule
        self.armdef = dict((cfg["search"].get("arms") or {}).get(self.row["arm"]) or ARM_M)
        self.fit_cfg = str(self.armdef.get("fitness") or "E4")
        self.scalar = self.armdef.get("feedback", "verdict") != "verdict"
        self.drrtl = self.armdef.get("feedback") == "drrtl"   # PLAN 5.2: the Dr. RTL re-implementation arm (2026-09-15)
        self.system, self.classes, self.prompt_version = PR.load_templates(caliber=self.fit_cfg, system="drrtl" if self.drrtl else "default")
        self.floor_version = cfg["noise"].get("floor_version")
        if self.armdef.get("floor", "rule_a") == "none":
            self.floor = {}
        else:
            self.floor = S.latest_floor(conn, self.row["design_id"], "E4", self.floor_version) or S.latest_floor(conn, self.row["design_id"], "E4")
        self.floor_class = next((r.get("floor_class") for r in self.floor.values() if r.get("floor_class")), None)
        # G5 item 1 correctness aids (config exp5.correctness_aids): scope-limited rewriting and one counterexample-guided repair per candidate
        aids = (cfg.get("exp5") or {}).get("correctness_aids") or {}
        self.scope_on = bool(aids.get("scope_limited_rewriting", False))
        self.scope_cfg = dict(aids.get("scope") or {})
        self.repair_max = int(aids.get("repair_attempts") or 0)
        self.repair_types = set(aids.get("repair_failure_types") or ["rejected", "sim_fail", "falsified"])
        self.thresholds = {"area": (self.floor.get("area") or {}).get("t_d"), "wns": (self.floor.get("wns") or {}).get("t_d"), "power": (self.floor.get("power_saif") or {}).get("t_d")}
        self.sigma = {"area": (self.floor.get("area") or {}).get("sigma_robust") or 0.0, "wns": (self.floor.get("wns") or {}).get("sigma_robust") or 0.0,
                      "power": (self.floor.get("power_saif") or {}).get("sigma_robust") or 0.0}
        base = conn.execute("SELECT * FROM evaluations WHERE design_id=? AND config=? AND is_baseline=1 AND pert_id IS NULL AND cand_id IS NULL AND status='ok' "
                            "AND abs(clock_ns-?)<1e-6 ORDER BY (power_saif_mw IS NOT NULL) DESC, eval_id DESC LIMIT 1", (self.row["design_id"], self.fit_cfg, self.phi)).fetchone()
        if base is None:
            raise RuntimeError(f"{self.row['design_id']}: no {self.fit_cfg} baseline at Phi_main {self.phi}; run scripts/phase2_noise.py (E4) or scripts/phase4_exp1.py baselines (Y) first")
        self.base_row, self.base = base, record_from_row(base)
        self.prior, self.prior_retained = self.load_map_prior()   # Phase 4 output (search.map_prior_file); arm M only
        # arm B1@E4 (feedback scalar_static): the literature's static complement text replaces the map-prior table (spec 05 §2)
        self.static_text, self.static_version = PR.load_static_complement() if self.armdef.get("feedback") == "scalar_static" else (None, None)
        if self.drrtl:
            self.static_text, self.static_version = PR.load_skill_library(cfg), "drrtl-skills"   # Dr. RTL's released skill library takes the prior table's slot
        self.prefix = PR.prefix(self.design, self.system, base, self.floor, self.phi, self.prior, caliber=self.fit_cfg, static_text=self.static_text,
                                prior_block=(self.armdef.get("feedback", "verdict") == "verdict"))   # B0 / B2: neither the prior table nor the static block
        self.d_text = "\n\n".join(Path(self.design["_dir"], f).read_text(errors="replace") for f in self.design["files"])
        self.d_design = SC.parse_design(self.d_text) if self.scope_on else None
        self._d_stats = None
        self.priority = int(cfg["search"].get("job_priority", 4))
        pats = (cfg["search"].get("long_proof_first") or {}).get("design_patterns") or []
        self.arith_design = any(pat in self.row["design_id"] for pat in pats)   # arithmetic pipelines by name (as the Phase 5 projection)
        self.load_state()
        self.mark_orphans()

    # ------------------------------------------------------------------ creation / resumption
    @classmethod
    def create(cls, cfg, conn, *, exp, arm, design_id, seed, model, K, N, queue=None, transport=None, note=""):
        base_id = f"r{db.now().replace('-', '').replace(':', '').replace('T', '_')}_{design_id[-12:]}_{str(arm)[:6]}_{model[-6:]}_s{seed}".replace(".", "")
        run_id, n = base_id, 1
        while conn.execute("SELECT 1 FROM runs WHERE run_id=?", (run_id,)).fetchone():   # the launch creates hundreds of runs within a second (2026-09-15): the arm is part of the id and a suffix settles the rest
            n += 1
            run_id = f"{base_id}-{n}"
        sc = cfg["search"]
        budget_calls = min(int(K) * int(N), int(cfg["scale"]["budget"]["llm_calls_per_run"]))
        armdef = (cfg["search"].get("arms") or {}).get(arm) or {}
        prompt_version = str(PR.load_templates()[2]) + (f"+sc{PR.load_static_complement()[1]}" if armdef.get("feedback") == "scalar_static" else "")
        db.insert(conn, "runs", {"run_id": run_id, "exp": exp, "arm": arm, "skeleton": "hillclimb", "design_id": design_id, "seed": int(seed), "llm_model": model,
                                 "prompt_version": prompt_version, "screening_enabled": 0, "e_s": None, "budget_dc_hours": None,
                                 "budget_llm_calls": budget_calls, "status": "created", "started_at": db.now(), "floor_version": cfg["noise"].get("floor_version")})
        run = cls(cfg, conn, run_id, queue=queue, transport=transport)
        run.state.update(K=int(K), N=int(N), budget_calls=budget_calls, note=note)
        run.bandit = ClassBandit(sc["bandit"]["arms"], sc["bandit"]["c_ucb"], sc["bandit"]["softmax_temp"], prior=run.prior_retained if sc["bandit"].get("init_from_map_prior") else None)
        run.archive = Archive(sc["archive_size"])
        run.save_state()
        return run

    @classmethod
    def resume(cls, cfg, conn, run_id, queue=None, transport=None):
        return cls(cfg, conn, run_id, queue=queue, transport=transport)

    def mark_orphans(self):
        """Candidate rows of this run that the state file does not know belong to a generation whose issue died before
        the state was saved (crash / kill): labelled `aborted`, never evaluated further, excluded from the tables."""
        known = set(self.state["cands"]) | {k for k in self.state["cands"]} | set(self.state["feedback"])
        rows = [r[0] for r in self.conn.execute("SELECT cand_id FROM candidates WHERE run_id=? AND label IS NULL", (self.run_id,))]
        orphans = [cid for cid in rows if cid not in known and not any(cid.startswith(k + "_dup") for k in known)]
        for cid in orphans:
            self.conn.execute("UPDATE candidates SET label='aborted', note=COALESCE(note,'') || ' [aborted: issued by an attempt that died before persisting its state]' WHERE cand_id=?", (cid,))
        return orphans

    def load_state(self):
        if self.state_path.exists():
            st = json.loads(self.state_path.read_text())
        else:
            st = {"gen": 0, "issued_at": None, "pending": {}, "cands": {}, "feedback": {}, "fingerprints": {}, "retained": 0, "calls": 0, "K": None, "N": None, "budget_calls": None, "done": False, "stall": 0, "last_retained_gen": 0}
        self.state = st
        sc = self.cfg["search"]
        self.bandit = ClassBandit.from_json(st["bandit"]) if st.get("bandit") else ClassBandit(sc["bandit"]["arms"], sc["bandit"]["c_ucb"], sc["bandit"]["softmax_temp"])
        self.archive = Archive.from_json(st["archive"]) if st.get("archive") else Archive(sc["archive_size"])

    def save_state(self):
        self.state["bandit"], self.state["archive"] = self.bandit.to_json(), self.archive.to_json()
        self.state_path.write_text(json.dumps(self.state, indent=1, sort_keys=True, default=str))

    # ------------------------------------------------------------------ helpers
    def _q(self):
        if self.queue is None:
            from src.jobqueue.core import Queue
            self.queue = Queue(self.cfg, self.conn, str(Path(C.results_dir(self.cfg)) / "queue" / "logs"), env={})
        return self.queue

    def job_state(self, job_id):
        r = self.conn.execute("SELECT state FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return r["state"] if r else "missing"

    def eq_record(self, cand_id):
        """The equivalence record of a candidate: by the content-addressed directory of its job payload (the runner reuses
        an earlier record when another run produced the same RTL, so the record may carry that run's cand_id), else by
        cand_id."""
        c = self.state["cands"].get(cand_id) or {}
        root = Path(C.results_dir(self.cfg)) / "raw" / self.row["design_id"] / "EQ"
        best = None
        payload = c.get("eq_payload")
        if payload:
            from src.equiv.run_equiv import equiv_extra, equiv_hash
            try:
                h = equiv_hash(payload["d_rtl"], payload["c_rtl"], payload["top"], self.cfg, equiv_extra(self.cfg, payload, True))
            except OSError:
                h = None
            if h:
                for eq in sorted(root.glob(f"{h}*/equiv.json"), key=lambda p: p.stat().st_mtime):
                    try:
                        best = (eq.stat().st_mtime, json.loads(eq.read_text()), str(eq.parent))
                    except json.JSONDecodeError:
                        continue
        if best is None:
            for eq in root.glob("*/equiv.json"):
                try:
                    rec = json.loads(eq.read_text())
                except json.JSONDecodeError:
                    continue
                if rec.get("cand_id") == cand_id and (best is None or eq.stat().st_mtime > best[0]):
                    best = (eq.stat().st_mtime, rec, str(eq.parent))
        return (best[1], best[2]) if best else (None, None)

    def e4_row(self, cand_id):
        return self.conn.execute("SELECT * FROM evaluations WHERE design_id=? AND cand_id=? AND config='E4' AND status='ok' AND abs(clock_ns-?)<1e-6 ORDER BY eval_id DESC LIMIT 1",
                                 (self.row["design_id"], cand_id, self.phi)).fetchone()

    def load_map_prior(self):
        """(absorbed, retained) per class from `search.map_prior_file` for arms with verdict feedback (M); (None, None) for
        the baselines and when the file is unset or missing. The absorbed table feeds the prescreen and the prompt's prior
        block, the retained table the bandit's pseudo-counts (spec 05 §1, §3)."""
        sc = self.cfg["search"]
        path = sc.get("map_prior_file")
        if not path or self.armdef.get("feedback", "verdict") != "verdict" or not sc["bandit"].get("init_from_map_prior", False):
            return None, None
        p = Path(path) if Path(path).is_absolute() else Path(C.ROOT) / path
        if not p.exists():
            return None, None
        data = json.loads(p.read_text())
        self.map_prior_meta = {k: data.get(k) for k in ("basis", "generated_at", "git_sha", "floor_version")}
        return {k: float(v) for k, v in (data.get("absorbed") or {}).items()}, {k: float(v) for k, v in (data.get("retained") or {}).items()}

    # ------------------------------------------------------------------ correctness aids (G5 item 1; config exp5.correctness_aids)
    def region_for(self, parent_id):
        """(region, prompt text) for the next rewrite: the critical endpoints of the parent's fitness evaluation (or D's
        baseline) mapped to the module / always blocks of the design text (src/search/scope.py); (None, None) when off."""
        if not self.scope_on:
            return None, None
        crit = None
        if parent_id:
            row = self.fit_row(parent_id)
            crit = row["crit_path_json"] if row is not None else None
        if not crit:
            crit = self.base_row["crit_path_json"] if self.base_row is not None else None
        region = SC.select_region(self.d_design, self.design["top"], crit, endpoints=int(self.scope_cfg.get("endpoints", 3)),
                                  single_module=str(self.scope_cfg.get("single_module", "block")), multi_module=str(self.scope_cfg.get("multi_module", "module")))
        region["from_parent"] = parent_id if (parent_id and crit) else None
        return region, SC.region_text(self.d_design, region, self.design["top"])

    def scope_flag(self, cid, violations):
        """Decision 2026-09-15 evening (item 2): an out-of-scope edit is no longer a discard — the text outside the region was
        restored from D by `scope.splice` and the candidate runs the pipeline; the violations stay on the row as a warning
        flag (`scope_json.violations`) and are counted per run (`state.scope_violations`, reported per arm). True when flagged."""
        if not violations:
            return False
        self.state.setdefault("scope_violations", 0)
        self.state["scope_violations"] += 1
        return True

    def maybe_repair(self, cid, c, rec):
        """G5 item 1 (ii): after a V1 rejection, a lock-step mismatch or a SEQ counterexample, one repair call with the
        verifier's evidence; the answer is a new candidate (`repair_of` = the failed one, same parent, same requested class)
        that goes through the whole pipeline; a repair's own failure is never repaired again; the call comes out of the
        run's equal-call budget."""
        if self.repair_max <= 0 or c.get("repair_of") or c.get("repaired_by"):
            return None
        failure, text = SC.failure_evidence(rec)
        if failure is None or failure not in self.repair_types:
            return None
        st = self.state
        if int(st["calls"]) >= int(st["budget_calls"]):
            st.setdefault("repairs_skipped_budget", 0)
            st["repairs_skipped_budget"] += 1
            return None
        gen = int(st["gen"])
        cls = c.get("class_requested") or "free"
        instr = self.classes.get(cls, self.classes.get("free"))
        region, scope_text = self.region_for(c.get("parent_id"))
        failed_rtl = Path(c["path"]).read_text(errors="replace")
        sfx = PR.repair_suffix(instr, cls, failed_rtl, text, scope_text=scope_text)
        r = self.client.call(self.row["llm_model"], self.prefix, sfx, tag=f"{self.run_id}:repair:{cid}:{failure}")
        st["calls"] += 1
        rep = {"of": cid, "failure": failure, "call_id": r["call_id"], "gen": gen, "cand_id": None, "unusable": None}
        st.setdefault("repairs", []).append(rep)
        c["repaired_by"] = "pending"
        meta = {"run_id": self.run_id, "gen": gen, "parent_id": c.get("parent_id"), "class_requested": cls, "call_id": r["call_id"], "cost_usd": r["cost_usd"], "usage": r["usage"], "repair_of": cid, "repair_failure": failure}
        try:
            if r.get("status") == "incomplete":
                raise CA.BadAnswer("truncated at max_output_tokens (status incomplete)")
            rtl, note = CA.parse_answer(r["text"])
            rtl, spliced = SC.splice(self.d_text, rtl, region)   # out-of-scope edits restored from D; the violations become the warning flag
            if spliced.get("region_missing"):
                raise CA.BadAnswer(f"the answer does not contain the region module {spliced['region_missing']}: not a rewrite of the region")
            CA.check_top(rtl, self.design["top"])
            if spliced:
                meta["scope_splice"] = spliced
        except CA.BadAnswer as e:
            rep["unusable"] = str(e)
            (self.dir / f"unusable_repair_{cid}.json").write_text(json.dumps({**meta, "unusable": str(e)}, indent=1, default=str))
            self.bandit.credit(cls, 0)
            c["repaired_by"] = None
            self.conn.execute("UPDATE runs SET llm_calls=? WHERE run_id=?", (st["calls"], self.run_id))
            return None
        new_cid = CA.cand_id_of(rtl, self.run_id)
        _cid, path = CA.store(self.run_id, self.design, rtl, {**meta, "note": note, "content_hash": CA.cand_id_of(rtl)}, root=self.dir.parent, cand_id=new_cid)
        rng = random.Random(f"{self.run_id}|repair|{cid}")
        if region is not None:
            self.scope_flag(new_cid, (meta.get("scope_splice") or {}).get("violations"))
        issued = self.issue_candidate(new_cid, path, rtl, note, cls, gen, c.get("parent_id"), r, rng, index=99, region=region, repair_of=cid, spliced=meta.get("scope_splice"))
        rep["cand_id"], c["repaired_by"] = issued, issued
        self.conn.execute("UPDATE runs SET llm_calls=? WHERE run_id=?", (st["calls"], self.run_id))
        return rep["cand_id"]

    def c2_allowed(self, c):
        """spec 03 §2 / config `equiv.c2_population`: a candidate proven only through the SEQ latency mapping (class c2, constant
        output offsets) may enter the population only when the protocol-recognition rules allow it; until then never."""
        if not c.get("latency_mapped"):
            return True
        return bool((self.cfg.get("equiv") or {}).get("c2_population", False))

    def seq_cap_min(self, cls):
        caps = self.cfg.get("equiv", {}).get("seq_cap_min_by_class") or {}
        return int(caps.get(cls, self.cfg["timeouts"]["seq_min"]))

    def lineage_feedback(self, parent_id):
        depth = int(self.cfg["search"]["feedback_depth"])
        blocks, cid = [], parent_id
        while cid and len(blocks) < depth:
            fb = self.state["feedback"].get(cid)
            if fb:
                blocks.append(fb)
            cid = (self.state["cands"].get(cid) or {}).get("parent_id")
        if not blocks:  # a fresh start from D: the most recent verdicts of this run still inform the model
            recent = sorted((c for c in self.state["cands"].values() if c["cand_id"] in self.state["feedback"]), key=lambda c: -c.get("gen", 0))
            blocks = [self.state["feedback"][c["cand_id"]] for c in recent[:depth]]
        return blocks

    # ------------------------------------------------------------------ generation
    def build_generation(self):
        st = self.state
        gen = st["gen"] + 1
        rng = random.Random(f"{self.run_id}|gen{gen}|seed{self.row['seed']}")
        parent = self.archive.select_parent(rng)
        if st["stall"] >= int(self.cfg["search"]["stall_gens"]) and self.archive.members:
            others = [m for m in self.archive.members if not parent or m["cand_id"] != parent["cand_id"]]
            parent = rng.choice(others) if others else None   # restart from another member (or D)
            st["stall"] = 0
        parent_id = parent["cand_id"] if parent else None
        parent_rtl = Path(st["cands"][parent_id]["path"]).read_text() if parent_id else None
        if self.drrtl and st.get("skill_learning_due") and int(st["calls"]) < int(st["budget_calls"]):
            self.drrtl_learn_skills(gen)   # in-run skill learning: one call on the previous round, charged before this round's calls are counted
        n = min(int(st["N"]), int(st["budget_calls"]) - int(st["calls"]))
        classes = self.bandit.draw(rng, n)
        blocks = self.lineage_feedback(parent_id)
        region, scope_text = self.region_for(parent_id)
        issued = []
        answers = []
        for i, cls in enumerate(classes):
            if self.drrtl:
                strat = self.drrtl_strategy(gen, i)
                paths = PR.drrtl_paths_block(self.drrtl_crit_path(parent_id), strat, int((self.cfg["search"].get("drrtl") or {}).get("k_paths", 10)), rng=rng)
                sfx = PR.drrtl_suffix(paths, st.get("drrtl_skills"), parent_rtl, blocks, scope_text=scope_text)
                cls = "free"   # no class instruction: the produced class (M6) is credited as for every arm
            else:
                instr = self.classes.get(cls, self.classes.get("free"))
                sfx = PR.suffix(instr, cls, parent_rtl, blocks, self.design["top"], scope_text=scope_text)
            r = self.client.call(self.row["llm_model"], self.prefix, sfx, tag=f"{self.run_id}:g{gen}:{cls}:{i}")
            st["calls"] += 1
            meta = {"run_id": self.run_id, "gen": gen, "parent_id": parent_id, "class_requested": cls, "call_id": r["call_id"], "cost_usd": r["cost_usd"], "usage": r["usage"]}
            if self.drrtl:
                meta["drrtl_strategy"] = self.drrtl_strategy(gen, i)
            try:
                if r.get("status") == "incomplete":
                    raise CA.BadAnswer(f"truncated at max_output_tokens (status incomplete, {(r.get('usage') or {}).get('output_tokens')} output tokens)")
                rtl, note = CA.parse_answer(r["text"])
                rtl, spliced = SC.splice(self.d_text, rtl, region)   # the text outside the region comes from D (omitted modules, changed modules or blocks); the violations become the warning flag (decision 2026-09-15 evening, item 2)
                if spliced.get("region_missing"):
                    raise CA.BadAnswer(f"the answer does not contain the region module {spliced['region_missing']}: not a rewrite of the region")
                CA.check_top(rtl, self.design["top"])
            except CA.BadAnswer as e:
                meta.update(unusable=str(e))
                (self.dir / f"unusable_g{gen}_{i}.json").write_text(json.dumps(meta, indent=1, default=str))
                self.bandit.credit(cls, 0)   # an unusable answer is the requested class's failure
                continue
            if region is not None:
                meta["scope"] = region
                if spliced:
                    meta["scope_splice"] = spliced
            answers.append((i, cls, rtl, note, r, meta))
        # DECISIONS 2026-09-14 item 2: on arithmetic designs the (c1) / (d) proofs (hours-long tails) are submitted before the
        # rest of the generation, so that their tails overlap with the other proofs; the produced class is known only after
        # M6 inside issue_candidate, which also raises the queue priority of such proofs (config search.long_proof_first)
        lp = self.cfg["search"].get("long_proof_first") or {}
        first = set(lp.get("classes") or [])
        if self.arith_design and first:
            answers.sort(key=lambda a: 0 if a[1] in first else 1)
        for i, cls, rtl, note, r, meta in answers:
            cid = CA.cand_id_of(rtl, self.run_id)   # per-run id; the unsalted content hash is stored alongside (DECISIONS 2026-09-14)
            _cid, path = CA.store(self.run_id, self.design, rtl, {**meta, "note": note, "content_hash": CA.cand_id_of(rtl)}, root=self.dir.parent, cand_id=cid)
            if region is not None:
                self.scope_flag(cid, (meta.get("scope_splice") or {}).get("violations"))
            issued.append(self.issue_candidate(cid, path, rtl, note, cls, gen, parent_id, r, rng, index=i, region=region, spliced=meta.get("scope_splice"), strategy=meta.get("drrtl_strategy")))
        st["gen"] = gen
        st["issued_at"] = self.clock()
        if self.drrtl and (self.cfg["search"].get("drrtl") or {}).get("skill_learning", False):
            st["skill_learning_due"] = gen   # the next build distils this round first
        self.conn.execute("UPDATE runs SET llm_calls=?, gens_done=?, status='running' WHERE run_id=?", (st["calls"], gen, self.run_id))
        self.write_gen_summary(gen)
        return issued

    # ------------------------------------------------------------------ Dr. RTL re-implementation arm (PLAN 5.2; config search.drrtl)
    def drrtl_strategy(self, gen, index):
        strategies = (self.cfg["search"].get("drrtl") or {}).get("strategies") or [{"paths": "top_slack", "focus": "mixed"}]
        return dict(strategies[((int(gen) - 1) * 2 + int(index)) % len(strategies)])   # a deterministic rotation: the first round starts at the first strategy

    def drrtl_crit_path(self, parent_id):
        """The parent's E4 timing paths when it has an E4 record, else D's baseline paths."""
        if parent_id:
            row = self.fit_row(parent_id)
            if row is not None and row["crit_path_json"]:
                return row["crit_path_json"]
        return self.base_row["crit_path_json"] if self.base_row is not None else None

    def drrtl_learn_skills(self, gen):
        """Dr. RTL's group-relative skill learning, one LLM call per built generation: the previous round's attempts (strategy,
        note, verdict, PPA deltas) -> pattern-strategy entries appended to the run's learned skills (kept in the state and
        given to every later call); the call is charged to the run's equal-call budget."""
        st = self.state
        prev = int(st.get("skill_learning_due") or 0)
        st["skill_learning_due"] = None
        attempts = []
        for c in st["cands"].values():
            if int(c.get("gen") or 0) != prev or c.get("repair_of"):
                continue
            fb = st["feedback"].get(c["cand_id"]) or {}
            attempts.append({"strategy": (c.get("drrtl_strategy") or {}), "note": c.get("note"), "verdict": c.get("label") or c.get("state"),
                             "ppa_delta": (fb.get("evidence") or {}) if isinstance(fb.get("evidence"), dict) else {}, "class": c.get("class_final")})
        if not attempts:
            return None
        gains = [a["ppa_delta"].get("dA_pct") for a in attempts if isinstance(a["ppa_delta"].get("dA_pct"), (int, float))]
        summary = {"round": prev, "attempts": attempts, "round_mean_dA_pct": (sum(gains) / len(gains)) if gains else None}
        r = self.client.call(self.row["llm_model"], self.prefix, PR.drrtl_skill_prompt(summary), tag=f"{self.run_id}:skills:g{prev}")
        st["calls"] += 1
        text = None
        try:
            raw = (r.get("text") or "").strip()
            raw = raw[raw.find("{"):raw.rfind("}") + 1]
            obj = json.loads(raw) if raw else {}
            entries = obj.get("skills") or []
            lines = [f"- [{e.get('confidence', 'medium')}] pattern: {e.get('pattern')}; strategy: {e.get('strategy')}" + (f" ({e.get('basis')})" if e.get("basis") else "") for e in entries[:3] if isinstance(e, dict)]
            text = "\n".join(lines) if lines else None
        except (ValueError, AttributeError, TypeError):
            text = None
        st.setdefault("drrtl_skill_calls", []).append({"gen": prev, "call_id": r["call_id"], "entries": text})
        if text:
            st["drrtl_skills"] = ((st.get("drrtl_skills") or "") + "\n" + text).strip()[-4000:]
        self.conn.execute("UPDATE runs SET llm_calls=? WHERE run_id=?", (st["calls"], self.run_id))
        return text

    def issue_candidate(self, cid, path, rtl, note, cls_requested, gen, parent_id, call, rng, index=0, region=None, repair_of=None, spliced=None, strategy=None):
        st = self.state
        scope_json = json.dumps({"region": region, "violations": list((spliced or {}).get("violations") or [])[:8], "spliced": {k: v for k, v in (spliced or {}).items() if k != "violations"}}, default=str) if region is not None else None
        if cid in st["cands"]:   # the same RTL came out twice: a duplicate of the earlier candidate, no evaluation
            dup = f"{cid}_dup{gen}_{index}"
            self.record_label(dup, None, "duplicate", {"duplicate_of": cid}, gen=gen, cls_requested=cls_requested, parent_id=parent_id, path=str(path), note=note, call=call)
            if scope_json:
                self.conn.execute("UPDATE candidates SET scope_json=? WHERE cand_id=?", (scope_json, dup))
            return cid
        if rtl.strip() == self.d_text.strip():   # (after the scope restoration an answer whose only edits were out of scope is D again: it keeps its flag)
            st["cands"][cid] = {"cand_id": cid, "gen": gen, "parent_id": parent_id, "path": str(path), "class_requested": cls_requested, "class_final": "a", "state": "final", "issued_at": self.clock(), "scope_flag": bool((spliced or {}).get("violations"))}
            self.record_label(cid, None, "absorbed_identical", {"identical_text": True}, gen=gen, cls_requested=cls_requested, parent_id=parent_id, path=str(path), note=note, call=call, cls_final="a")
            if scope_json:
                self.conn.execute("UPDATE candidates SET scope_json=? WHERE cand_id=?", (scope_json, cid))
            return cid
        d_files = [str(p) for p in K.abs_paths(self.design, self.design["files"])]
        incdirs = [str(p) for p in K.abs_paths(self.design, self.design["incdirs"])]
        feat = None
        try:
            if self._d_stats is None:   # D's statistics once per run (2026-09-15), reused for every candidate
                self._d_stats = M6.d_statistics(d_files, self.design["top"], self.cfg, sverilog=self.design.get("sverilog", False), incdirs=incdirs, workdir=self.dir / "m6_D")
            feat = M6.features(d_files, [str(path)], self.design["top"], self.cfg, sverilog=self.design.get("sverilog", False),
                               incdirs=incdirs, workdir=self.dir / f"m6_{cid}", d_stats=self._d_stats)
            cls_rule = M6.classify(feat, cfg=self.cfg)
            cls_final = cls_rule["class_rule"]
        except Exception as e:  # the classifier could not read the candidate: the requested class stands, flagged
            cls_rule, cls_final = {"class_rule": None, "error": f"{type(e).__name__}: {e}"[:200]}, cls_requested
        RET.slim_m6_workdir(self.dir / f"m6_{cid}", self.cfg)   # tiered retention: the features are archived in the row below
        pre = prescreen_decide(self.prior, cls_final, self.cfg["prescreen"]["p_min"], self.cfg["prescreen"]["audit_frac"], rng) if self.armdef.get("prescreen", True) else "evaluate"
        cap = self.seq_cap_min(cls_final if cls_final in ("a", "b", "c1", "c2", "d") else "d")
        entry = {"cand_id": cid, "gen": gen, "parent_id": parent_id, "path": str(path), "class_requested": cls_requested, "class_rule": cls_final,
                 "class_final": cls_final, "prescreen": pre, "seq_cap_min": cap, "issued_at": self.clock(), "state": "eq_pending", "note": note,
                 "repair_of": repair_of, "scope": region, "drrtl_strategy": strategy, "scope_flag": bool((spliced or {}).get("violations"))}
        row = {"cand_id": cid, "run_id": self.run_id, "design_id": self.row["design_id"], "gen": gen, "parent_id": parent_id, "arm": self.row["arm"],
               "content_hash": CA.cand_id_of(rtl),
               "class_requested": cls_requested, "class_rule": cls_final, "class_final": cls_final, "confidence": cls_rule.get("confidence"),
               "subtags_json": json.dumps(cls_rule.get("rules") or cls_rule), "prompt_hash": None, "llm_model": self.row["llm_model"],
               "tokens_in": (call["usage"] or {}).get("input_tokens"), "tokens_cached": (call["usage"] or {}).get("cached_tokens"),
               "tokens_out": (call["usage"] or {}).get("output_tokens"), "cost_usd": call["cost_usd"], "rtl_path": str(path), "prescreened": int(pre == "prescreened"),
               "seq_cap_min": cap, "note": note, "call_id": call["call_id"], "repair_of": repair_of,
               "scope_json": scope_json,
               "features_json": json.dumps(feat, default=list, sort_keys=True) if feat else None, "rules_version": (feat or {}).get("rules_version")}
        db.insert(self.conn, "candidates", row)
        if pre == "prescreened":
            entry["state"] = "final"
            st["cands"][cid] = entry
            self.record_label(cid, None, "prescreened", {"prior": (self.prior or {}).get(cls_final)}, gen=gen, cls_requested=cls_requested, parent_id=parent_id, path=str(path), note=note, call=call, cls_final=cls_final, insert_row=False)
            return cid
        payload = {"design_id": self.row["design_id"], "cand_id": cid, "d_rtl": d_files, "c_rtl": [str(path)], "top": self.design["top"],
                   "clk": (self.design.get("clk_ports") or [None])[0], "rst": self.design.get("rst_port"), "rst_sense": self.design.get("rst_sense"),
                   "sverilog": self.design.get("sverilog", False), "incdirs": [str(p) for p in K.abs_paths(self.design, self.design["incdirs"])],
                   "note": f"search {self.run_id} g{gen} {cls_final}"}
        lp = self.cfg["search"].get("long_proof_first") or {}
        boost = int(lp.get("priority_boost") or 0) if (self.arith_design and cls_final in set(lp.get("classes") or [])) else 0
        jid = self._q().submit("vcf", payload, design_id=self.row["design_id"], cand_id=cid, config="EQ", priority=self.priority + boost, timeout_sec=cap * 60 + 900)
        entry["eq_job_id"], entry["eq_payload"] = jid, payload
        self.conn.execute("UPDATE candidates SET eq_job_id=? WHERE cand_id=?", (jid, cid))
        st["cands"][cid] = entry
        st["pending"][cid] = "eq"
        return cid

    # ------------------------------------------------------------------ verdict processing
    def process_verdicts(self):
        """Apply every verdict that has arrived (any generation): equivalence -> E4 job; E4 -> diagnosis; envelope -> final label."""
        changed = False
        for cid, stage in list(self.state["pending"].items()):
            c = self.state["cands"][cid]
            if stage == "eq":
                js = self.job_state(c["eq_job_id"])
                if js not in ("done", "failed"):
                    continue
                rec, rec_dir = self.eq_record(cid)
                changed = True
                if rec is None:
                    self.finish_nonequiv(cid, {"verdict": "error", "v1_status": "error"}, "no equivalence record (job failed)")
                    continue
                c["eq_record"] = rec_dir
                c["v3_seconds"], c["eq_seconds"] = rec.get("v3_seconds"), rec.get("seconds")
                c["time_to_verdict_s"] = round(self.clock() - float(c["issued_at"]), 1)
                self.conn.execute("UPDATE candidates SET v1_status=?, v2_status=?, v2_cycles=?, latency_offset_json=?, v3_status=?, v3_seconds=?, v4_status=?, "
                                  "counterexample_path=?, verdict=?, time_to_verdict_s=?, proven_by=?, equiv_version=? WHERE cand_id=?",
                                  tuple(rec.get(k) for k in EQ_KEEP[:8]) + (rec.get("verdict"), c["time_to_verdict_s"], rec.get("proven_by"),
                                                                             rec.get("equiv_version") or (self.cfg.get("equiv") or {}).get("version"), cid))   # decision 2026-09-15 evening item 5: the stack version stamped on every verdict
                offsets = json.loads(rec.get("latency_offset_json") or "{}")
                if rec.get("verdict") in ("proven", "proven_sim_only") and any(int(v) > 0 for v in offsets.values()):
                    c["class_final"] = "c2"
                    c["latency_mapped"] = bool(rec.get("latency_mapped"))   # G2.1 (b): SEQ-proven at the V2 offsets; population rule in c2_allowed()
                    self.conn.execute("UPDATE candidates SET class_final='c2' WHERE cand_id=?", (cid,))
                if rec.get("verdict") in ("proven", "proven_sim_only"):
                    self.submit_fitness(cid, c, rec)
                else:
                    self.finish_nonequiv(cid, rec, None)
                    self.maybe_repair(cid, c, rec)   # G5 item 1 (ii): one counterexample-guided repair call
            elif stage == "e4":
                js = self.job_state(c["e4_job_id"])
                if js not in ("done", "failed"):
                    continue
                changed = True
                row = self.fit_row(cid)
                if row is None:
                    c["state"], c["e4_failed"] = "final", True
                    self.state["pending"].pop(cid, None)
                    self.conn.execute("UPDATE candidates SET note=COALESCE(note,'') || ? WHERE cand_id=?", (f" [{self.fit_cfg} evaluation failed]", cid))
                    continue
                if self.scalar:
                    self.scalar_verdict(cid, c, row)
                else:
                    self.diagnose_candidate(cid, c, row)
            elif stage == "envelope":
                jobs = c.get("envelope_jobs") or []
                if any(self.job_state(j) not in ("done", "failed") for j in jobs):
                    continue
                changed = True
                self.finish_envelope(cid, c)
        if changed:
            self.slim_finished()
        return changed

    def slim_finished(self):
        """Tiered retention (G5 item 5 (ii)): once a candidate has its final label and is neither accepted (ever archived) nor in
        the audit sample, its regenerable artifacts are removed (equivalence record, fitness and envelope records, classifier
        workdir); the records themselves stay. Runs once per candidate (`slimmed` in the state)."""
        if not RET.enabled(self.cfg):
            return
        for cid, c in self.state["cands"].items():
            if c.get("state") != "final" or c.get("slimmed") is not None or c.get("repaired_by") == "pending":
                continue
            row = self.conn.execute("SELECT accepted, in_archive FROM candidates WHERE cand_id=?", (cid,)).fetchone()
            accepted = bool(row and (row[0] or row[1])) or any(m.get("cand_id") == cid for m in self.archive.members)
            fit_dirs = [c.get("e4_raw_dir")] + [r[0] for r in self.conn.execute("SELECT raw_dir FROM evaluations WHERE cand_id LIKE ? AND cand_id != ?", (f"{cid}_env%", cid))]
            res = RET.slim_candidate(self.cfg, cid, accepted, eq_dir=c.get("eq_record"), fit_dirs=[d for d in fit_dirs if d], m6_dir=self.dir / f"m6_{cid}")
            c["slimmed"] = {"kept_full": res["kept_full"], "bytes": sum(res["freed"].values()) + res["m6"]}

    def submit_fitness(self, cid, c, rec):
        """The fitness evaluation of a proven candidate: E4 (arm M, B1@E4, B2) or Y (arm B0, `yosys` kind on the local pool);
        the job id is kept in candidates.e4_job_id whatever the fitness configuration."""
        prev = self.conn.execute("SELECT e4_job_id FROM candidates WHERE cand_id=?", (cid,)).fetchone()
        if prev is not None and prev[0]:   # a previous attempt submitted the job before dying: reuse it
            c["e4_job_id"], c["state"] = prev[0], "e4_pending"
            self.state["pending"][cid] = "e4"
            return
        j = J.dc_job(self.cfg, self.design, self.fit_cfg, self.phi, self.priority)
        if self.cfg["configs"][self.fit_cfg].get("tool") == "yosys_opensta":
            j["kind"] = "yosys"
        saif = rec.get("saif_c")
        j["payload"].update(rtl=[c["path"]], incdirs=[str(p) for p in K.abs_paths(self.design, self.design["incdirs"])], is_baseline=0, cand_id=cid)   # candidates `include D's files (cktevo spi, 2026-09-14)
        if saif and Path(saif).exists() and j["kind"] == "dc":
            j["payload"].update(saif=saif, saif_instance="bs_lockstep/u_c")
        jid = self._q().submit(j["kind"], j["payload"], design_id=self.row["design_id"], cand_id=cid, config=self.fit_cfg, priority=self.priority, timeout_sec=j["timeout_sec"])
        c["e4_job_id"], c["state"] = jid, "e4_pending"
        self.conn.execute("UPDATE candidates SET e4_job_id=? WHERE cand_id=?", (jid, cid))
        self.state["pending"][cid] = "e4"

    submit_e4 = submit_fitness

    def fit_row(self, cand_id):
        return self.conn.execute("SELECT * FROM evaluations WHERE cand_id=? AND config=? AND status='ok' ORDER BY eval_id DESC LIMIT 1", (cand_id, self.fit_cfg)).fetchone()

    def scalar_verdict(self, cid, c, row):
        """Arms with scalar feedback (spec 05 §5: B0 at the Y caliber, B1@E4, B2): the three-component gain against D under
        the fitness configuration, no floor; `improved` = any positive component (any positive gain), credited 1 to the
        produced class; the archive keeps the Pareto front of improved candidates; the feedback block carries the numbers
        only. No diagnosis row is written here: the M3 diagnosis at E4 of every object belongs to the analysis (PLAN 4.3)."""
        cand = record_from_row(row)
        c["e4_raw_dir"], c["dc_seconds"] = cand.get("raw_dir"), cand.get("dc_seconds")
        gains = {k: v for k, v in m3.relative_gains(self.base, cand, self.phi).items() if v is not None}   # a metric the caliber lacks (Y power) is absent
        improved = any(float(v) > 1e-12 for v in gains.values())
        label = "improved" if improved else "no_gain"
        credit = 1 if improved else 0
        cls_final = c.get("class_final")
        if not self.c2_allowed(c):   # a latency-mapped (c2) candidate is a map object only: no archive, no acceptance, no credit (spec 03 §2)
            improved, credit = False, 0
        self.bandit.credit(cls_final, credit)
        fb = {"class": cls_final, "caliber": self.fit_cfg, "diagnosis": label,
              "evidence": {"dA_pct": round(-100.0 * float(gains.get("area") or 0.0), 2), "dWNS_ns": round(float(gains.get("wns") or 0.0) * float(self.phi), 4),
                           "dP_pct": round(-100.0 * float(gains.get("power") or 0.0), 2)}}
        self.state["feedback"][cid] = fb
        c.update(state="final", label=label, gains=gains, credit=credit)
        self.state["pending"].pop(cid, None)
        in_archive = 0
        if improved:
            in_archive = int(self.archive.add({"cand_id": cid, "gains": gains, "gen": c["gen"], "label": label}))
            self.state["retained"] += 1   # "accepted" for scalar arms
            self.state["last_retained_gen"], self.state["stall"] = c["gen"], 0
        self.conn.execute("UPDATE candidates SET label=?, in_archive=?, accepted=?, class_final=? WHERE cand_id=?", (label, in_archive, in_archive, cls_final, cid))

    def finish_nonequiv(self, cid, rec, note):
        c = self.state["cands"][cid]
        diag = m3.diagnose(self.base, self.base, self.sigma, self.phi, v3_status=rec.get("verdict") or "error")
        self.apply_diagnosis(cid, c, diag, cand_rec=None)

    def diagnose_candidate(self, cid, c, row):
        cand = record_from_row(row)
        c["e4_raw_dir"], c["dc_seconds"] = cand.get("raw_dir"), cand.get("dc_seconds")
        fps = {k: v for k, v in self.state["fingerprints"].items() if k != cid}
        diag = m3.diagnose(self.base, cand, self.sigma, self.phi, v3_status="proven", k_sigma=float(self.cfg["noise"]["k_sigma"]),
                           fp_jaccard=float(self.cfg["diag"]["fp_jaccard"]), thresholds=self.thresholds, floor_class=self.floor_class,
                           run_fingerprints=fps, envelope=c.get("envelope_gains"))
        self.state["fingerprints"][cid] = {"metrics": {"area": cand["metrics"]["area"], "cells": cand["metrics"]["cells"]}, "hist": cand["hist"]}
        if diag.get("envelope_required") and not c.get("envelope_jobs"):
            self.submit_envelope(cid, c)
            c["diag_pending"] = diag
            return
        self.apply_diagnosis(cid, c, diag, cand_rec=cand)

    def submit_envelope(self, cid, c):
        """C2.1(d): text-level renamings of the candidate itself at E4; their gains bound what counts as retained."""
        from src.noise import rename_text as RT
        from src.noise import vast as V
        n = int(self.cfg["search"]["acceptance_envelope"]["n_perturbations"])
        try:
            ast, _d, _n = V.parse_files([c["path"]], workdir=self.dir / f"env_{cid}" / "parse", strict=False)
            variants = RT.text_variants([c["path"]], ast, f"{self.run_id}:{cid}", n)
        except Exception as e:
            c["envelope_error"] = f"{type(e).__name__}: {e}"[:200]
            variants = []
        jobs = []
        for k, mapping, texts in variants:
            p = self.dir / f"env_{cid}" / f"P1_text_{k}.v"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(next(iter(texts.values())))
            j = J.dc_job(self.cfg, self.design, "E4", self.phi, self.priority)
            j["payload"].update(rtl=[str(p)], incdirs=[], is_baseline=0, cand_id=f"{cid}_env{k}")
            jobs.append(self._q().submit(j["kind"], j["payload"], design_id=self.row["design_id"], cand_id=f"{cid}_env{k}", config="E4", priority=self.priority, timeout_sec=j["timeout_sec"]))
        c["envelope_jobs"], c["state"] = jobs, "envelope_pending"
        self.state["pending"][cid] = "envelope"
        if not jobs:
            self.finish_envelope(cid, c)

    def finish_envelope(self, cid, c):
        gains = []
        for k in range(len(c.get("envelope_jobs") or [])):
            row = self.conn.execute("SELECT * FROM evaluations WHERE design_id=? AND cand_id=? AND config='E4' AND status='ok' ORDER BY eval_id DESC LIMIT 1",
                                    (self.row["design_id"], f"{cid}_env{k}")).fetchone()
            if row is not None:
                gains.append(m3.relative_gains(self.base, record_from_row(row), self.phi))
        c["envelope_gains"] = gains
        row = self.e4_row(cid)
        cand = record_from_row(row)
        if len(gains) < int(self.cfg["search"]["acceptance_envelope"].get("n_min", 2)):
            diag = dict(c.get("diag_pending") or {})
            diag.update(label="fragile", sublabel=f"acceptance envelope unavailable ({len(gains)} of {len(c.get('envelope_jobs') or [])} perturbation runs)")
        else:
            fps = {k: v for k, v in self.state["fingerprints"].items() if k != cid}
            diag = m3.diagnose(self.base, cand, self.sigma, self.phi, v3_status="proven", k_sigma=float(self.cfg["noise"]["k_sigma"]),
                               fp_jaccard=float(self.cfg["diag"]["fp_jaccard"]), thresholds=self.thresholds, floor_class=self.floor_class,
                               run_fingerprints=fps, envelope=gains)
        diag["envelope"] = gains
        self.apply_diagnosis(cid, c, diag, cand_rec=cand)

    def apply_diagnosis(self, cid, c, diag, cand_rec):
        existing = self.conn.execute("SELECT * FROM diagnoses WHERE cand_id=?", (cid,)).fetchone()
        if existing is not None:   # written by a previous attempt that died before persisting its state: sync the state, insert nothing
            existing = dict(existing)
            ev = json.loads(existing.get("evidence_json") or "{}")
            gains = ev.get("gains") or {}
            label, credit, cls_final = existing["label"], int(existing.get("credit") or 0), existing.get("credited_class") or c.get("class_final")
            self.bandit.credit(cls_final, credit)
            self.state["feedback"][cid] = json.loads(existing.get("feedback_json") or "{}")
            c.update(state="final", label=label, gains=gains, credit=credit)
            self.state["pending"].pop(cid, None)
            if label == "retained":
                self.archive.add({"cand_id": cid, "gains": gains, "gen": c["gen"], "label": label})
                self.state["retained"] += 1
                self.state["last_retained_gen"], self.state["stall"] = c["gen"], 0
            return
        label = diag["label"]
        gains = (diag.get("evidence") or {}).get("gains") or {}
        parent = self.state["cands"].get(c.get("parent_id")) if c.get("parent_id") else None
        parent_gains = (parent or {}).get("gains") or {}
        improves = any(float(gains.get(m, 0)) > float(parent_gains.get(m, 0)) + 1e-9 for m in gains) and not any(float(gains.get(m, 0)) < float(parent_gains.get(m, 0)) - 1e-9 for m in gains)
        credit = m3.credit(diag, improves)
        cls_final = c.get("class_final")
        c2_blocked = not self.c2_allowed(c)     # spec 03 §2: a latency-mapped (c2) candidate is diagnosed for the map but never archived, accepted or credited
        if c2_blocked:
            credit = 0
        self.bandit.credit(cls_final, credit)   # produced class (DECISIONS 2026-09-14 C2.1(c))
        fb = m3.feedback_block(diag, cls_final, [], prior=(self.prior or {}))
        fb["floor_class"] = self.floor_class
        self.state["feedback"][cid] = fb
        c.update(state="final", label=label, gains=gains, credit=credit)
        self.state["pending"].pop(cid, None)
        in_archive = 0
        if label == "retained" and not c2_blocked:
            in_archive = int(self.archive.add({"cand_id": cid, "gains": gains, "gen": c["gen"], "label": label}))
            self.state["retained"] += 1
            self.state["last_retained_gen"], self.state["stall"] = c["gen"], 0
        attribution = diag.get("attribution") if diag.get("attribution") in ("measured", "prior") else None  # the table's CHECK; 'identical' lives in the evidence
        db.insert(self.conn, "diagnoses", {"cand_id": cid, "run_id": self.run_id, "label": label, "rung": diag.get("rung"), "capability": diag.get("capability"),
                                           "attribution": attribution, "fp_jaccard": (diag.get("evidence") or {}).get("fp_jaccard"),
                                           "offset_design": int(bool(diag.get("offset_design"))), "duplicate_of": diag.get("duplicate_of"),
                                           "envelope_json": json.dumps(diag.get("envelope")) if diag.get("envelope") is not None else None,
                                           "evidence_json": json.dumps(diag.get("evidence"), default=str), "feedback_json": json.dumps(fb, default=str),
                                           "credit": credit, "credited_class": cls_final, "floor_version": self.floor_version})
        self.conn.execute("UPDATE candidates SET label=?, in_archive=?, accepted=?, class_final=? WHERE cand_id=?", (label, in_archive, in_archive, cls_final, cid))

    def record_label(self, cid, rec, label, extra, *, gen, cls_requested, parent_id, path, note, call, cls_final=None, insert_row=True):
        """Labels decided without evaluation (duplicate answer, identical text, prescreened)."""
        if insert_row:
            db.insert(self.conn, "candidates", {"cand_id": cid, "run_id": self.run_id, "design_id": self.row["design_id"], "gen": gen, "parent_id": parent_id,
                                                "arm": self.row["arm"], "class_requested": cls_requested, "class_final": cls_final, "llm_model": self.row["llm_model"],
                                                "cost_usd": call["cost_usd"], "rtl_path": path, "note": note, "call_id": call["call_id"], "label": label,
                                                "prescreened": int(label == "prescreened")})
        else:
            self.conn.execute("UPDATE candidates SET label=? WHERE cand_id=?", (label, cid))
        db.insert(self.conn, "diagnoses", {"cand_id": cid, "run_id": self.run_id, "label": label, "duplicate_of": extra.get("duplicate_of"),
                                           "evidence_json": json.dumps(extra), "feedback_json": json.dumps({"diagnosis": label, **extra}), "credit": 0, "credited_class": cls_final})
        self.state["feedback"][cid] = {"class": cls_final or cls_requested, "diagnosis": label, **extra}
        self.state["cands"].setdefault(cid, {"cand_id": cid, "gen": gen, "parent_id": parent_id, "path": path, "class_requested": cls_requested, "class_final": cls_final, "state": "final"})
        self.state["cands"][cid]["label"] = label
        self.bandit.credit(cls_final or cls_requested, 0)

    # ------------------------------------------------------------------ bookkeeping
    def spent(self):
        dc = self.conn.execute("SELECT COALESCE(SUM(e.dc_seconds),0) FROM evaluations e JOIN candidates c ON (e.cand_id=c.cand_id OR e.cand_id LIKE c.cand_id || '_env%') WHERE c.run_id=?", (self.run_id,)).fetchone()[0]
        vcf = sum(float((self.state["cands"][k].get("v3_seconds") or 0)) for k in self.state["cands"])
        usd = self.conn.execute("SELECT COALESCE(SUM(amount),0) FROM budget_ledger WHERE run_id=? AND kind='llm'", (self.run_id,)).fetchone()[0]
        return float(dc) / 3600.0, vcf / 3600.0, float(usd)

    def write_gen_summary(self, gen):
        dc_h, vcf_h, usd = self.spent()
        db.insert(self.conn, "gen_summary", {"run_id": self.run_id, "gen": gen, "archive_json": self.archive.to_json(), "bandit_probs_json": json.dumps(self.bandit.probs()),
                                             "tau": None, "e_s": None, "spent_dc_hours_cum": dc_h, "spent_usd_cum": usd, "retained_count_cum": self.state["retained"],
                                             "pending_json": json.dumps(sorted(self.state["pending"])), "built_at": db.now(), "llm_calls_cum": self.state["calls"]})
        self.conn.execute("UPDATE runs SET spent_dc_hours=?, spent_vcf_hours=?, spent_usd=?, llm_calls=?, gens_done=? WHERE run_id=?",
                          (dc_h, vcf_h, usd, self.state["calls"], gen, self.run_id))

    def generation_due(self):
        st = self.state
        if st["gen"] == 0:
            return True
        current = [c for c in st["cands"].values() if c.get("gen") == st["gen"]]
        if all(c.get("state") == "final" for c in current):
            return True
        return st["issued_at"] is not None and (self.clock() - float(st["issued_at"])) >= float(self.cfg["search"]["gen_wait_sec"])

    def disk_guard(self):
        """Decision 2026-09-15 item 1: below `retention.min_free_gb` of free space on `/` the run submits nothing (no LLM call,
        no equivalence / fitness / envelope / repair job): status `paused_disk`, a line in the job log; it resumes by itself
        when space returns. -> True when the run may submit."""
        ok, free, thr = RET.disk_ok(self.cfg, C.results_dir(self.cfg))
        if ok:
            if self.state.get("paused_disk"):
                self.state["paused_disk"] = None
                self.conn.execute("UPDATE runs SET status='running' WHERE run_id=? AND status='paused_disk'", (self.run_id,))
                print(f"{self.run_id}: disk guard released ({free:.1f} GB free >= {thr:.0f} GB), resuming", flush=True)
            return True
        if not self.state.get("paused_disk"):
            self.state["paused_disk"] = {"since": db.now(), "free_gb": round(free, 1), "threshold_gb": thr}
            self.conn.execute("UPDATE runs SET status='paused_disk' WHERE run_id=?", (self.run_id,))
            self.save_state()
            print(f"{self.run_id}: DISK GUARD — {free:.1f} GB free on / is below {thr:.0f} GB: no new job is submitted until space returns (retention.min_free_gb)", flush=True)
        return False

    def step(self):
        """One scheduling round: apply arrived verdicts, build the next generation when due, persist. -> 'running' | 'done' |
        'paused_disk' (nothing submitted while the disk guard holds)."""
        st = self.state
        if not self.disk_guard():
            return "paused_disk"
        self.process_verdicts()
        if st["gen"] < int(st["K"]) and st["calls"] < int(st["budget_calls"]) and self.generation_due():
            before = st["retained"]
            self.build_generation()
            if st["gen"] > 1 and st["retained"] == before:
                st["stall"] += 1
        done = (st["gen"] >= int(st["K"]) or st["calls"] >= int(st["budget_calls"])) and not st["pending"]
        if done and not st["done"]:
            st["done"] = True
            dc_h, vcf_h, usd = self.spent()
            self.conn.execute("UPDATE runs SET status='done', finished_at=?, spent_dc_hours=?, spent_vcf_hours=?, spent_usd=? WHERE run_id=?", (db.now(), dc_h, vcf_h, usd, self.run_id))
        self.save_state()
        return "done" if st["done"] else "running"

    def run(self, poll_sec=None, sleep=time.sleep, max_steps=None):
        poll = float(poll_sec or self.cfg["search"].get("poll_sec", 30))
        steps = 0
        while True:
            if self.conn.execute("SELECT status FROM runs WHERE run_id=?", (self.run_id,)).fetchone()[0] == "superseded":
                print(f"{self.run_id}: superseded by the operator, not continued", flush=True)   # a retried queue job must not revive a stopped run (2026-09-15)
                return "superseded"
            status = self.step()
            steps += 1
            if status == "done" or (max_steps and steps >= max_steps):
                return status
            sleep(poll)
