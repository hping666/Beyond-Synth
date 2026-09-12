"""Final verdict of the equivalence stack (docs/spec/03-equivalence.md; DECISIONS 2026-09-12, V4 guardrails).
Pure functions so that the decision rules are unit-testable without any tool."""

V4_ACCEPT_REASONS = ("all_outputs_covered", "no_assumes", "vacuity_check_passed")


def v4_acceptance(v4, outputs, vacuity):
    """-> (accepted: bool, failed_conditions: list). v4 is the run_dpv record, vacuity the vacuity-check record."""
    failed = []
    lemmas = v4.get("lemmas") or {}
    if not outputs or set(lemmas) != {f"eq_{o}" for o in outputs} or any(s != "proven" for s in lemmas.values()):
        failed.append("all_outputs_covered")
    if int(v4.get("assume_count") or 0) != 0:
        failed.append("no_assumes")
    if not vacuity or vacuity.get("status") != "ok":
        failed.append("vacuity_check_passed")
    return (not failed), failed


def decide(v1_status, v2_status, v3_status, v4_status=None, v4_accepted=False):
    """-> (verdict, proven_by). Guardrail 1: a V3 falsified is final. V4 only counts after a V3 inconclusive."""
    if v1_status == "rejected":
        return "rejected", None
    if v2_status in ("sim_fail", "compile_failed", "run_failed", "timeout", "no_trace"):
        return "sim_fail", None
    if v2_status == "offset":
        return "proven_sim_only", None
    if v3_status == "proven":
        return "proven", "seq"
    if v3_status == "falsified":
        return "falsified", None
    if v3_status == "inconclusive":
        if v4_status == "falsified":
            return "falsified", None
        if v4_status == "proven" and v4_accepted:
            return "proven", "dpv"
        return "inconclusive", None
    if v3_status in ("not_run", None):
        return "not_run", None
    return "error", None
