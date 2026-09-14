"""Classifier-based prescreen (DECISIONS 2026-09-14 C2.3; config `prescreen`): a candidate whose produced class has a
map-prior absorption probability >= p_min is not evaluated with probability 1 - audit_frac and receives the prior's
feedback at once; audited candidates continue through the pipeline. Without a prior table nothing is prescreened."""


def decide(prior_absorb, produced_class, p_min, audit_frac, rng):
    """-> 'evaluate' | 'prescreened' | 'audit'. prior_absorb: {class: absorption probability} (None / empty = no prior)."""
    p = (prior_absorb or {}).get(produced_class)
    if p is None or float(p) < float(p_min):
        return "evaluate"
    return "audit" if rng.random() < float(audit_frac) else "prescreened"
