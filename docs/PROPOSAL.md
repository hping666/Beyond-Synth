# Beyond the Synthesizer: Optimizing RTL for Gains Logic Synthesis Cannot Recover

Research proposal (detailed version). All literature numbers quoted here are taken from the reference papers; budgets and runtimes are estimates and are marked as such; the full reference list is at the end.

---

## 1. Thesis and three contributions

**Problem.** Of the gains an LLM obtains by rewriting RTL, how much would the synthesizer have obtained on its own? Nobody can answer this today, and existing methods were not designed around the question. The real value of an RTL rewrite to a chip is the part that **remains** after a production-grade synthesis flow has optimized at full effort — the part the synthesizer cannot do and that can only be done at the RTL level. This quantity has never been defined, never been measured, and no search has ever used it as its target.

**Thesis.** The synthesizer is a fixed but tiered family of transformations T; the value of an LLM rewrite exists only in the complement of T. Existing work treats the synthesizer as a scorer; this work treats it as an adversary to be subtracted: first measure where the complement is, then aim the search at it, then prove that what was found really is the complement.

**Three contributions.**

- **C1 Definition and map of the residual.** Define retained gain (gain at the full-effort rung that exceeds the noise floor); build the capability ladder E1–E4 inside DC; measure the noise floor σ_D of every design at every rung with semantics-preserving surface perturbations; produce the first map of "rewrite class × absorbing rung/capability × cross-configuration retention", and re-evaluate the various settings labeled "DC" in the literature on one scale.
- **C2 Ladder search framework.** Fitness is defined only at the full-effort rung E4 (retained gain); lower rungs serve only as screening and cheap negative feedback, with the screening rung chosen automatically per design, the promotion threshold adjusted automatically by budget, and both calibrated by E4 audits; every E4 candidate receives a five-way diagnosis with the original design as control (absorbed / noise / harmful / trade-off / retained) that serves as prompt feedback and operator credit. Claim: at equal DC hours, the search finds more retained gain than full-E4 search and is erased less than low-rung search. The framework is skeleton-agnostic: the main skeleton is parallel-candidate hill climbing with a small archive (isomorphic to Dr.RTL and ARES), verified also on the COEVO and REvolution skeletons.
- **C3 Comprehensive experimental validation.** Four design suites (Dr.RTL's 20 human-written designs, RTL-OPT's 36 pairs, CktEvo modules, RTLLM), an equal-DC-hour budget, comparison against low-rung search, static complement prompting, naive commercial-in-the-loop search, and Dr.RTL; all accepted candidates certified under a set of configurations the search never sees (tight constraint, second technology libraries, physical-aware synthesis, PrimeTime/PTPX signoff, production-representative configuration) with a reported speculation rate — the first implementation of HORIZON's two-level protocol for PPA optimization; open-source reproduction layer and place-and-route spot checks; skeleton independence (COEVO / REvolution) and second-model checks; per-component ablations.

C1 is analysis, C2 is method, C3 is validation; all three share one ladder: C1 measures with it, C2 searches with it, C3 certifies with it.

## 2. Problem definition

Given a functionally correct original design D (Verilog, single module or CktEvo-level module), synthesis constraint Φ, a rewrite generator G (a frozen LLM inside a search skeleton), the synthesizer's capability ladder, and a set of hidden configurations. For a candidate C ≡ D (sequentially equivalent):

- **Retained-gain vector** g(C) = PPA(E4(D)) − PPA(E4(C)), three components: area, timing (WNS/TNS, supplemented by critical-path delay under knee-point constraints), power.
- **Noise floor** σ_D(k): the spread of PPA of n semantics-preserving surface perturbations of D at rung k (one value per design, rung and metric).
- **Retained**: some component g > 2σ_D(E4) and no component g < −2σ_D(E4); **trade-off**: some component > 2σ_D and some component < −2σ_D; otherwise no retained gain, which the diagnoser splits into absorbed / noise / harmful.
- **Residual**: the residual of a search on a design is the retained gain of the Pareto set of accepted candidates; the residual of a method is its distribution over the design set.

Within a design, the ranking by g is identical to the ranking by E4 PPA — this work does not present "subtracting the original design" as a new fitness; the contributions are the measurement around it (C1), the search (C2), and the validation (C3).

**Questions.** (a) For the candidates produced by existing methods, by rewrite class: at which rung and by which capability are they absorbed, how many fall within the noise floor, how many are retained? (b) Can a search whose fitness is defined on retained gain, screened at low rungs, and fed back with comparative diagnoses find more retained gain at equal DC hours than full-E4 search and than low-rung search? (c) How much of the gain found survives under configurations the search never saw?

**Toolchain.** Synopsys Design Compiler (fixed version, 50-way parallelism, `set_host_options -max_cores 4` fixed for bit-exact reproducibility), PrimeTime and PrimeTime-PX, VC Formal (SEQ and DPV), VCS; technology libraries Nangate45 (main), ASAP7 and sky130hd (hidden), with DC physical reference libraries for `-spg`. On the open-source side, Yosys / ABC / OpenSTA / OpenROAD play three roles: the reference caliber Y (the literature's caliber), the open-source ladder of the supplementary experiment, and the open-source reproduction layer.

**DC capability ladder (main axis).** Tiered by DC's own capabilities; each rung corresponds to documented, RTL-visible transformations, enabled cumulatively:

- E1 = `compile` with only the standard synthetic library (no DesignWare Foundation): constant propagation, dead-logic removal, basic Boolean optimization, simple resource sharing; `-map_effort medium/high` is DC's native effort knob (SymRTLO used medium). The attribution rung E1d = `compile` + DesignWare Foundation isolates the DesignWare architecture choice, which Phase 0 measured to change `compile` results by 3–6% in either direction (DECISIONS 2026-09-12).
- E2 = `compile_ultra`: adds datapath extraction and arithmetic restructuring, DesignWare Foundation implementation selection (added by the command itself), boundary optimization, two automatic-ungrouping phases, the area-oriented compile strategy. The most common "DC" rung in the literature (RTL-OPT).
- E3 = E2 + `-retime`: register retiming, pipeline balancing. Corresponds specifically to class (c1) rewrites.
- E4 = E3 + `-gate_clock`: wire-load-mode full-effort synthesis (`compile_ultra` + retiming + automatic clock-gating insertion). `-gate_clock` must be included, otherwise clock-gating rewrites would be misjudged as retained. E4 is the **main scoring configuration**. On the DC version used here (W-2024.09) the option `-timing_high_effort_script` is documented as ignored (kept for backward compatibility) and the timing-high-effort strategy variable exists only in topographical mode; it is therefore not part of the wire-load ladder and is covered by the hidden configuration H3 (DECISIONS 2026-09-12; the G3 gate revisits the main scoring configuration if H3 is affordable and disagrees with E4).
- `-spg` (physical guidance) requires physical libraries and a floorplan; it is physical awareness rather than a logic-synthesis capability and belongs to the hidden configurations (H3).

Two handling rules: (i) the DesignWare architecture choice, `-retime` and `-gate_clock` are independent knobs; the linear order is a projection from the flow's point of view; for sampled candidates entering the ladder analysis, the attribution rungs E1d (`compile` + DesignWare), E2r (= E3, `compile_ultra -retime`) and E2g (`compile_ultra -gate_clock`) attribute absorption to a specific capability; a hierarchy rung E2u = `compile_ultra -no_autoungroup` is added only if Phase 4 shows many class-(b) candidates absorbed at E2. (ii) DC results are not monotone in capability (`-retime` can increase area, the high-effort script trades area for timing, ICGs add area and reduce power); the "absorption rung" is defined as "the rung from which all higher rungs stay within the noise band" (permanent absorption), and non-monotone cases are reported separately.

**Reference caliber Y.** Yosys `synth -top X; abc -liberty nangate45.lib; stat` + OpenSTA. This is the caliber of COEVO, REvolution, the ChipSeek series, CODMAS and Metamorphosis. Y is not a rung of the ladder: Y→E1 is a change of tool, E1→E4 adds capabilities within the same tool, and the two are not comparable. Y serves three purposes only: dialogue with literature numbers, a candidate screening rung (its predictive power decided by Experiment 1), and the open-source reproduction layer.

**Open-source ladder O0–O2 (supplementary experiment).** O0 = Y; O1 = `synth -flatten` + `opt -full` + `share -aggressive`; O2 = O1 + heavy ABC script (multiple `resyn2` rounds / `dch` / `&deepsyn`). Purpose: separate the "tool effect" from the "capability effect" — a rewrite absorbed at both O2 and E2 is "something any decent synthesizer does", one absorbed at E2 but retained at O2 is "a commercial-only capability", and only one retained at E4 is the complement. It is also the fallback when the license restricts publication (comparisons within one tool are unrestricted). OpenROAD is not a synthesizer and appears only in the reproduction layer.

**Main constraint Φ_main.** Following ASPEN, sweep the clock once per original design (about 5–7 E4 syntheses) and take the knee frequency where area starts to rise sharply; all candidates inherit their original design's Φ_main. The Dr.RTL head-to-head sub-experiment uses 0.1 ns to match its setting.

**Hidden configurations.** H1 = 0.1 ns tight constraint (also Dr.RTL's visible caliber, interpreted as "retention under a constraint shift"); H2a = ASAP7 and H2b = sky130hd (each with its own knee constraint); H3 = E4 + `-spg` in topographical mode with the timing-high-effort strategy variable enabled (physical-aware full effort); H4 = independent PrimeTime timing check + PrimeTime-PX signoff power on the same SAIF; H5 = production-representative configuration `compile_ultra -no_autoungroup -gate_clock` (no `-retime`, hierarchy preserved; see §3.6); if available, H6 = a second DC version or Genus.

**Open-source reproduction layer O.** Yosys `synth -flatten; opt -full` + deterministic multi-round ABC (no randomization) + OpenROAD floorplan/place STA; run only on final designs, answering "how much of the conclusion survives under an open-source flow".

## 3. Background and motivation: the chain of evidence

### 3.1 The synthesizer erases most of the LLM's "gains"

- **CktEvo**: 11 real repositories (611–12,285 lines, 6–42 modules), AlphaEvolve-style evolution. DeepSeek-v3 under Yosys + Sky130 reduces geometric-mean ADP by 10.50%; §4.4 **re-runs the same evolution experiment with a commercial toolchain (DC compile_ultra -retime -timing_high_effort_script, Formality equivalence)** and only 1.77% remains, with risc / sdc_ctrl / spi at 0. The authors' manual audit: synthesis-friendly coding-style changes, logic flattening and pruning of redundant pipeline registers, state-machine merging/re-encoding — "these local rewrites are often reduced to the same gate-level netlist by commercial synthesis". Note: this is a DC-in-the-loop result, not a post-hoc re-evaluation; it is also risk evidence for this work's C2 expectation.
- **RTL-OPT** (Lu et al.): of RTLRewriter's 43 code pairs, only 13 human-optimized versions are actually better under DC compile_ultra (24 under Yosys); of its 12 released LLM-optimized samples, only 3 are better under compile_ultra. The authors conclude that Yosys amplifies artificially planted differences, commercial tools erase artificial inefficiencies, and LLM optimizations mostly replicate compiler transformations. RTL-OPT's own 36 pairs of real engineer optimizations (14 to 20K cells): 27.64% area improvement under DC, 11.25% under Yosys; 35/36 pairs hold at 1 ns, 23–24 hold at 0.1 ns and 12–13 turn into PPA trade-offs (the text and the table disagree by one).
- **Dr.RTL**: DC + Nangate45 + 0.1 ns, Jasper SEC. Fig. 9 shows the same method gaining most under the Yosys caliber; Table 3 re-implements RTLRewriter / SymRTLO under DC on human-written designs, leaving −3.1% / −1.4% area.
- **Metamorphosis**: on semantics-preserving mutants (Yosys caliber), LLM methods beat Yosys on logic operations and datapaths (Yosys wires 4.67× on nested-expression mutants) but degrade across the board on FSMs, timing control flow and clock domains, no longer beating compiler methods.

### 3.2 "DC" is not one caliber but a ladder

Under the single label "DC", the literature's settings span E1 to E4:

| Work | Actual setting | Rung |
|---|---|---|
| SymRTLO | DC 2019, medium mapping effort, RTLRewriter's artificial benchmark; reports −38.05% area, still claims −27.7% with flatten + high effort | E1 |
| LongRTL | DC + ASAP7, compile command and constraints unstated; Table I shows alu critical path 1555 ps and fpu_post 3009 ps, possible only under unconstrained / very loose synthesis; reports ~25% single-module PPA improvement | E1–E2, not timing-driven |
| RTL-OPT | `compile_ultra`, 1 ns (0.1 ns also reported) | E2 |
| CktEvo (commercial arm) | `compile_ultra -retime -timing_high_effort_script`, Sky130 | E3 on DC W-2024.09, where the high-effort flag is a no-op; its effect on CktEvo's DC version is unknown (no `-gate_clock`) |
| Dr.RTL | DC, 0.1 ns tight constraint, Nangate45 | E2 + tight constraint |
| ARES | DC + PrimeTime, max frequency + area, JasperGold SEC | rung unstated |
| ASPEN | commercial synthesis, area/power/delay effort all set to high, clock sweep to the knee | high rung |

Conclusion: even after moving to DC, the numbers are mutually incomparable; the collapse from SymRTLO's 38% to Dr.RTL's re-implemented 1.4% mixes two effects — benchmark realism (artificial redundancy vs human-written designs) and rung — and this work reports the two effects separately rather than lumping them into "tool caliber". No work reports the synthesizer's sensitivity to surface form itself: ROVER reports that non-functional changes such as renaming a variable can change area by up to 15%, and "gains" below that jitter have been counted as gains.

### 3.3 But the complement exists, and it has a shape

- **The other side of RTL-OPT**: its six classes of human optimization patterns (bit-width reduction, precomputation/LUT, operator strength reduction, control simplification, resource sharing, state encoding) include things the synthesizer "nominally does", yet 35 of 36 pairs remain better under compile_ultra. What DC nominally can do, it often does not — whether sharing fires depends on whether exclusivity can be recognized; bit-width reduction needs value-range analysis DC does not perform. So the complement is not only "architectural"; it is "any rewrite that requires knowledge the synthesizer lacks": value ranges, syntactically invisible mutual exclusivity, algebraic identities, cross-cycle invariants.
- **RTLScout**: an FP16 multiplier from 121 µm² / 1618 ps to 79 µm² / 891 ps; scaling Mockturtle gate-level optimization to 19,500 steps reaches only 92 µm² / 994 ps, and Deepsyn 91 µm² / 1088 ps — gate-level optimization effort cannot substitute for algorithm-level rewriting.
- **EvolVE**: on IC-RTL, GEMM evolves from an output-stationary systolic array to a mixed-stationary one, latency 1448 → 776 ns, buffer rows 2n−1 → n; Huffman coding PPA −66%. All architectural rewrites, and they hold under the DC (TSMC 180 nm) final evaluation.
- **Dr.RTL**: synthesis is constrained by the original RTL structure and cannot change higher-level design choices such as datapath organization or pipelining (from Dr.RTL's introduction). Dr.RTL's skill library of 47 pattern–strategy entries has a dedicated category "Invalid: already done by synthesis tool" — such boundaries were distilled from failed trajectories on DC, not hand-written.
- **Synopsys' official mechanism**: `analyze_datapath_extraction` emits HDL messages when datapath extraction is blocked by RTL coding style, and rewriting the RTL per these messages significantly improves QoR (§3.6). This is the official version of "the synthesizer's effective boundary depends on coding style, and RTL rewrites can unlock synthesis capabilities".

### 3.4 Counter-evidence and the layered explanation

Pluto reports consistent efficiency trends between Genus and Yosys; Fu et al. find Spearman > 0.99 across three technology libraries under the same tool; RTL-OPT's own 36 pairs hold in 33 cases under Yosys and 35 under DC. These do not contradict the CktEvo/Dr.RTL conclusions: the disagreement between calibers concentrates on **artificial-redundancy pairs** (RTLRewriter) and **LLM candidate distributions** (CktEvo, Dr.RTL Fig. 9), while on **human-written optimization pairs** the two calibers agree. Experiment 1 of this work is performed on real LLM candidate distributions and is calibrated with human-written pairs at the same time, making this layering explicit.

### 3.5 The common structure of existing methods and the gaps

Except SymRTLO (single-pass templated rewriting + symbolic verification) and SmaRTLy (a rule-based algorithm without an LLM), every training-free LLM optimization work contains the same step — evaluate candidates with a synthesizer and choose the next step accordingly: explicit population evolution (REvolution, COEVO, EvolVE, POET, CktEvo, HORIZON, the e-graph search of ASPEN/ROVER), multi-candidate iterative hill climbing (Dr.RTL with N parallel candidates per iteration and promotion of the best SEC-passing one; ARES editing the running best; RTLRewriter and LongRTL with MCTS; AUTOGATE iterating over clock-gating candidate clusters; RTLScout's tool loop), and single-trajectory iterative refinement (CODMAS). Alpha-RTL performs test-time training per design, the "training version" of this loop; the ChipSeek series, EARL and Takeshita are RL-trained. This work changes that common step and is therefore skeleton-agnostic.

The gaps fall into three groups: Yosys-caliber methods measure the wrong quantity; diagnostic works (RTL-OPT, CktEvo §4.4, Dr.RTL Fig. 9, Metamorphosis) have only two to four tool points, no definition of "real gain", no noise floor, and no attribution to rewrite classes; commercial-in-the-loop methods (Dr.RTL, ARES, CktEvo's commercial arm, ASPEN, AUTOGATE) use DC as a scalar scorer — the search cannot tell whether a candidate without gain was absorbed by the synthesizer, is noise, or is harmful; every candidate pays full price, so only few candidates are evaluated (Dr.RTL: 20 designs × 50 candidates took a week of wall-clock; LongRTL's runtime is dominated by synthesis and equivalence checking; ARES exists precisely because cost is the bottleneck); and optimization targets a single configuration with no evaluator the search cannot see (HORIZON proposed a two-level protocol for functional harnesses but it was never implemented).

### 3.6 Why the scoring point is the full-effort rung

- **Definitional basis**: gains count only after the deployment flow. compile_ultra includes all compile options and runs the complete compilation process, requiring DC Ultra and DesignWare Foundation licenses; practitioner references uniformly recommend compile_ultra; advanced nodes add physical awareness on top (DC Ultra topographical technology, DC Graphical providing physical guidance to ICC). Nobody signs off with `compile`.
- **Upper bound vs production configuration**: in production, retiming is used selectively — it defeats conventional formal verification that relies on structural similarity, must be disabled around FSMs / asynchronous resets / gated logic, and breaks observability of internal registers; hierarchy is often deliberately preserved (`compile_ultra -no_autoungroup`). So E4 is the **upper bound of synthesizer capability** (answering "can the synthesizer do it"), while the production-representative configuration H5 answers "would your team benefit"; both are reported.
- **Empirical basis**: the drop from low to high rungs is large and systematic (3.1); the drop from the high rung to post-layout signoff is small and order-preserving (Dr.RTL post-PR: WNS 21% → 14%, area 6% → 4%; Fu et al. cross-library Spearman > 0.99). E4 is the lowest rung at which conclusions stabilize; Experiment 1 re-verifies the agreement between E4 and H4/H5.
- **Methodological basis**: the search exploits any gap between the scorer and the true objective; scoring at the capability upper bound minimizes the gap, and the hidden layer measures the residual gap.
- **Constraint basis**: E4 is the highest rung affordable at search scale, and deterministic/reproducible at a fixed version and core count; `-spg`, PrimeTime and place-and-route belong to the certification layer. The final verdict is post-layout signoff; this work spot-checks a small number of final designs through P&R.

## 4. Method

### 4.1 Overall structure

```
Original design D ──► Preconditions: Φ_main knee sweep; noise floor (D and perturbations synthesized once at E1–E4 and hidden configs)
                            │  Outputs: σ_D(k); D's PPA, cell histogram, compile log, critical path at every rung (control baselines)
                            ▼
Candidate C ◄── M4 search skeleton (parallel-candidate hill climbing + small archive; frozen LLM generates candidates by rewrite class)
   │
   ▼
M5 equivalence stack V1 lint → V2 simulation (+SAIF) → V3 VC Formal SEQ → V4 DPV     → non-proven never enters the population
   │ proven
   ▼
M6 rewrite classification (AST/dataflow diff + LLM review)
   │
   ▼
M2 cascade evaluation: E_s screening → predictor p(retained | class, g_s, history) ≥ τ → E4 scoring; random 10% of non-promoted audited
   │
   ▼
M3 diagnoser: g, fingerprint convergence, log/resource diffs, path mapping, σ_D → {absorbed@rung/capability, noise, harmful, trade-off, retained}
   │
   ├─► fitness (retained-gain vector, zero inside the noise band) → three-objective non-dominated sorting
   ├─► operator credit (only retained / trade-off improvement) → UCB
   └─► prompt feedback (label + evidence + map prior)

Accepted candidates ──► hidden layer H1–H5 (all of them; the search process has no read access) ──► speculation rate
Final designs       ──► open-source reproduction layer O; P&R spot checks
```

### 4.2 M1 evaluation service

- Configurations: E1–E4, hidden H1–H5, open-source ladder O0–O2 (supplementary), open-source reproduction layer O; definitions in §2.
- Three objectives: area; timing (WNS/TNS, supplemented by critical-path delay under knee constraints); power from DC `report_power` driven by a SAIF produced by VCS simulation. Designs with testbenches (RTLLM, RTL-OPT, part of Dr.RTL) use testbench + random stimulus; CktEvo modules without testbenches use constrained random stimulus only and are marked low-confidence for power on the map; the power at default toggle rates is also recorded on the same netlist as a control. H4 uses PrimeTime-PX on the same SAIF.
- One record per evaluation: {design, candidate hash, configuration, constraint, area, WNS, TNS, power, DC seconds, equivalence result, cell histogram, compile-log summary (datapath-extracted blocks, retimed registers, ICG count, ungrouped modules, shared resources), `report_resources` (DesignWare components and implementations), critical path mapped to RTL lines, layer}.
- Reproducibility: fixed DC version and core count, bit-identical; open-source scripts without randomization.

### 4.3 Noise floor σ_D

For each original design generate n = 16–32 semantics-preserving surface perturbations across four types: identifier renaming; reordering of independent statements / always blocks; equivalent expression rewrites (De Morgan, constant notation, bit-select notation); equivalent control-structure rewrites (if-else vs case, ternary vs if). Generated by Pyverilog rule scripts; each perturbation is first proven equivalent to D by SEQ. Synthesize D and all perturbations once each at E1–E4, H1, H2a, H2b and H5; H3 (`-spg`) on a reduced set (D plus one perturbation per type) for cost reasons; H4 reuses σ_D(E4) because PrimeTime re-times the same E4 netlists.

- σ_D(k, metric): the spread of the perturbation distribution; with small n use empirical quantiles or MAD-type robust estimates, and report sensitivity at 1σ/2σ/3σ. The decision threshold is uniformly 2σ_D (a conventional coverage level, not an arbitrary delta).
- Statistical framing: the null hypothesis is "the difference between C and D is, in the synthesizer's eyes, equivalent to a surface rewrite"; it is rejected only beyond the band. On designs with a wide band, small gains are not reportable — that is information, not a defect; small designs are also reported in absolute units.
- The unperturbed D is the center of the distribution and the reference for all controls (PPA(E4(D)) in retained gain, D's fingerprint in the convergence test, D's log in the log diff).
- Optional two-sided version: in the cascade, run 2–3 perturbations of candidate C at E_s to estimate C's own jitter.
- The distribution of σ_D is itself a result: propose the "minimum reportable gain" and report the fraction of literature gains that fall below the floor.

### 4.4 M5 equivalence stack and class-(c) policy

Four levels: V1 VCS compile and lint, port/width changes rejected outright; V2 simulation (testbench + random stimulus, the same simulation producing the SAIF); V3 VC Formal SEQ, no register correspondence required, proven / falsified / inconclusive, 30-minute timeout at sub-module level; V4 DPV as the second line for arithmetic datapath modules. Proven enters the population, falsified is discarded, inconclusive is recorded as "equivalence undecided", stays out of the population, and is reported per class. Formality is not part of the protocol (it verifies DC, not the LLM's rewrite); Jasper SEC and VC Formal SEQ are interchangeable; eqy is used only in the open-source reproduction layer.

Class (c) is split in two: (c1) latency-preserving sequential restructuring (retiming-style register redistribution, duplication), proven directly by SEQ, enters the population normally and counts in the headline; (c2) latency or interface-timing change: first measure each output's latency offset by simulation comparison and use it as the SEQ latency mapping before proving; even if proven, it enters the population only for designs whose interface is a handshake protocol and whose testbench is latency-agnostic, and its results are listed separately and never in the headline — for fixed-latency interfaces it is a specification change. The map gives both the proven subset and the undecided subset for (c2).

### 4.5 M6 rewrite classification

For each candidate compute an AST/dataflow diff (Pyverilog); rules classify first: (a) combinational rewrite; (b) latency-preserving coding/structural refactor; (c1) latency-preserving sequential restructuring; (c2) latency change; (d) algorithm/architecture replacement. Uncertain cases go to LLM review with a recorded confidence. Sub-tags: RTL-OPT's six patterns plus clock gating, and the "knowledge the synthesizer lacks" sub-classes (value range, mutual exclusivity, algebraic identity, cross-cycle invariant). Rules are calibrated by the manual verification in Experiment 1.

### 4.6 M3 diagnoser: the reason for a low score is read from the synthesis artifacts

**Five reasons and their evidence.** A proven candidate without retained gain can only be:

1. **Absorbed**: the transformation C expresses is one DC also applies to D, and the two land on the same (or nearly the same) netlist after some rung. Evidence: C's and D's fingerprints converge at that rung — area delta within that rung's σ_D, Jaccard similarity of cell histograms above threshold (calibrated in Experiment 1, expected around 0.95), identical critical-path endpoints; the compile-log diff shows that D's log contains the very transformation C wrote by hand.
2. **Noise**: fingerprints do not converge, all three components lie within the noise band.
3. **Harmful**: some component g < −2σ_D. Sub-class **blocks synthesis**: D's log/resource report shows datapath extraction or DesignWare components (e.g. the Booth implementation of DW02_mult) that C lacks; otherwise the loss is located with register counts, ICG counts and the critical-path-to-RTL mapping ("the 16 extra flip-flops are not on the critical path").
4. **Trade-off**: some component > 2σ_D and some < −2σ_D.
5. **Non-equivalent**: decided by M5, never enters the PPA diagnosis.

**Decision order.** V3 not proven → non-equivalent. Compute g and compare each component with 2σ_D(E4): some > 2σ and none < −2σ → retained; fingerprint converged at E4 → absorbed, then determine the rung; not converged and all within the band → noise; some < −2σ and none > 2σ → harmful (check for blocking synthesis); both positive and negative → trade-off.

**Three sources of rung and capability attribution (decreasing reliability, marked in the feedback).** (i) The E_s point the cascade already runs: converged with D at E_s → absorbed by the basic optimizations; not converged at E_s but converged at E4 → absorbed by a capability after E_s. (ii) Per-generation sampling (a few elites and random candidates) additionally runs E2, E3 and E2 + single flags to attribute to a specific capability. (iii) Unsampled candidates take the Experiment 1 map prior P(capability | class), marked "prior, not verified on this candidate". Whether online attribution is worth its cost is decided by ablation (§6.5).

**Feedback block.** Structured: rewrite class, diagnosis label, rung/capability, evidence (ΔA/ΔWNS/ΔP, histogram similarity, the relevant line of the log diff, missing DesignWare components or extra registers), map prior ("this class is absorbed at E2 with probability 0.9; retained cases concentrate in value-range-based bit-width reduction"). Feedback states evidence; suggestions come only from the prior table. Screened-out candidates also receive a cheap negative feedback ("already converged with the original at E_s").

**Reliability validation.** In Experiment 1, 30–50 candidates per class are manually verified (reading both netlists and logs) and the diagnoser's agreement with the human is reported; "absorbed" is additionally reproduced with single flags (apply only `-retime` or `-gate_clock` to D and confirm the fingerprint matches C). Stated limitations: fingerprint convergence is a proxy for "DC turned both into things of equal quality"; structurally different netlists with equal PPA are classified as noise (same conclusion for the search, an underestimate of the absorbed fraction for the map); log granularity depends on the DC version.

### 4.7 C2 ladder search

**One round.** Given the current design D, D's results at all rungs, σ_D, and the remaining budget B (DC hours). Per generation:

1. Generation: select a parent from the archive; a five-arm bandit (by M6 rewrite class) assigns N transformation prompts; the LLM generates N candidates in parallel; the equivalence stack filters to proven.
2. Classification: M6 gives class j.
3. Screening: each candidate is synthesized once at the screening rung E_s, giving g_s and whether the fingerprint converged.
4. Promotion: the predictor gives p = P(retained at E4 | j, g_s, this design's audited history); p ≥ τ goes to E4; a random 10% of the rest also goes to E4 (audit); the remainder are not synthesized further and are marked "judged absorbed/noise at the low rung".
5. Scoring: E4 candidates get their retained-gain vector and run through the diagnoser; only they have fitness and can enter the elite pool.
6. Feedback and credit: E4 candidates' diagnoses enter the prompt; retained / trade-off improvements credit the operator; screened-out candidates get cheap negative feedback and no credit.
7. Calibration: audited candidates' E4 results are compared with predictions to update this design's predictor and miss-rate estimate.
8. Archive update (three-objective Pareto front, ≤ 5; restart with a different parent after several stalled rounds), budget deduction, next generation; stop when exhausted.
9. Accepted candidates go to the hidden layer.

**Rung control 1: E_s chosen automatically per design.** All first-generation candidates run E1, E2 and E4 (no screening). With these data plus the noise-floor data for D, compute the predictive power (AUROC / precision-recall) of E1 and E2 (Y as an alternative) for E4 retention. Rule: choose the cheapest rung whose predictive power exceeds the threshold as E_s; if none qualifies → screening off for this design, full E4; if E4 is cheap for this design (below a given number of seconds) → full E4. Re-estimate every few generations from audit data; switching rungs is allowed.

**Rung control 2: τ adjusted automatically by budget.** Each generation's E4 quota follows from the remaining budget and remaining generations; τ is the quantile that fills the quota exactly, then corrected by the audited miss rate — a high miss rate lowers τ, a low one raises it and saves budget for later generations or more candidates.

**Predictor.** Trained on the Experiment 1 map (features: class, g_s, E_s fingerprint convergence, register-count change, AST diff size; target: E4 retention), with per-class retention rates as priors, then updated online per design. It is the entry point of C1 into C2.

**Difference from EvolVE.** EvolVE's fitness lives entirely at the low rung (Yosys) and DC only looks once at the end, so the search is misdirected; this work's fitness always lives at E4 and low rungs never score. Written up as a comparative experiment.

**What the framework must prove is a curve.** x-axis DC hours, y-axis retained gain (under E4 and hidden configurations): M's curve should lie above B0's (all low rung) and B2's (all E4) — B0 is high early but collapses under hidden configurations; B2 is real but slow.

**Degeneration when E4 is cheap.** If Experiment 0 shows that total full-E4 DC hours fit within licenses and wall-clock, screening is removed from the main method and C2 keeps only E4 scoring + comparative diagnosis + credit; in either case, the "full E4 every step, no screening" M is run as a control.

### 4.8 Hidden layer and certification (core component of C3)

H1–H5 (H6 when available) run on all visible-layer accepted candidates; results are written only to the hidden table; the database role of the search process and of the prompt generator has no read access to the hidden table (enforced in software). Speculation rate = fraction of visible-layer accepted candidates (proven and gain > 2σ_D(E4)) whose gain under some hidden configuration is ≤ 2σ_D(H) or negative, reported per configuration and as a combined "vetoed by any configuration" value, per generation. A random 10% of visible-layer rejected candidates also run the hidden layer to estimate the reverse error. The open-source reproduction layer O runs on final designs; a small number of final designs are spot-checked through place and route (OpenROAD or ICC2).

### 4.9 M4 search skeleton

- **Main skeleton: parallel-candidate hill climbing + small archive**, isomorphic to Dr.RTL's orchestrator D_t → {D_t^(i)}_{i=1..N} → D_{t+1} and ARES's running-best loop. Each round selects a parent from the archive (three-objective Pareto front, ≤ 5), generates N candidates in parallel from N transformation prompts organized by M6 rewrite class (the class is the operator; credit is a five-arm bandit), filters with the equivalence stack, evaluates with the cascade, attaches diagnosis feedback to the parent lineage, and restarts with a different parent after several stalled rounds; N = 5–8, K = 10–20, 50–160 candidates per design (the budget is measured in DC hours; the generation count is only an upper bound). Reasons: the two strongest commercial-in-the-loop RTL-to-RTL methods (Dr.RTL, ARES) both use this minimal loop, and ARES shows that carefully engineered skill libraries and long-term memory add little; population mechanisms serve the correctness bottleneck of spec-to-RTL, whereas correctness here is a binary equivalence gate. The minimal skeleton also keeps ablations interpretable and makes the Dr.RTL head-to-head "the same loop + this work's evaluation mechanisms vs the same loop + a scalar score".
- **Input side (identical across arms, not a contribution)**: the E4 report with the critical path mapped to RTL lines (borrowing CktEvo's CDFG annotation or Dr.RTL's path-to-RTL), because Dr.RTL's ablation shows that removing register-level slack feedback is the largest loss (WNS gain 21% → 9%).
- **Problem form: RTL-to-RTL.** The residual needs D as reference and the equivalence gate needs D as the golden model. Spec-to-RTL fits only when a reference implementation exists (use the reference RTL as D).
- **Skeleton-independence supplementary experiment**: M and B2 re-run once each on the COEVO and REvolution skeletons (30-start subset). Both are spec-to-RTL frameworks, adapted to RTL-to-RTL: the correctness dimension becomes the SEQ binary gate, COEVO's four-objective non-dominated sorting degenerates to three objectives (retained gain in area, timing, power), REvolution's Fail population is removed; Fix/Simplify correctness operators are down-weighted, Optimize, Restructure, Explore and Fusion are kept, and Explore becomes "propose an architectural alternative from the current RTL" (EvolVE's IGR idea). Their published spec-to-RTL numbers are not compared directly.
- **Dr.RTL head-to-head**: Dr.RTL's loop is isomorphic to the main skeleton, so it is re-implemented inside this framework as an arm (B2 + Dr.RTL's prompts and in-run skill learning) with the same LLM, stated as a re-implementation; one reference row keeps the original (Claude Code + Claude Opus) result, annotated as a different LLM.
- **LLM**: frozen, the same model in all arms. The main model is chosen by the calibration experiment of §5.2 among GPT-5.6 Luna / gpt-5.4-mini / GPT-5.6 Terra / GPT-5.4 (GPT-5.3-Codex as an alternative); the prior comes from Fu et al. (HQI: GPT-5.3-Codex 80.8 ≈ Claude 4.6 Opus 78.0, GPT-5.4 74.7, GPT-5-Mini 46.6, GPT-5-Nano 35.0 — mini/nano tiers are unsuitable for generation unless calibration proves otherwise). A second model re-runs the main arm on a 30-design subset. M6 review and log summaries use Luna or gpt-5.4-mini (Batch). Prompts are organized as "stable prefix (system prompt, RTL, D's E4 report, noise floor, map prior) + per-generation content" to hit the cache; the search loop uses Flex, offline generation uses Batch; reasoning effort medium; output limited to RTL plus a one-sentence transformation note.

## 5. Implementation

### 5.1 Engineering components

1. Evaluation service: DC / PT / VC Formal / VCS job queue (50-way), input (RTL, configuration, constraint), output M1 records (with log summary, resource report, path mapping); Yosys / ABC / OpenSTA / OpenROAD serving the reference caliber, the open-source ladder and the reproduction layer.
2. Results database: visible and hidden tables separated, information barrier = access control; aggregation by design / class / configuration into maps, retention curves and speculation rates.
3. Noise-floor estimator: surface-perturbation generation (Pyverilog) + SEQ proof + DC runs per rung/configuration, producing σ_D and D's control baselines.
4. Rewrite classifier: Pyverilog diff + rules + LLM review.
5. Diagnoser: fingerprint similarity, compile-log and resource-report diffs, path mapping, five-way rules, feedback-block generation.
6. Cascade controller: screening-rung selection, predictor training and online update, τ control, audit sampling, budget accounting.
7. Search skeleton: the implementation of parallel-candidate hill climbing + small archive (parent selection, class bandit, archive maintenance, restarts), prompt templates with feedback blocks and map prior; the COEVO / REvolution adapters serve only the skeleton-independence experiment.
8. Open-source reproduction-layer runner and P&R spot-check scripts.

### 5.2 Preconditions and decision points (no schedule)

Completed before any experiment; failure of any one changes the design:

- License: written confirmation of whether the Synopsys academic license allows publishing Yosys-vs-DC comparisons (confirmed allowed by Viterbi ITS on 2026-09-12). If restricted, the paper reports only differences between DC rungs, differences within the open-source ladder, and the reproduction-layer retention fraction, without cross-tool side-by-side tables.
- Noise-floor magnitude: if the median σ_D is so large that 2σ truncation swallows most candidates (e.g. > 5%), switch to rank truncation or a two-sided test with the candidate's own perturbations.
- SEQ inconclusive rate: pilot of 50 class-(c) candidates; if the (c2) inconclusive rate is too high, (c2) is measured only, not searched.
- E4 runtime distribution: decides whether screening enters the main method (end of §4.7).
- LLM calibration: the candidate models, the same prompts and skeleton (K = 6 × N = 5), 5 designs (RTLLM 1, RTL-OPT 2, Dr.RTL 2) × 2 seeds, 300 candidates per model, no screening, all through SEQ and E4. Recorded: V1 pass rate, V3 proven rate, M6 class distribution (whether (c1)/(d) appear), E4 retained fraction, best retained gain per design, response rate to "absorbed" diagnoses (fraction of children whose rewrite class changes), token/dollar cost per retained candidate, wall-clock per generation. Decision: the primary metric is retained candidates per dollar and per DC hour; the hard floor is a best retained gain per design of at least 70% of the strongest model's and a non-zero count of retained (c1)/(d) candidates. These data also serve as the first-generation data of "rung control 1" and the first measured run of the diagnoser. LLM cost negligible; DC about 45 hours.

### 5.3 Failure handling

- SEQ inconclusive → equivalence undecided, out of the population, reported per class; arithmetic datapath modules go to DPV.
- VCS compile/simulation failure → rejected at V1/V2, not counted as undecided.
- DC timeout or crash → evaluation failed, out of the population, counted per design and configuration, re-run once to exclude sporadic faults.
- Insufficient PT parallelism → H4 falls back to sampling (5 elites + 5 random per generation); H1–H3 and H5 remain exhaustive.
- Predictor without predictive power → screening off for that design (rung-control rule), reported as a map finding.

## 6. Experimental setup

### 6.1 Design sets

| Suite | Source | Size | Use |
|---|---|---|---|
| Dr.RTL 20 designs | open-sourced, human-written, 128–4615 lines (mean 812) | medium | main comparison set and head-to-head (0.1 ns sub-experiment) |
| RTL-OPT | 36 real engineer suboptimal / optimized pairs, 14 to 20K cells, DC netlists/scripts released | single module to thousands of lines | suboptimal versions as starting points; optimized versions as reference upper bound ("fraction of expert gain recovered"); calibration |
| CktEvo | about 30 modules extracted from 11 repositories | hundreds to thousands of lines, no standalone testbench | medium-size tier; low-confidence power |
| RTLLM v2.0 | 50 designs, N synthesizable under this DC flow (measured; ChipSeek-R1 reports 44 under Yosys) | small single modules | dev set uses about 20 of them; the rest held out |
| RTLRewriter short benchmark | 20 artificial-redundancy pairs + 12 public LLM samples | single module | calibration only, noted as overestimating the caliber gap |

The dev set uses only part of RTLLM to bring up the flow and prompt templates; everything else is held out and never used for tuning. Experiment 2 starts from about 40–50 designs (Dr.RTL 20 + RTL-OPT 12 + CktEvo modules 8 + some held-out RTLLM designs). CODMAS's RTLOPT (120 triples, 70 pipelining / 50 clock gating; not to be confused with Lu et al.'s RTL-OPT) and the LongRTL benchmark are not public; if obtainable from the authors, the former serves as calibration data for class (c1) and clock gating.

### 6.2 Experiment 0: preliminary measurements

License confirmation; Φ_main knee sweep for every starting point; noise floor (§4.3); SEQ pilot; E4 runtime distribution; monotonicity statistics of original designs across E1–E4 (a by-product).

### 6.3 Experiment 1: ladder and map (C1; offline, using candidates from existing methods)

- Objects: B0 (main skeleton + Y-caliber fitness) generates 30 proven candidates on each of 10 designs (300 in total; the literature caliber is used for generation so that this work's objective does not shape the candidate distribution); RTL-OPT 36 pairs, RTLRewriter 20 pairs and 12 LLM samples. Every object runs E1–E4, the attribution rungs E1d / E2r / E2g, H1, H2a, H2b, H3, H5, PT (H4); supplementary: O0–O2 and Ycoevo (COEVO's exact Yosys script and OpenSTA setting, to show that Yosys settings are not comparable among themselves either).
- Outputs: motivating figure (fraction of Y-caliber "better" candidates absorbed at each rung; a re-run of a ChipSeek-R1-style barrel shifter or a CODMAS-style hand-written clock-gating case through E1–E4); per-rung maps and per-class retention curves; single-flag attribution; non-monotone cases; σ_D distribution and minimum reportable gain; re-evaluated literature settings table (RTL-OPT and RTLRewriter at every rung); diagnoser agreement with manual verification; retention predictor and its accuracy on held-out designs (decides whether screening is viable); **static-rule misclassification rates**: with the static rule "no syntactic/coding optimizations, only architectural rewrites", report "forbidden by the rule but actually retained" and "allowed by the rule but actually absorbed" — the direct test of whether B1@E4 suffices.

### 6.4 Experiment 2: ladder-search comparison (C2, C3)

- Arms (same skeleton: parallel-candidate hill climbing + small archive; same LLM unless noted): B0 = Y-caliber fitness (EvolVE-style, DC only at the end); B1@E4 = E4 fitness + static complement prompt (strongest "intuitive" baseline); B2 = E4 fitness, scalar feedback, no screening (naive commercial-in-the-loop); M = ladder search fully enabled; M-noscreen = M without screening (full E4 every step); Dr.RTL-reimpl (its 20 designs, 0.1 ns, same LLM, VC Formal SEQ); reference row: the original Dr.RTL (Claude Code + Claude Opus, annotated as a different LLM). Skeleton independence: M and B2 re-run once each on the COEVO and REvolution skeletons (30-start subset).
- Budget: equal DC hours as the primary caliber (per-design budget = K E4-synthesis equivalents of the original design, K calibrated to Dr.RTL's 50-evaluation scale); equal LLM calls as an auxiliary caliber in a separate group. 3 seeds.
- Accepted candidates of all arms run E4 and the hidden layer so that all arms are compared under the same hidden configurations.
- Metrics: retained gain vs DC hours (under E4 and each hidden configuration, area/timing/power separately, geometric mean); ratio of main-configuration gain to hidden gain; speculation rate (per configuration and combined); retained candidates per DC hour; SEQ pass rate per class; drift of the operator distribution over generations and its correlation with hidden gain; fraction of expert gain recovered on RTL-OPT starting points; head-to-head on the Dr.RTL set (ratio of DC hours at equal gain).

### 6.5 Ablations (30-start subset, 3 seeds)

- No screening (full E4 every step); fixed screening rung and fixed τ (no automatic rung control); class-blind predictor (no connection to the map).
- No diagnosis feedback (scalar score only); no change to operator credit (UCB credited by E4 gain); no noise truncation; no online rung attribution (five-way labels only, no sampled ladder); no map prior injection.
- Fitness rung lowered from E4 to E2 / E1 (tests whether "full effort" is necessary).
- No power dimension; class (c1) excluded; skeleton replaced by REvolution.

### 6.6 Experiment 3: final map, open-source reproduction layer and P&R spot checks

Aggregate accepted candidates of all arms into the final three-axis map; run the open-source reproduction layer O on final designs and report the fraction of conclusions retained under an open-source flow; place and route a small number of final designs and report the shrinkage from E4 to post-layout signoff.

### 6.7 Budget (estimates, to be replaced by measurements)

Assumptions: one E4 run takes 30–90 s at RTLLM scale, 3–5 min at RTL-OPT scale, 5–15 min for CktEvo modules, 3–10 min for Dr.RTL designs; E1 is 1/3–1/5 of E4; PT 1 min; VCS 1 min; SEQ 2–5 min.

- Experiment 0: about 50 designs × (1 + 24 perturbations) × 8 configurations ≈ 10,000 syntheses ≈ 500 DC hours; SEQ about 40 hours.
- Experiment 1: about 420 objects × 11 runs ≈ 4,700 runs ≈ 250 DC hours.
- Experiment 2: about 45 starting points × 6 arms × 3 seeds × about 100 candidates per design (N and K set by calibration, range 50–160, estimate 100); E4 about 40,000 runs ≈ 3,300 hours, E1 about 30,000 runs ≈ 450 hours, hidden layer about 12,000 accepted candidates × 4–5 configurations ≈ 4,000 hours; total about 8,000 DC hours, about 7 days of wall-clock at 50 seats; SEQ about 70,000 runs ≈ 3,500 hours, about 3 days at 50 seats.
- Ablations: about 2,500 DC hours.
- Report DC runtime tiers, total DC hours, VC Formal hours, LLM call counts and normalized cost (ARES's per-call cost). GPU: 0.

## 7. Expected results and interpretation

### 7.1 Three map shapes and the corresponding paper forms

- **Concentrated**: retained gain concentrates in a few cells (value-range-based bit-width reduction, exclusivity-based sharing, algebraic-identity replacement, the part of (c1) where DC's retiming is limited, (d)), while syntactic rewrites, state re-encoding and hand-written gating are near zero. The map is actionable and C2 has a target — the present full design.
- **Near zero**: retained gains of all SEQ-provable classes lie within the floor; retention appears only in (c2) or SEQ-undecided candidates. The conclusion is that under strict sequential equivalence, LLM rewriting of RTL has no value beyond the full-effort synthesizer, and the value lies only where the specification allows relaxation. An important negative result plus a roadmap (equivalence definitions moving to the specification level), not a method paper.
- **Large and diffuse**: retention is substantial but without class structure, and a static prompt covers most of it (B1@E4 ≈ M). The measurement, floor and map remain contributions; the method part is dropped.

Expectation (from 3.1–3.4): most gains reported by existing methods are absorbed by compile_ultra-level capabilities or lie below the noise floor; the retained residual concentrates in rewrites that require information the synthesizer lacks and in architectural rewrites that need specification-level equivalence.

### 7.2 Success criteria

- C2: under hidden configurations at equal DC hours, M's geometric-mean gain exceeds B2's by more than 2σ_D on ≥ 60% of designs; M has an advantage of the same order over B1@E4 (otherwise the static prompt suffices); on Dr.RTL's 20 designs, M is not below Dr.RTL, or reaches the same level with ≤ 1/3 of the DC hours.
- Screening: the retention predictor's miss rate on held-out designs < 15%, and DC hours per retained candidate below full-E4 evaluation.
- C1: the map's class structure is significant (the cross-design retention predictor's accuracy on held-out designs is significantly above the class-blind baseline); high diagnoser–human agreement.

### 7.3 Interpretation table

| Outcome | Meaning | Paper form |
|---|---|---|
| Map concentrated, M > B2 and M > B1@E4 | the complement must be measured rather than declared; the relative signal carries extra information | DAC method paper (C1 + C2 + C3) |
| M ≈ B2, screening viable | the verdict carries no information beyond the score, but cost drops k-fold | "the right way to put DC in the loop": efficiency + certification + map |
| M ≈ B1@E4 | a static complement suffices | measurement and map paper, with "the complement can be written down; here is how" |
| Screening not viable (low rungs not predictive) | low-rung information is useless for the complement (itself a finding) | framework keeps diagnosis and certification, drops screening |
| Map near zero | no residual under strict equivalence | negative result + equivalence-definition roadmap, submit to ICCAD/DATE |

## 8. Risks and fallbacks

- License forbids cross-tool comparison: a precondition, not a risk item; the restricted write-up is in §5.2.
- σ_D too wide, swallowing the signal: switch to rank truncation or a two-sided test; a wide floor is itself reported as the "minimum reportable gain".
- (c2) inconclusive rate too high: measured only, not searched; the map gives the proven and undecided subsets.
- M ≈ B2: fall back to the efficiency paper per the interpretation table; M ≈ B1@E4: fall back to the measurement paper.
- Predictor without predictive power: screening off per design; reported as a finding.
- Power dimension unreliable on CktEvo modules: marked low-confidence; power conclusions rest on the suites with testbenches.
- DC becomes the optimized object: exhaustive hidden layer + information barrier + speculation rate.
- Version-specific conclusions: wording limited to this version and configuration; scripts released.
- Budget underestimated: Dr.RTL's week of wall-clock suggests the estimates may be optimistic; starting points and seeds can shrink, and the hidden layer can run H4/H5 first.

## 9. Submission positioning and release

- Target DAC 2027 (research manuscript deadline 2026-11-17, 6+1 pages). Narrative: the one-sentence question; the DC rung table and motivating figure; the map and minimum reportable gain; the quality–time curve of ladder search; speculation rate and open-source retention; head-to-head with Dr.RTL. Alternatives: ICCAD 2027 / DATE 2028.
- Reproducibility: pinned DC version and core count; in the paper, "the synthesizer can / cannot do X" is always written as "this version, this configuration can / cannot do X". Released with the paper: DC / PT / VC Formal / VCS scripts and SDCs, Nangate45 / ASAP7 / sky130hd configuration notes, all candidate RTL and the results database (including the hidden table), map data, retention predictor, diagnoser, open-source ladder and reproduction-layer scripts. Synopsys tools and their library data are not released.

## 10. Relation to this group's prior work COEVO

COEVO answers "how to search" in spec-to-RTL (correctness–PPA co-evolution, four-objective non-dominated sorting, annealed correctness gate, operator UCB); its evaluation caliber is Yosys + OpenSTA + Nangate45, i.e. this work's reference caliber Y. This work answers, for RTL-to-RTL, "what to search for, how to score it, how to spend less, how to prove it": the definition and map of retained gain, ladder search, hidden-configuration certification. COEVO plays two roles here: its Yosys-caliber results are one source of the "literature caliber" in §3; its skeleton, adapted to RTL-to-RTL, serves the skeleton-independence supplementary experiment. The main skeleton of this work is not COEVO.

---

## References

Roles: evidence = source of the problem; baseline = experimental control; borrowed = source of a method component; related = related work.

1. **CktEvo: Repository-Level RTL Code Benchmark for Design Evolution.** Zhengyuan Shi et al. arXiv 2603.08718, 2026. — evidence / baseline (Yosys 10.50% → DC-in-the-loop 1.77%; repository-level design set)
2. **A New Benchmark for the Appropriate Evaluation of RTL Code Optimization (RTL-OPT).** Yao Lu et al. arXiv 2601.01765, 2026. — evidence / calibration / starting points (36 pairs; 43 RTLRewriter pairs drop to 13 under compile_ultra; 35/36 retained as counter-evidence)
3. **Dr. RTL: Autonomous Agentic RTL Optimization through Tool-Grounded Self-Improvement.** Wenji Fang et al. arXiv 2604.14989 / ICCAD 2026. — evidence / baseline / head-to-head (DC 0.1 ns + SEC; skill-library category "already done by synthesis"; Table 3, Fig. 9, post-PR shrinkage; 20 open-sourced human-written designs)
4. **RTLScout: Joint Agentic Code and Synthesis Optimization for Efficient Digital Circuits.** Felix Arnold et al. arXiv 2606.06530, 2026. — evidence (Mockturtle gate-level control)
5. **Rethinking LLM-Based RTL Code Optimization Via Timing Logic Metamorphosis.** Zhihao Xu et al. arXiv 2507.16808, 2025. — evidence / borrowed (semantics-preserving-variant evaluation idea; Yosys caliber)
6. **Synthesis-in-the-Loop Evaluation of LLMs for RTL Generation.** Weimin Fu et al. GLSVLSI 2026. — related (best-of-5 vs single-shot HQI gap 3.7–22.1; cross-library Spearman > 0.99; Yosys caliber)
7. **SmaRTLy: RTL Optimization with Logic Inferencing and Structural Rebuilding.** arXiv 2510.17251, 2025. — related (rule-based method beats default Yosys by 8.95% AIG area; no LLM)
8. **COEVO: Co-Evolutionary Framework for Joint Functional Correctness and PPA Optimization in LLM-Based RTL Generation.** H. Ping et al. arXiv 2604.15001, 2026. — borrowed (skeleton) / baseline
9. **REvolution: An Evolutionary Framework for RTL Generation driven by Large Language Models.** Kyungjun Min et al. arXiv 2510.21407, 2025. — borrowed / ablation skeleton
10. **EvolVE: Evolutionary Search for LLM-based Verilog Generation and Optimization.** Wei-Po Hsin et al. arXiv 2601.18067, 2026. — baseline (low-rung search + DC final evaluation; architectural rewrite examples)
11. **RTLRewriter: Methodologies for Large Models aided RTL Code Optimization.** Xufeng Yao et al. arXiv 2409.11414, 2024. — calibration data (20 pairs + 12 LLM samples)
12. **SymRTLO: Enhancing RTL Code Optimization with LLMs and Neuron-Inspired Symbolic Reasoning.** Yiting Wang et al. arXiv 2504.10369, 2025. — related (DC 2019 medium effort, artificial benchmark; rung table)
13. **ROVER: RTL Optimization via Verified E-Graph Rewriting.** Samuel Coward et al. arXiv 2406.12421, 2024. — evidence (non-functional changes cause up to 15% area difference)
14. **ASPEN: LLM-Guided E-Graph Rewriting for RTL Datapath Optimization.** Niansong Zhang et al. MLCAD 2025. — borrowed (clock sweep to the knee; precedent of residual gains at a commercial high-effort caliber)
15. **Pluto: A Benchmark for Evaluating Efficiency of LLM-generated Hardware Code.** Manar Abdelatty et al. arXiv 2510.14756, 2025. — related (counter-evidence: consistent Genus / Yosys trends)
16. **ChipSeek-R1.** Zhirong Chen et al. arXiv 2507.04736, 2025. — related (six RTLLM v2.0 designs unsynthesizable; barrel-shifter suspected coding-style gain)
17. **ChipSeek: Optimizing Verilog Generation via EDA-Integrated Reinforcement Learning.** Zhirong Chen et al. ACL 2026. — related (DC sensitivity table)
18. **Pareto-Optimal RTL Code Generation via Multi-Objective RL with LLMs.** Koki Takeshita et al. COLM 2026. — related (union of 30 trials comparable to Base)
19. **EARL: Entropy-Aware RL Alignment of LLMs for Reliable RTL Code Generation.** Jiahe Shi et al. arXiv 2511.12033, 2025. — related (eqy as a cascaded signal; this work uses eqy only in the open-source layer)
20. **Agentic Hardware Design as Repository-Level Code Evolution (HORIZON).** Cunxi Yu et al. arXiv 2606.28279, 2026. — borrowed (two-level evaluation protocol proposal)
21. **ARES: Adaptive Reasoning-Effort Steering for PPA- and Cost-Aware RTL Optimization with LLM Agents.** Stef Cuyckens et al. arXiv 2607.27879, 2026. — related / borrowed (DC + PT + SEC in the loop; equal-cost accounting)
22. **Prompting for Power: Benchmarking LLMs for Low-Power RTL Design Generation.** Kevin Immanuel Gubbi et al. MLCAD 2025. — related (DC + PTPX power caliber, simulation-only verification; the "simplification outside coverage" concern is this work's, not the paper's)
23. **AUTOGATE: Automated Clock Gating via Toggling-Aware LLM-based RTL Rewriting.** Yiting Wang et al. arXiv 2606.17461, 2026. — related (RTL rewriting on top of a commercial flow with aggressive automatic clock gating)
24. **Alpha-RTL: Test-Time Training for RTL Hardware Optimization.** Peilong Zhou et al. arXiv 2606.05253, 2026. — related (test-time training; OpenSTA 0 ps floor)
25. **POET: Power-Oriented Evolutionary Tuning for LLM-Based RTL PPA Optimization.** arXiv 2603.19333, 2026. — related (Yosys-caliber evolution)
26. **LongRTL: Graph-Similarity-Guided LLM-driven Long-Context RTL Optimization.** Ye et al. arXiv 2606.08944, 2026. — related (DC + ASAP7 with rung and constraints unstated; combinational equivalence; rung table)
27. **CODMAS: A Dialectic Multi-Agent Collaborative Framework for Structured RTL Optimization.** Chang et al. EACL 2026 Industry, arXiv 2603.17204. — related (Yosys caliber; RTLOPT 120 triples of pipelining and clock gating; no formal equivalence; clock-gating gains as false-gain candidates)
28. Synopsys, *Design Compiler Optimization Reference Manual* (compile_ultra includes all compile options; requires DC Ultra and DesignWare Foundation licenses); *DC Ultra Datasheet*; *Design Compiler Graphical* (physical guidance). — industrial basis (§3.6)
29. Synopsys DesignWare Technical Bulletin, *Enhancing QoR with Datapath Analysis Techniques* (HDL messages of `analyze_datapath_extraction` and RTL coding guidelines). — industrial basis (RTL rewrites unlock synthesis capabilities)
30. Practitioner references (EcrioniX synthesis command reference; a Medium note on retiming and equivalence checking; a USPTO patent on equivalence checking of retimed circuits). — industrial basis (selective use of retiming; the `-no_autoungroup` convention)
