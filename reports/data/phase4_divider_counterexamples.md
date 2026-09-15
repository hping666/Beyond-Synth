# The four RTL-OPT divider counterexamples, inspected by hand (G5 decisions item 4 (c), 2026-09-15)

Objects: the RTL-OPT expert references `divider_4bit_ref`, `divider_8bit_ref`, `divider_16bit_ref`, `divider_32bit_ref` against their suboptimal originals (data/designs/rtlopt/divider_*/). All four are combinational (no clock); under the protocol of spec 03 they are not equivalent (reports/phase4.md §4a) and are therefore excluded from the literature re-evaluation counts.

## Records

| pair | verdict | evidence (results/raw/<design>/EQ/<record>) | first mismatch |
|---|---|---|---|
| divider_4bit | sim_fail (V2) | 5dbcf3d5f1c25ad8, v2_sim/trace.txt | cycle 24: `result` original e, reference f; `odd` 9 in both |
| divider_8bit | sim_fail (V2) | dbaf8c3bf8062fcc, v2_sim/trace.txt | cycle 32: `result` fe vs ff; `odd` 98 in both |
| divider_16bit | sim_fail (V2) | e554620fe483e5c3, v2_sim/trace.txt | cycle 260: `result` fffe vs ffff; `odd` cc7d in both |
| divider_32bit | falsified (SEQ, 3 071 s) | 50005d10c3152fa6, v3_seq/vcf.log | property `_map_output_result` falsified; `odd` proven; 20 000 random cycles found no mismatch (P(B = 0) = 2^-16 per cycle) |

## The two algorithms

The original is a non-restoring divider: `temp = {0, A}`; per bit it shifts left, subtracts `B` from the upper half when `temp[MSB] == 0` and adds it when `temp[MSB] == 1`, writes the quotient bit `~temp[MSB]`, and restores once at the end when the MSB is set. The reference is a restoring divider: `tmp_b = {B, 0}`; per bit it shifts left and, when `tmp_a >= tmp_b`, subtracts and sets the quotient bit. Both keep the remainder in the upper half (`odd`) and the quotient in the lower half (`result`).

For every non-zero divisor the two agree: the partial remainder before a subtraction is at most `2B - 1`, so with a remainder field of `n` bits and a divisor of `n/2` bits the field's MSB is set only when a subtraction went negative, exactly the case the non-restoring algorithm treats as "negative". With `B = 0` the subtraction never changes the field, the shifted-in dividend bits accumulate in it, and once the dividend's own MSB reaches the field's MSB the original reads it as a negative partial remainder: it adds 0, writes quotient bit 0 and, at the end, "restores" by adding 0. The reference sees `tmp_a >= 0` in every step and writes quotient bit 1 every time. Hence `result` differs (original `2^n - 2`, reference `2^n - 1`) while `odd` (= A after the shifts) agrees — exactly the pattern of the three simulation traces (result e / f with odd 9, fe / ff with odd 98, fffe / ffff with odd cc7d: the dividend's MSB is set and the divisor is zero).

## Confirmation by directed simulation (Icarus Verilog, scratch testbench of 2026-09-15)

```
divider_4:  B=0,MSB set: 64/64 differ; B=0,MSB clear: 0/64 differ; B!=0: 0/4000 differ; example A=8        B=0: original result=e        odd=8,        reference result=f        odd=8
divider_8:  B=0,MSB set: 64/64 differ; B=0,MSB clear: 0/64 differ; B!=0: 0/4000 differ; example A=80       B=0: original result=fe       odd=80,       reference result=ff       odd=80
divider_16: B=0,MSB set: 64/64 differ; B=0,MSB clear: 0/64 differ; B!=0: 0/4000 differ; example A=8000     B=0: original result=fffe     odd=8000,     reference result=ffff     odd=8000
divider_32: B=0,MSB set: 64/64 differ; B=0,MSB clear: 0/64 differ; B!=0: 0/4000 differ; example A=80000000 B=0: original result=fffffffe odd=80000000, reference result=ffffffff odd=80000000
```

Testbench: for each width, 64 random dividends with the MSB forced to 1 and `B = 0`, the same 64 with the MSB cleared, 4 000 random pairs with `B != 0`, and the directed pair `A = 2^(n-1), B = 0`; the outputs of the original and the reference are compared with `!==`.

## Conclusion

The four pairs differ **only** on division by zero with a dividend whose MSB is set — an input outside any divider's specification, where neither behaviour is "correct". Under RTL-OPT's own evaluation (simulation with a testbench, or combinational equivalence without a `B != 0` constraint) such a difference is either never exercised or ignored; under this project's protocol (random lock-step simulation and unconstrained SEQ) it is a functional difference and the pairs are reported apart. For the paper: the benchmark-hygiene table states the cause as "division by zero: quotient differs when the dividend's MSB is set (non-restoring vs restoring algorithm); equivalent for every non-zero divisor". Nothing is changed in the objects or the verdicts (rule 8); the pairs remain excluded from the re-evaluation counts and could be admitted only under an explicit `B != 0` assumption, which the protocol does not make.
