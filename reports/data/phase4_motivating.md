## 10. Motivating figure (PLAN 4.9): the same rewrite along the ladder

Two Phase 4 objects chosen by the data: the largest plain-compile (E1) gain that the full-effort flow recovers on its own, and the largest gain that survives E4 (retained). Positive = better than D under that configuration (relative); t_D is the rule-A threshold of the design at E4.

| object | design | class | E4 label / rung | E1 area / wns / power | E1d area / wns / power | E2 area / wns / power | E3 area / wns / power | E2g area / wns / power | E4 area / wns / power | Y area / wns / power | O0 area / wns / power | O1 area / wns / power | O2 area / wns / power | t_D(E4) area |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| recovered: c5873c2b59da776 | rtlrewriter_memory__memory_sharing | c1 | noise / - | +40.6 % / -0.6 % / +34.6 % | +40.6 % / -0.6 % / +47.4 % | +0.0 % / +0.0 % / +0.0 % | +0.0 % / +0.0 % / -0.0 % | -0.1 % / +0.0 % / +3.0 % | -0.1 % / +0.0 % / -0.9 % | +0.0 % / +1.4 % / +0.0 % | +0.0 % / +1.4 % / +0.0 % | +0.0 % / +1.4 % / +0.0 % | +0.1 % / +0.0 % / +0.0 % | 0.28 % |
| retained: c634baa4b8fa859 | rtlopt_ticket_machine | b | retained / E4 | +58.9 % / +24.4 % / +73.8 % | +58.9 % / +24.4 % / +51.3 % | +58.4 % / +30.9 % / +34.0 % | +58.4 % / +30.9 % / +34.0 % | +58.4 % / +30.9 % / +50.1 % | +58.4 % / +30.9 % / +34.0 % | +42.8 % / +6.0 % / +41.7 % | +42.8 % / +6.0 % / +41.7 % | +42.8 % / +6.0 % / +41.7 % | +41.2 % / +2.0 % / +43.2 % | 0.28 % |

The recovered object shows the gain a plain compile reports vanishing under `compile_ultra -retime -gate_clock` (the synthesizer obtains it on its own); the retained object keeps its gain there — the complement the ladder search aims at (PROPOSAL §1).
