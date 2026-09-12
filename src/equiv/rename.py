"""Module renaming so that the original design and a candidate can live in one simulation.

A candidate normally keeps the original module names (SEQ compares two libraries with the same top). The
lock-step harness instantiates both, so the candidate's module names get a suffix: every module declared in the
candidate's files is renamed by whole-word replacement across those files (declarations and instantiations).
"""
import re

MODULE_DECL = re.compile(r"^\s*(?:macro)?module\s+([A-Za-z_]\w*)", re.M)
SUFFIX = "__cand"


def module_names(text):
    return list(dict.fromkeys(MODULE_DECL.findall(text)))


def rename_modules(text, names, suffix=SUFFIX):
    for n in sorted(names, key=len, reverse=True):
        text = re.sub(rf"(?<![\w$`]){re.escape(n)}(?![\w$])", n + suffix, text)
    return text


def rename_candidate(files, suffix=SUFFIX):
    """-> (list of (original_path, renamed_text), all module names found)."""
    texts = [(f, open(f, errors="replace").read()) for f in files]
    names = []
    for _, t in texts:
        for n in module_names(t):
            if n not in names:
                names.append(n)
    return [(f, rename_modules(t, names, suffix)) for f, t in texts], names
