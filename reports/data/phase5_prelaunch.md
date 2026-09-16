# Phase 5 pre-launch report (2026-09-15T19:15; decisions 2026-09-15 item 6 and evening items 3 / 7)

**NO-GO** — probe not finished

## Probe (G5 item 1)

| model | cktevo_nn_engine__spikeLayer8_H7 | drrtl_datapath | drrtl_pcie | qualifies (>= 5 proven on a design) |
|---|---|---|---|---|
| gpt-5.6-terra | 3 | 41 | 47 | yes |
| gpt-5.6-sol | 0 | 50 | 47 | yes |

Probe runs: 12, finished: False. Model assignment by tier (decision 2026-09-15 evening, item 3; supersedes the probe rule for the large tier): small: gpt-5.6-luna on every arm, gpt-5.6-terra on M/B2 (second); medium: gpt-5.6-luna on every arm, gpt-5.6-terra on M/B2 (second); large: gpt-5.6-terra on every arm, gpt-5.6-luna on M (contrast). Probe designs below min_proven under every model: cktevo_nn_engine__spikeLayer8_H7 — kept in the large tier; their near-zero proven rate is the LLM-correctness limit and is reported as such (item 4).

## Run matrix

612 runs, 36720 LLM calls: gpt-5.6-luna 378 runs, gpt-5.6-terra 234 runs.

| model | B0 | B1_E4 | B2 | DrRTL_reimpl | M | total |
|---|---|---|---|---|---|---|
| gpt-5.6-luna | 72 | 72 | 72 | 72 | 90 | 378 |
| gpt-5.6-terra | 18 | 18 | 90 | 18 | 90 | 234 |

| tier | model | role | runs |
|---|---|---|---|
| large | gpt-5.6-luna | contrast | 18 |
| large | gpt-5.6-terra | main | 90 |
| medium | gpt-5.6-luna | main | 270 |
| medium | gpt-5.6-terra | second | 108 |
| small | gpt-5.6-luna | main | 90 |
| small | gpt-5.6-terra | second | 36 |

Seat targets at launch: vcf_seats_target = dc_seats_target = 50 (restored to the Phase 3-4 targets afterwards); search runs in their own pool of 16.

## Projections against the caps

| quantity | projected | cap | inside |
|---|---|---|---|
| llm_usd | 447.8 | 600.0 | yes |
| disk_gb | 44.0 | 53.5 | yes |
| vcf_hours | 2192.0 | 4200.0 | yes |
| dc_hours | 1447.9 | 4000.0 | yes |

Free space now 78.5 GB (cap = free minus the 20 GB margin minus the 5 GB reserve of the storage decision 2026-09-15); disk projection = the tiered policy with the kept-record equivalence slimming and the hidden registrations of `exp5.hidden_scope` / `hidden_audit_frac` (reports/data/phase5_footprint.md). Stamps: equiv_version = phase5; floor_version = phase4. DC hours count the E4 fitness runs of the proven candidates (B0: its accepted candidates), the hidden configurations per `exp5.hidden_scope` and 10 % for envelope and single-flag runs; VC Formal hours are the measured seconds per LLM call of the same model and tier (or the main model's).

## Per-call figures used (measured where a finished run of the model on the tier exists)

| model | tier | USD / call | VCF s / call | proven / call | accepted / call | E4 s / proven |
|---|---|---|---|---|---|---|
| gpt-5.6-luna | large | 0.003 (measured) | 22.0 (measured) | 0.0 (measured) | 0.0 | 143.4 |
| gpt-5.6-luna | medium | 0.0029 (measured) | 302.1 (measured) | 0.341 (measured) | 0.156 | 87.3 |
| gpt-5.6-luna | small | 0.0016 (measured) | 49.1 (measured) | 0.81 (measured) | 0.36 | 80.8 |
| gpt-5.6-terra | large | 0.0304 (measured) | 119.6 (measured) | 0.506 (measured) | 0.067 | 132.8 |
| gpt-5.6-terra | medium | 0.0294 (from gpt-5.6-luna on the tier) | 302.1 (from gpt-5.6-luna on the tier) | 0.341 (from gpt-5.6-luna on the tier) | 0.156 | 87.3 |
| gpt-5.6-terra | small | 0.0156 (from gpt-5.6-luna on the tier) | 49.1 (from gpt-5.6-luna on the tier) | 0.81 (from gpt-5.6-luna on the tier) | 0.36 | 80.8 |

