---
version: 1
purpose: static complement block of arm B1@E4 (spec 05 §2, PLAN Appendix A; G5 decisions item 2 (i), DECISIONS 2026-09-15). It replaces the map-prior table of arm M in the cacheable prefix. Fixed content for every design; no candidate-level evidence; written from the literature's own guidance and not from this project's map.
sources:
  - Dr. RTL (arXiv 2604.14989, ICCAD'26). §1, finding (3) "Invalid strategies: many naive transformations are either absorbed by synthesis or violate equivalence, such as manual rebalancing of optimized logic or moving control updates across registers"; finding (2) effective strategies "pre-computation, decomposition, and selective register insertion"; §6.1 "Dr. RTL also explicitly identifies avoiding strategies that are ineffective, absorbed by synthesis, or violate equivalence" (47 entries, 12 high / 16 medium / 6 low confidence, 13 avoid); Fig. 7, "Invalid Strategies (DO NOT USE)": "Already done by synthesis tool" (4.1 XOR tree balance / XOR chain flatten, 4.2 bit-level comparison replace), "Will degrade timing" (4.3 pre-registering wide concatenation), "Will break equivalence" (4.4 counter direction change); the released skill library data/sources/Dr_RTL/.claude/skill/rtl-opt/skill.md, entries 1-12 (high), 13-28 (medium), 29-34 (low), 35-47 (do not use).
  - RTL-OPT (arXiv 2601.01765). §2 "Synthesis tools can easily optimize these contrived patterns" (redundant computations, superfluous arithmetic such as adding 0 and multiplying by 1); §2.1 "More advanced modes (e.g., compile_ultra in DC) tend to aggressively restructure logic, which can obscure fine-grained RTL differences"; §3.2 the six optimization pattern types (bit-width optimization, precomputation and LUT conversion, operator strength reduction, control simplification, resource sharing, state encoding optimization) with their definitions; §4 the three LLM failure modes (control logic inconsistencies, overly aggressive pipelining violating latency requirements, improper resource sharing with stale data due to register reuse).
---
Static guidance from the RTL-optimization literature (the same text for every design; use it to decide what is worth rewriting):

A. The synthesizer already does these; a rewrite of this kind is absorbed and counts for nothing:
- Re-balancing or flattening XOR / AND / OR trees and reduction chains, and re-associating logic that the tool has already optimized ("manual rebalancing of optimized logic" is absorbed).
- Replacing a comparison against a constant by bit-level tests, a wide equality by a bit select, or a power-of-two compare by an MSB check: the tool's Boolean optimization does this itself.
- Restructuring mux trees by hand where the tool already optimizes muxes well; splitting one expression into named intermediate wires, or inlining them, without a structural change (wire decomposition "solely for hoped timing gain" gives negligible improvement).
- Removing contrived redundancies: adding zero, multiplying by one, duplicated identical arithmetic, dead branches, constants that propagate; full-effort synthesis removes them itself and aggressively restructures logic, so fine-grained differences of this kind disappear in the netlist.
- Renaming signals, re-ordering statements, or restating the same expression in another syntax.

B. Directions the literature found to survive commercial synthesis (the six optimization patterns of RTL-OPT and the high- and medium-confidence skills of Dr. RTL):
- Bit-width optimization: reduce register and wire widths where full precision is not necessary (establish the value range first).
- Precomputation and LUT conversion: replace run-time arithmetic over a small selection space by precomputed values or a case-based lookup, eliminating the arithmetic unit.
- Operator strength reduction: substitute a high-cost operator by a simpler equivalent through bit manipulation — shift-add decomposition of a constant multiplication, borrow-lookahead instead of a serial decrement, a carry-select split of a wide adder that dominates the path.
- Control simplification: flatten nested state machines, remove unnecessary states, streamline the control logic; pre-compute repeated conditions (state == X, cmd == Y) into shared wires; one-hot pre-decode of FSM state or opcode fields that fan out widely; group states by shared output behaviour before the final decode.
- Resource sharing: consolidate duplicate logic across cycles or branches when exclusivity is guaranteed; extract common sub-expressions and hoist arithmetic shared by sibling instances; move the mux before the adder, (sel ? A : C) + (sel ? B : D) instead of sel ? (A + B) : (C + D); compute both arithmetic branches and select late.
- State encoding optimization: choose the encoding (one-hot, Gray, binary) that fits the state count and the decode logic, and derive outputs from state groups.
- Fan-out management: duplicate a high-fan-out register or decoded condition per consumer cone, at the same latency.

C. Do not do these; they break equivalence or the interface protocol (the avoid list of Dr. RTL and the LLM failure modes observed by RTL-OPT):
- Do not change the latency of any output: no pipeline stage added or removed, no registering of a selector or of a control signal that must act in the same cycle, no pre-registered cross-module control; the cycle-by-cycle behaviour at every port must stay identical.
- Do not reverse a counter's direction to cheapen its terminal detection; do not change an LFSR polynomial or feedback structure.
- Do not flatten a priority if-else chain into parallel AND-OR logic unless the conditions are provably mutually exclusive.
- Do not narrow operand or interface widths, re-group or fuse arithmetic ((a - b) * c into a * c - b * c, (a - b) + c into a + (c - b)) or re-order signed / saturating comparisons unless overflow, sign and truncation behaviour are proven unchanged.
- Do not reuse a register for a second purpose when stale data can leak, and do not rewrite memory addressing or decode casually.
- Prefer pre-computation over restructuring and local simplification over architectural rewrites; treat aggressive transformations as one experiment at a time.
