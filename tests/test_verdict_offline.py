"""Offline tests of the verdict rules and the mutant generator (V4 guardrails, DECISIONS 2026-09-12)."""
from pathlib import Path

from src.equiv.mutants import generate_mutants
from src.equiv.verdict import decide, v4_acceptance

ACCU = Path("/home/hping/RTLLM/Arithmetic/Accumulator/accu/verified_accu.v")


def test_guardrail_1_v3_falsified_is_final():
    assert decide("ok", "identical", "falsified", "proven", True) == ("falsified", None)
    assert decide("ok", "identical", "falsified") == ("falsified", None)


def test_v3_proven_is_by_seq_and_v4_never_needed():
    assert decide("ok", "identical", "proven") == ("proven", "seq")
    assert decide("ok", "identical", "proven", "falsified", True) == ("proven", "seq")


def test_v4_counts_only_after_inconclusive_v3():
    assert decide("ok", "identical", "inconclusive", "proven", True) == ("proven", "dpv")
    assert decide("ok", "identical", "inconclusive", "proven", False) == ("inconclusive", None)
    assert decide("ok", "identical", "inconclusive", "falsified", False) == ("falsified", None)
    assert decide("ok", "identical", "inconclusive", "inconclusive", False) == ("inconclusive", None)
    assert decide("ok", "identical", "inconclusive", "unavailable", False) == ("inconclusive", None)
    assert decide("ok", "identical", "inconclusive") == ("inconclusive", None)


def test_lower_levels_short_circuit():
    assert decide("rejected", None, None) == ("rejected", None)
    assert decide("ok", "sim_fail", None) == ("sim_fail", None)
    assert decide("ok", "offset", None) == ("proven_sim_only", None)
    assert decide("ok", "identical", "not_run") == ("not_run", None)
    assert decide("ok", "identical", "error") == ("error", None)


def test_guardrail_2_acceptance_conditions():
    good = {"lemmas": {"eq_a": "proven", "eq_b": "proven"}, "assume_count": 0}
    ok_vac = {"status": "ok", "mutant": "add_to_sub@10"}
    assert v4_acceptance(good, ["a", "b"], ok_vac) == (True, [])
    assert v4_acceptance({"lemmas": {"eq_a": "proven"}, "assume_count": 0}, ["a", "b"], ok_vac) == (False, ["all_outputs_covered"])
    assert v4_acceptance({"lemmas": {"eq_a": "proven", "eq_b": "inconclusive"}, "assume_count": 0}, ["a", "b"], ok_vac)[0] is False
    assert v4_acceptance(dict(good, assume_count=1), ["a", "b"], ok_vac) == (False, ["no_assumes"])
    assert v4_acceptance(good, ["a", "b"], {"status": "failed"}) == (False, ["vacuity_check_passed"])
    assert v4_acceptance(good, ["a", "b"], None) == (False, ["vacuity_check_passed"])
    assert v4_acceptance(good, [], ok_vac)[0] is False


def test_mutants_keep_the_interface_and_change_one_site():
    text = ACCU.read_text()
    muts = generate_mutants(text)
    assert len(muts) >= 3
    header = text[: text.index(");") + 2]
    for name, new in muts:
        assert new != text and new.startswith(header), name
        # exactly one contiguous difference
        i = next(k for k in range(min(len(text), len(new))) if text[k] != new[k])
        assert new[:i] == text[:i] and len(new) - len(text) in (-1, 0, 1, 2)
    names = [n.split("@")[0] for n, _ in muts]
    assert "eq_to_ne" in names and "add_to_sub" in names


def test_mutants_skip_comments_and_empty_bodies():
    text = "module m(input a, output b);\n// a == b + 1 in a comment\nassign b = a;\nendmodule\n"
    assert generate_mutants(text) == []
    text2 = "module m(input [1:0] a, output c);\nassign c = a == 2'd1;\nendmodule\n"
    muts = generate_mutants(text2)
    assert any("!=" in new for _, new in muts) and all("input [1:0] a, output c" in new for _, new in muts)


def test_offset_candidates_stay_proven_sim_only_unless_seq_ran_with_the_latency_mapping():
    """DECISIONS 2026-09-14 G2.1 (b): with the latency mapping SEQ's verdict decides for a V2 offset candidate; without it the
    weaker proven_sim_only class stands (both directions)."""
    assert decide("ok", "offset", "proven_sim_only") == ("proven_sim_only", None)
    assert decide("ok", "offset", "proven", latency_mapped=False) == ("proven_sim_only", None)
    assert decide("ok", "offset", "proven", latency_mapped=True) == ("proven", "seq")
    assert decide("ok", "offset", "falsified", latency_mapped=True) == ("falsified", None)
    assert decide("ok", "offset", "inconclusive", latency_mapped=True) == ("inconclusive", None)
    assert decide("ok", "sim_fail", "proven", latency_mapped=True) == ("sim_fail", None)   # a mismatch is never mapped away
