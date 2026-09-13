Hand check of the five spot-check curves (operator, 2026-09-13):

- rtllm_JC_counter: area 343 µm² at every period, timing met down to 0.5 ns (+0.30 ns) → Φ = 0.5 ns (the tightest swept period; a 4-bit Johnson counter meets everything). Sensible.
- drrtl_DSP: met at 4.0–1.4 ns with area rising 3528 → 3818 (+8 %); at 1.0 ns WNS −0.23 ns → Φ = 1.4 ns. Sensible.
- rtlopt_add_sub: met at every period, but the area jumps from 93 to 132 µm² (+42 %) between 2.8 and 2.0 ns → the +10 % bound stops at Φ = 2.8 ns, i.e. just before the area explosion — the knee the rule is meant to find. Sensible.
- cktevo_ethmac__eth_cop: met down to 0.7 ns with +6.5 % area; at 0.5 ns area +14 % and WNS −0.11 ns → Φ = 0.7 ns. Sensible.
- rtlrewriter_algorithm__spmv: met at 2.8 ns with unchanged area; at 2.0 ns DC more than doubles the area (2403 µm²), and the curve is non-monotone below (1385 µm² at 0.7 ns): the bound relative to the loosest area keeps Φ = 2.8 ns. Sensible; the non-monotone tail is a DC restructuring effect worth remembering when reading area deltas at tight periods.

Fallback designs among the sets (no swept period met on any library): drrtl_LSTM (deep combinational cell), rtllm_div_16bit, rtlopt_divider_8bit / 16bit / 32bit (combinational dividers, 9–13 ns critical paths): Φ = the loosest period with `knee_fallback = true`; their baselines carry negative WNS by construction. Missing hidden-library periods: rtllm_freq_divbyfrac on ASAP7 (negative-edge flip-flop absent from the library subset) and rtlopt_divider_32bit on ASAP7 / sky130hd (every point exceeded the 17-minute DC limit) → no H2a / H2b certification for those two designs.
