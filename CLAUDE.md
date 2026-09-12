# Beyond-Synth — CLAUDE.md

Project: **Beyond the Synthesizer: Optimizing RTL for Gains Logic Synthesis Cannot Recover** (target: DAC 2027).
Research question: of the gains an LLM obtains by rewriting RTL, how much would the synthesizer have obtained on its own? This project defines and measures *retained gain* (gain that survives full-effort DC synthesis and exceeds a measured noise floor), uses *ladder search* to aim the LLM at the complement of what the synthesizer can do, and certifies results under synthesis configurations the search never sees. Full proposal: `docs/PROPOSAL.md`. Implementation plan: `docs/PLAN.md`.

## Your role

You are the **operator**: you build the framework, submit EDA jobs, aggregate results, and maintain the documentation. You are **never the subject**: the LLM inside the search loop is called only through the OpenAI API (fixed model, temperature, seed). Never use this session's Claude to generate or edit candidate RTL, prompt feedback, or diagnosis labels. The only exception is the "Dr.RTL original reference row" marked in `docs/PLAN.md` Phase 5.

## Directories

```
/home/hping/Beyond-Synth/        this project (code, data, results all here; remote https://github.com/hping666/Beyond-Synth)
  CLAUDE.md  STATUS.md  docs/  config/  src/  scripts/  tests/  data/  results/  reports/
/home/hping/eda-knowledge/       on-machine EDA tool overview (read README -> 02 -> 05 -> 06 -> 04 -> 01 -> 03 -> 07)
/hdd1/hping/eda/setup/env.sh     the only entry point for the EDA environment (then dc_shell / pt_shell / vcf / vcs are available)
/hdd1/hping/eda/flow/            existing flow scripts (selfcheck.py, e2e.py, ...) — call them, never modify them
/hdd1/hping/eda/libs/            .db files for nangate45 / asap7 / sky130hd
/home/hping/OpenROAD-flow-scripts/   ORFS (Yosys + OpenROAD + KLayout)
```

## First-time bootstrap (once, at the very start of Phase 0)

1. If `.git` does not exist: `git init`, create `.gitignore` (exclude `results/raw/`, `results/llm/`, `results/candidates/`, `.venv/`, large files such as `*.db`/`*.saif`/`*.vcd`/netlists, any Synopsys files, and `.env`), make the first commit.
2. GitHub remote `https://github.com/hping666/Beyond-Synth` (empty repository, already created by the user). You perform the authentication, but it requires one authorization action from the user: preferably generate a dedicated SSH key `~/.ssh/id_ed25519_beyond_synth`, print the **public** key and stop, asking the user to add it as a Deploy key with write access on that repository. After the user confirms, configure a Host alias in `~/.ssh/config`, run `git remote add origin git@github.com:hping666/Beyond-Synth.git`, then `git push -u origin main`. If the user instead provides a `GITHUB_TOKEN` environment variable, use HTTPS with a credential helper and never write the token into any file.
3. `OPENAI_API_KEY`: the user will direct you to place it in the server environment (`~/.bashrc` or the queue daemon's environment file, never inside the project directory). Verify it with a single minimal call (list models or a one-token request). Logs and STATUS record only "configured / not configured"; never print or commit any part of the key.
4. Only then proceed to Phase 0.1.

## Start of every session

1. Read `STATUS.md` (current phase, open questions, where the last session stopped).
2. If the environment section of `STATUS.md` is empty: read `eda-knowledge/` in order, run `source /hdd1/hping/eda/setup/env.sh && python3 /hdd1/hping/eda/flow/selfcheck.py`, and fill the environment section (tool versions, paths, license seats, flow-script API, known boundaries).
3. Read the current phase section of `docs/PLAN.md` and work against its acceptance criteria.
4. Before the session ends: update `STATUS.md` (progress, decisions, open questions, next steps), commit, push.

## Hard rules

1. **Never modify `/hdd1/hping/eda/flow/`.** If a change is unavoidable: record the reason in `docs/DECISIONS.md` first, then re-run `selfcheck.py` and `e2e.py` after the change; both must pass before committing.
2. **DC returns 0 on failure and does not raise; its main failure mode is silently producing wrong data.** Every EDA step must check exceptions, return codes, Error/Warning patterns in logs, and the existence and non-emptiness of outputs. Every decision rule is verified in **both directions**: correct inputs must pass, incorrect inputs must be caught (both directions have test cases in `tests/`). Evaluation records that have not passed the bidirectional checks must not be written to the results database.
3. **Hidden-configuration results are written only to `results/hidden/hidden.sqlite`**, and only `scripts/report_hidden.py` may read it. Search code, prompt templates, the predictor, and any analysis you perform during Phases 2–5 must not read that file. Add a deny rule in `.claude/settings.json` that blocks reads of that path (the report script excepted).
4. **Dev / held-out separation**: prompt templates, the predictor, and thresholds are tuned only on designs marked `dev` in `config/experiments.yaml`; held-out designs only produce results.
5. **Results are append-only**: directories under `results/` are named by content hash; a re-run writes a new directory; database records carry `git_sha`, `cfg_hash`, and tool versions. `rm -rf results/*` is forbidden.
6. **Budgets live in `config/experiments.yaml` and you may not change them**: per-phase LLM dollar caps, DC/PT/VC Formal concurrency caps, per-job timeouts. When a cap is reached, stop and write STATUS.
7. **Small before large**: any new component is first run end-to-end on one design, its reference outputs saved, and a smoke test written, before scaling up. Batch jobs must not be launched on components that have not passed their smoke tests.
8. **Never work around tool errors**: SEQ inconclusive is recorded as inconclusive, not treated as proven; a DC error means fix the input or record "evaluation failed", never silently change settings; a failing testbench means the candidate is discarded, not the criterion relaxed.
9. **Long jobs are decoupled from the session**: all batch EDA and LLM jobs are executed by the daemon in `scripts/queue/` (`setsid`, logs on disk, resumable). You only submit, poll, and aggregate. A dropped desktop SSH session must not affect running jobs.
10. **Writing to `eda-knowledge/05-traps.md` is append-only**, and a new trap must first be verified with bidirectional test cases; each entry carries the date and the path in this project.
11. **Configuration-driven**: rung commands, constraints, thresholds, and design-set lists exist only in `config/experiments.yaml`; code must not hard-code these numbers.
12. **Secrets live only in environment variables** (`OPENAI_API_KEY`, `GITHUB_TOKEN`); never write them to files, logs, or the conversation. Synopsys tools and library files never enter git and never leave the server.
13. **Every session ends with `git add -A && git commit && git push`** (large result files are excluded by .gitignore; whether database snapshots enter git is decided in DECISIONS). A failed push must be recorded in STATUS, never silently skipped.

## STOP gates (write the report, stop, wait for human confirmation; while waiting, work on engineering tasks unrelated to the gate)

| Gate | When | Report |
|---|---|---|
| G0 | End of Phase 0 | Environment self-check results; whether VC Formal SEQ/DPV are usable; one successful run each of `-spg`, ASAP7, sky130hd; whether the license permits publishing cross-tool comparisons |
| G1 | Noise floor measured | Distribution of σ_D per design and rung; if the median exceeds 5%, propose an alternative truncation |
| G2 | SEQ pilot done | proven / falsified / inconclusive fractions and runtimes for classes (b), (c1), (c2) |
| G3 | E4 runtime measured | E4 seconds per design; DC-hour estimates for full-E4 and cascade scales; recommendation on whether screening enters the main method |
| G4 | LLM calibration done | For the four models: retained candidates per dollar and per DC-hour, best gain, class distribution; recommended main model |
| G5 | Exp1 done | Map shape (concentrated / near-zero / diffuse); static-rule misclassification rates; predictor accuracy; recommended paper form |

## Working rhythm

- Each phase: write `reports/<phase>.md` (one page: what was done, numbers, anomalies, next steps), update `STATUS.md`, commit, push.
- First thing each day: `python3 scripts/status.py` (queue, seats, budget, failed jobs).
- Any change to a decision rule -> bidirectional test cases -> `pytest tests/` all green -> only then batch runs.
- Anything that "looks strange": check `eda-knowledge/05-traps.md` first, then `docs/DECISIONS.md`, then act.

## Common commands

```bash
source /hdd1/hping/eda/setup/env.sh
python3 /hdd1/hping/eda/flow/selfcheck.py        # 20 checks, ~9 min
python3 /hdd1/hping/eda/flow/e2e.py              # 11 checks, ~3.5 min
source .venv/bin/activate
pytest tests/ -x                                  # all smoke / bidirectional tests
python3 scripts/status.py                         # queue, seats, budget
python3 scripts/queue/submit.py <job.yaml>        # submit a job
python3 scripts/report_phase.py <phase>           # generate a phase report
python3 scripts/report_hidden.py                  # the only script allowed to read the hidden DB (after Phase 5)
```

## Document index

`docs/PROPOSAL.md` research proposal · `docs/PLAN.md` phased implementation plan and acceptance criteria · `docs/spec/` module specifications (read as needed) · `docs/DECISIONS.md` decision log · `STATUS.md` current state · `config/experiments.yaml` all parameters · `reports/` phase reports
