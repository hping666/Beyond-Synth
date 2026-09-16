# Probe report (2026-09-15 21:05; decision 2026-09-15 item 5)

```text
(12 superseded runs not shown: the first launch, stopped after the scope-splice fix)
r20260915_173230_drrtl_pcie_-terra_s1        gpt-5.6-terra  drrtl_pcie                         done     gens 6 calls 30 usd 0.71 cands 30 proven 26 sim_fail 4 falsified 0 rejected 0 inconclusive 0 scope_flags 0 repairs 2
r20260915_173230_drrtl_pcie_-terra_s2        gpt-5.6-terra  drrtl_pcie                         done     gens 5 calls 30 usd 0.72 cands 30 proven 21 sim_fail 9 falsified 0 rejected 0 inconclusive 0 scope_flags 0 repairs 8
r20260915_173230_drrtl_pcie_6-sol_s1         gpt-5.6-sol    drrtl_pcie                         done     gens 6 calls 30 usd 1.48 cands 30 proven 24 sim_fail 0 falsified 0 rejected 0 inconclusive 6 scope_flags 0 repairs 0
r20260915_173230_drrtl_pcie_6-sol_s2         gpt-5.6-sol    drrtl_pcie                         done     gens 6 calls 30 usd 1.40 cands 30 proven 27 sim_fail 1 falsified 0 rejected 1 inconclusive 1 scope_flags 0 repairs 2
r20260915_173230_ikeLayer8_H7_-terra_s1      gpt-5.6-terra  cktevo_nn_engine__spikeLayer8_H7   done     gens 6 calls 30 usd 1.00 cands 30 proven 1 sim_fail 0 falsified 0 rejected 1 inconclusive 1 scope_flags 0 repairs 1
r20260915_173230_ikeLayer8_H7_-terra_s2      gpt-5.6-terra  cktevo_nn_engine__spikeLayer8_H7   done     gens 6 calls 30 usd 1.06 cands 30 proven 2 sim_fail 0 falsified 0 rejected 2 inconclusive 1 scope_flags 0 repairs 1
r20260915_173230_ikeLayer8_H7_6-sol_s1       gpt-5.6-sol    cktevo_nn_engine__spikeLayer8_H7   done     gens 6 calls 30 usd 2.39 cands 30 proven 0 sim_fail 0 falsified 3 rejected 0 inconclusive 4 scope_flags 0 repairs 2
r20260915_173230_ikeLayer8_H7_6-sol_s2       gpt-5.6-sol    cktevo_nn_engine__spikeLayer8_H7   done     gens 6 calls 30 usd 2.13 cands 30 proven 0 sim_fail 1 falsified 2 rejected 0 inconclusive 0 scope_flags 0 repairs 1
r20260915_173230_rtl_datapath_-terra_s1      gpt-5.6-terra  drrtl_datapath                     done     gens 6 calls 30 usd 0.99 cands 29 proven 20 sim_fail 3 falsified 0 rejected 2 inconclusive 0 scope_flags 0 repairs 3
r20260915_173230_rtl_datapath_-terra_s2      gpt-5.6-terra  drrtl_datapath                     done     gens 5 calls 30 usd 0.99 cands 30 proven 21 sim_fail 5 falsified 0 rejected 1 inconclusive 0 scope_flags 0 repairs 5
r20260915_173230_rtl_datapath_6-sol_s1       gpt-5.6-sol    drrtl_datapath                     done     gens 6 calls 30 usd 2.46 cands 30 proven 26 sim_fail 0 falsified 0 rejected 1 inconclusive 1 scope_flags 5 repairs 0
r20260915_173230_rtl_datapath_6-sol_s2       gpt-5.6-sol    drrtl_datapath                     done     gens 6 calls 30 usd 2.14 cands 30 proven 28 sim_fail 0 falsified 0 rejected 1 inconclusive 1 scope_flags 0 repairs 1
probe spend 24.18 of 120 USD
repair yield per failure type (decision 2026-09-15 item 5):
  | failure type of the original | repair calls | proven | accepted | retained / improved | scope flags (restored) | proven per repair call | not repaired (budget / unusable / already a repair) |
  |---|---|---|---|---|---|---|---|
  | rejected | 7 | 5 | 0 | 1 | 0 | 71 % | 2 |
  | sim_fail | 17 | 13 | 5 | 6 | 0 | 76 % | 6 |
  | falsified | 2 | 0 | 0 | 0 | 0 | 0 % | 3 |
scope violations: none
  gpt-5.6-sol    cktevo_nn_engine__spikeLayer8_H7   runs 2 done 2 candidates 60 proven 0 -> below min_proven (rule: >= 5 proven on the design)
  gpt-5.6-sol    drrtl_datapath                     runs 2 done 2 candidates 60 proven 54 -> carries the large tier (rule: >= 5 proven on the design)
  gpt-5.6-sol    drrtl_pcie                         runs 2 done 2 candidates 60 proven 51 -> carries the large tier (rule: >= 5 proven on the design)
  gpt-5.6-terra  cktevo_nn_engine__spikeLayer8_H7   runs 2 done 2 candidates 60 proven 3 -> below min_proven (rule: >= 5 proven on the design)
  gpt-5.6-terra  drrtl_datapath                     runs 2 done 2 candidates 59 proven 41 -> carries the large tier (rule: >= 5 proven on the design)
  gpt-5.6-terra  drrtl_pcie                         runs 2 done 2 candidates 60 proven 47 -> carries the large tier (rule: >= 5 proven on the design)

```
