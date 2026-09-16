# Phase 5 pre-launch report (2026-09-15T17:57; decision 2026-09-15 item 6)

**NO-GO** — probe not finished

## Probe (G5 item 1)

| model | cktevo_nn_engine__spikeLayer8_H7 | drrtl_datapath | drrtl_pcie | qualifies (>= 5 proven on a design) |
|---|---|---|---|---|
| gpt-5.6-terra | 2 | 13 | 30 | yes |
| gpt-5.6-sol | 0 | 16 | 22 | yes |

Probe runs: 12, finished: False. Large tier for arms M / B2: gpt-5.6-terra — gpt-5.6-terra carries the large tier (>= min_proven on a probe design).

## Run matrix

630 runs, 37800 LLM calls: gpt-5.6-luna 450 runs, gpt-5.6-terra 180 runs.

## Projections against the caps

| quantity | projected | cap | inside |
|---|---|---|---|
| llm_usd | 355.0 | 600.0 | yes |
| disk_gb | 43.7 | 61.0 | yes |
| vcf_hours | 2059.3 | 4200.0 | yes |
| dc_hours | 1911.9 | 4000.0 | yes |

Free space now 81.0 GB (cap = free minus 20 GB); disk projection = the tiered policy plus H1 / H3 / H5 on every E4-evaluated candidate (reports/data/phase5_footprint.md). DC hours count the E4 fitness runs of the proven candidates (B0: its accepted candidates), the hidden configurations per `exp5.hidden_scope` and 10 % for envelope and single-flag runs; VC Formal hours are the measured seconds per LLM call of the same model and tier (or the main model's).

## Per-call figures used (measured where a finished run of the model on the tier exists)

| model | tier | USD / call | VCF s / call | proven / call | accepted / call | E4 s / proven |
|---|---|---|---|---|---|---|
| gpt-5.6-luna | large | 0.003 (measured) | 22.0 (measured) | 0.0 (measured) | 0.0 | 143.4 |
| gpt-5.6-luna | medium | 0.0029 (measured) | 302.1 (measured) | 0.341 (measured) | 0.156 | 87.3 |
| gpt-5.6-luna | small | 0.0016 (measured) | 49.1 (measured) | 0.81 (measured) | 0.36 | 80.8 |
| gpt-5.6-terra | large | 0.0271 (measured) | 33.9 (measured) | 0.446 (measured) | 0.04 | 114.1 |
| gpt-5.6-terra | medium | 0.0294 (from gpt-5.6-luna on the tier) | 302.1 (from gpt-5.6-luna on the tier) | 0.341 (from gpt-5.6-luna on the tier) | 0.156 | 87.3 |
| gpt-5.6-terra | small | 0.0156 (from gpt-5.6-luna on the tier) | 49.1 (from gpt-5.6-luna on the tier) | 0.81 (from gpt-5.6-luna on the tier) | 0.36 | 80.8 |

