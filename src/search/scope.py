"""Scope-limited rewriting (G5 decisions item 1, correctness aid (i); DECISIONS 2026-09-15).

The prompt names the region the model may rewrite — the module on the critical path (multi-module designs) or the
always block(s) holding the critical endpoint registers (single-module designs) — the answer must return the full
file, and every other region is verified textually before any tool runs; since the evening decision of 2026-09-15 (item 2)
an out-of-scope edit is restored from D (`splice`) and recorded as a warning flag instead of discarding the answer. "Regions" are the statement-level items of a
module: always / initial blocks, continuous assigns, instantiations, functions, tasks, generate and specify blocks;
declarations (ports, regs, wires, parameters, integers, genvars) are free, so a rewrite may add the wires or registers
it needs. The scanner is a small statement parser over comment-stripped Verilog-2001 text (Yosys stays the parser
of record for V1; this one only finds item boundaries and assignment targets)."""
import json
import re

from src.designs import verilog as V

_TOK = re.compile(r"""(?P<ws>\s+)
    |(?P<str>"(?:[^"\\]|\\.)*")
    |(?P<num>\d*\s*'\s*[sS]?[bBoOdDhH]\s*[0-9a-fA-FxXzZ_?]+|\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?)
    |(?P<id>\\[^\s]+|[A-Za-z_$][A-Za-z_0-9$]*)
    |(?P<op>===|!==|<<<|>>>|<=|>=|==|!=|&&|\|\||<<|>>|->|\*\*|\+:|-:|[()\[\]{};,:.#@=<>!~&|^+\-*/%?])""", re.X)
_DECL = {"input", "output", "inout", "reg", "wire", "tri", "tri0", "tri1", "wand", "wor", "supply0", "supply1", "integer", "real",
         "realtime", "time", "parameter", "localparam", "genvar", "event", "defparam", "signed", "unsigned"}
_ALWAYS = {"always", "always_ff", "always_comb", "always_latch", "initial"}
_STMT_KW = {"if", "case", "casex", "casez", "for", "while", "repeat", "forever", "wait", "begin", "fork", "disable"}


def tokenize(text):
    """[(kind, value, start, end)] of comment-stripped text; whitespace dropped."""
    out, pos = [], 0
    n = len(text)
    while pos < n:
        m = _TOK.match(text, pos)
        if not m:
            pos += 1   # a character outside the grammar (backtick directive, stray symbol): skipped, never a boundary
            continue
        kind = m.lastgroup
        if kind != "ws":
            out.append((kind, m.group(0), m.start(), m.end()))
        pos = m.end()
    return out


class _P:
    def __init__(self, toks):
        self.t = toks
        self.i = 0

    def peek(self, k=0):
        j = self.i + k
        return self.t[j][1] if j < len(self.t) else None

    def take(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def at_end(self):
        return self.i >= len(self.t)

    def skip_balanced(self, open_, close):
        """The current token is `open_`; advance past its matching `close`."""
        depth = 0
        while not self.at_end():
            v = self.take()[1]
            if v == open_:
                depth += 1
            elif v == close:
                depth -= 1
                if depth == 0:
                    return
        raise ValueError(f"unbalanced {open_}{close}")

    def until_semicolon(self):
        """Advance to just past the next `;` outside parentheses / brackets / braces; returns the index of the `;`."""
        depth = 0
        while not self.at_end():
            k, v, s, e = self.take()
            if v in "([{":
                depth += 1
            elif v in ")]}":
                depth -= 1
            elif v == ";" and depth <= 0:
                return self.i - 1
        return self.i - 1

    def statement(self, targets):
        """Parse one statement starting at self.i; assignment targets of simple statements are added to `targets`."""
        v = self.peek()
        if v is None:
            return
        if v == ";":
            self.take()
            return
        if v == "begin":
            self.take()
            if self.peek() == ":":
                self.take(); self.take()
            while not self.at_end() and self.peek() != "end":
                self.statement(targets)
            if not self.at_end():
                self.take()   # end
            if self.peek() == ":" and self.peek(1) is not None and self.t[self.i + 1][0] == "id":
                self.take(); self.take()
            return
        if v == "fork":
            self.take()
            while not self.at_end() and self.peek() != "join":
                self.statement(targets)
            if not self.at_end():
                self.take()
            return
        if v in ("if",):
            self.take()
            self.skip_balanced("(", ")")
            self.statement(targets)
            if self.peek() == "else":
                self.take()
                self.statement(targets)
            return
        if v in ("case", "casex", "casez"):
            self.take()
            self.skip_balanced("(", ")")
            while not self.at_end() and self.peek() != "endcase":
                # item label: `default [:]` or an expression list up to the `:` that is not a ternary's
                if self.peek() == "default":
                    self.take()
                    if self.peek() == ":":
                        self.take()
                else:
                    depth, tern = 0, 0
                    while not self.at_end():
                        k, val, s, e = self.take()
                        if val in "([{":
                            depth += 1
                        elif val in ")]}":
                            depth -= 1
                        elif val == "?" and depth == 0:
                            tern += 1
                        elif val == ":" and depth == 0:
                            if tern:
                                tern -= 1
                            else:
                                break
                self.statement(targets)
            if not self.at_end():
                self.take()   # endcase
            return
        if v in ("for", "while", "repeat", "wait"):
            self.take()
            self.skip_balanced("(", ")")
            self.statement(targets)
            return
        if v == "forever":
            self.take()
            self.statement(targets)
            return
        if v == "@":
            self.take()
            if self.peek() == "(":
                self.skip_balanced("(", ")")
            elif self.peek() == "*":
                self.take()
            else:
                self.take()   # @ident
            self.statement(targets)
            return
        if v == "#":
            self.take()
            if self.peek() == "(":
                self.skip_balanced("(", ")")
            else:
                self.take()
            self.statement(targets)
            return
        # simple statement: [target(s)] (<= | =) expression ; — or a task / system call / disable / event trigger
        start = self.i
        lhs, depth = [], 0
        while not self.at_end():
            k, val, s, e = self.t[self.i]
            if val in ("<=", "=", ";") and depth == 0:
                break
            if val in ("[", "("):
                depth += 1
            elif val in ("]", ")"):
                depth -= 1
            elif k == "id" and depth == 0 and self.t[self.i - 1][1] != ".":   # the assigned names: not indices, not hierarchical tails
                lhs.append(val)
            self.i += 1
        if not self.at_end() and self.peek() in ("<=", "="):
            for name in lhs:
                if name not in _STMT_KW and not name.startswith("$"):
                    targets.add(name)
        self.i = start
        self.until_semicolon()


def _module_items(body):
    """Statement-level items of one comment-free module body: [{kind, name, targets, start, end}] with offsets into the
    body, plus the instance table {inst: module}. Declarations are skipped (free)."""
    toks = tokenize(body)
    p = _P(toks)
    items, instances = [], {}
    # header: `module name [#(...)] [(ports)] ;`
    p.until_semicolon()
    while not p.at_end():
        k, v, s, e = p.t[p.i]
        if v == "endmodule":
            break
        if v in _ALWAYS:
            targets = set()
            p.take()
            if p.peek() == "@":
                p.take()
                if p.peek() == "(":
                    p.skip_balanced("(", ")")
                else:
                    p.take()
            p.statement(targets)
            items.append({"kind": "always" if v != "initial" else "initial", "targets": sorted(targets), "start": s, "end": p.t[p.i - 1][3]})
            continue
        if v == "assign":
            targets = set()
            p.take()
            j = p.i
            while j < len(p.t) and p.t[j][1] not in ("=", ";"):
                if p.t[j][0] == "id":
                    targets.add(p.t[j][1])
                j += 1
            p.until_semicolon()
            items.append({"kind": "assign", "targets": sorted(targets), "start": s, "end": p.t[p.i - 1][3]})
            continue
        if v in ("function", "task", "generate", "specify"):
            endkw = {"function": "endfunction", "task": "endtask", "generate": "endgenerate", "specify": "endspecify"}[v]
            p.take()
            name, depth, head = None, 0, True
            while not p.at_end() and p.peek() != endkw:
                tok = p.take()
                if head and v in ("function", "task"):
                    if tok[1] in ("[", "("):
                        depth += 1
                    elif tok[1] in ("]", ")"):
                        depth -= 1
                    if tok[1] in (";", "(") and depth <= (1 if tok[1] == "(" else 0):
                        head = False   # the header ends at `;` or at the ANSI port list; the name is the last plain identifier before it
                    elif tok[0] == "id" and depth == 0 and tok[1] not in _DECL and tok[1] != "automatic":
                        name = tok[1]
            if not p.at_end():
                p.take()
            items.append({"kind": v, "targets": [name] if name else [], "start": s, "end": p.t[p.i - 1][3]})
            continue
        if v in _DECL or v == "`":
            p.until_semicolon()
            continue
        if k == "id" and v not in V.KEYWORDS:
            # instantiation: `mod [#(...)] inst [range] (`
            j = p.i + 1
            if j < len(p.t) and p.t[j][1] == "#":
                depth = 0
                while j < len(p.t):
                    if p.t[j][1] == "(":
                        depth += 1
                    elif p.t[j][1] == ")":
                        depth -= 1
                        if depth == 0:
                            j += 1
                            break
                    j += 1
            if j < len(p.t) and p.t[j][0] == "id":
                inst = p.t[j][1]
                j2 = j + 1
                if j2 < len(p.t) and p.t[j2][1] == "[":
                    while j2 < len(p.t) and p.t[j2][1] != "]":
                        j2 += 1
                    j2 += 1
                if j2 < len(p.t) and p.t[j2][1] == "(":
                    p.until_semicolon()
                    instances[inst] = v
                    items.append({"kind": "inst", "targets": [inst], "module": v, "start": s, "end": p.t[p.i - 1][3]})
                    continue
        # anything else (defparam, a stray statement): one item up to the semicolon
        p.until_semicolon()
        items.append({"kind": "other", "targets": [], "start": s, "end": p.t[p.i - 1][3]})
    return items, instances


def module_offsets(text):
    """[(name, start, end)]: raw-text offsets of every `module ... endmodule` (comments blanked in place, so the offsets
    address the raw text as well)."""
    b = V.blank_comments(text)
    out, pos = [], 0
    while True:
        m = V._MODULE.search(b, pos)
        if not m:
            break
        e = V._ENDMODULE.search(b, m.end())
        end = e.end() if e else len(b)
        out.append((m.group(1), m.start(), end))
        pos = end
    return out


def parse_design(text):
    """{module: {"first_line", "last_line", "start", "end", "items": [...], "instances": {...}}} over the design text with the
    comments blanked in place; item texts are canonical token sequences (whitespace and comments do not count, 2026-09-15
    evening decision 2) and carry their first line and their raw-text offsets (`abs_start`, `abs_end`)."""
    out = {}
    b = V.blank_comments(text)
    for name, start, end in module_offsets(text):
        body = b[start:end]
        items, instances = _module_items(body)
        first = b.count("\n", 0, start) + 1
        for it in items:
            it["text"] = canonical(body[it["start"]:it["end"]])
            it["line"] = first + body.count("\n", 0, it["start"])
            it["abs_start"], it["abs_end"] = start + it["start"], start + it["end"]
        out[name] = {"first_line": first, "last_line": b.count("\n", 0, end) + 1, "start": start, "end": end, "items": items, "instances": instances}
    return out


def canonical(s):
    """The comparison form of an item: its tokens joined by single spaces (comments were blanked before; whitespace, line
    breaks and `ENCRYPTION    : x` vs `ENCRYPTION: x` do not count; `begin`/`end` and every other token do)."""
    return " ".join(t[1] for t in tokenize(s))


def normalise(s):
    return re.sub(r"\s+", " ", s).strip()


def _register_of(endpoint):
    """`txcounters1/NibCnt_reg[13]` -> (["txcounters1"], "NibCnt"); DC's clock-gating latches and generated names give None."""
    parts = endpoint.split("/")
    leaf = parts[-1]
    if leaf in ("latch", "D", "Q") and len(parts) > 1:   # `.../clk_gate_x_reg/latch`: an ICG, not an RTL register
        return None, None
    leaf = re.sub(r"(\[[^\]]*\])+$", "", leaf)
    leaf = re.sub(r"_reg$", "", leaf)
    if not re.match(r"^[A-Za-z_][A-Za-z_0-9$]*$", leaf):
        return None, None
    return parts[:-1], leaf


def select_region(design, top, crit_path, *, endpoints=3, single_module="block", multi_module="module"):
    """The region of the next rewrite from the critical endpoints of the parent's (or D's) evaluation.
    -> {"module", "kind": "module" | "blocks", "items": [item indices], "registers", "endpoints", "reason"}."""
    cp = crit_path if isinstance(crit_path, dict) else (json.loads(crit_path) if crit_path else {})
    ends = []
    for e in (cp.get("endpoints") or [])[:max(int(endpoints), 1)]:
        if isinstance(e, (list, tuple)) and len(e) > 1:
            ends.append(str(e[1]))
    crit = (cp.get("critical") or {}).get("endpoint")
    if crit and str(crit) not in ends:
        ends.insert(0, str(crit))
    multi = len(design) > 1
    resolved = []   # (module, register)
    for ep in ends:
        path, reg = _register_of(ep)
        if reg is None:
            continue
        mod = top
        for inst in path:
            nxt = (design.get(mod) or {}).get("instances", {}).get(inst)
            if nxt is None or nxt not in design:
                mod = None
                break
            mod = nxt
        resolved.append((mod or top, reg, ep))
    if not resolved:
        return {"module": top, "kind": "module", "items": [], "registers": [], "endpoints": ends, "reason": "no critical endpoint maps to an RTL register (D's evaluation has no path data or the names are tool-generated)"}
    module = resolved[0][0]
    items = design.get(module, {}).get("items", [])
    known = {t for it in items for t in it.get("targets") or []}
    regs = sorted({r for m, r, _ in resolved if m == module and r in known})   # names the RTL assigns (tool-generated names such as R_2 are dropped)
    eps = [e for m, _, e in resolved if m == module]
    if multi and multi_module == "module":
        return {"module": module, "kind": "module", "items": [], "registers": regs, "endpoints": eps, "reason": "multi-module design: the module holding the critical endpoints"}
    idx = sorted({i for i, it in enumerate(items) if it["kind"] == "always" and any(r in it["targets"] for r in regs)})
    if not idx or single_module == "module":
        return {"module": module, "kind": "module", "items": [], "registers": regs, "endpoints": eps,
                "reason": "no always block assigns the critical registers (renamed by the tool)" if not idx else "configured: whole module"}
    return {"module": module, "kind": "blocks", "items": idx, "registers": regs, "endpoints": eps, "reason": "single-module design: the always blocks holding the critical endpoints"}


def region_text(design, region, top):
    """The prompt block that names the region (spec 05 §2 addition, G5 item 1)."""
    mod = region["module"]
    regs = ", ".join(region.get("registers") or []) or "tool-generated names, not RTL registers"
    if region["kind"] == "module":
        if mod == top and len(design) == 1:
            return (f"Scope of this rewrite: the whole module `{mod}` (critical endpoints: {regs}). Return the complete file; "
                    f"module names, ports and the interface stay as given.\n")
        return (f"Scope of this rewrite: rewrite only module `{mod}` (it holds the critical endpoint registers {regs}); every other module of the design stays "
                f"as it is. Return the rewritten module `{mod}` in full (you may return only this module: every module you do not return is taken unchanged from the original; "
                f"any other module you do return must be textually unchanged). The module's name and ports stay as given.\n")
    items = design[mod]["items"]
    blocks = [items[i] for i in region["items"]]
    desc = "; ".join(f"the always block at line {b['line']} assigning {', '.join(b['targets'][:6])}" for b in blocks)
    return (f"Scope of this rewrite: in module `{mod}` rewrite only {desc} (critical endpoints: {regs}). Return the complete file; every other "
            f"always block, assign statement, instantiation, function and task of the design must be returned textually unchanged "
            f"(declarations — wires, regs, localparams — may be added or changed).\n")


def splice(d_text, c_text, region):
    """The scope aid's restoration step (decision 2026-09-15 evening, item 2, amending `correctness_aids.scope`): the answer's
    text outside the region is replaced by D's text, the region keeps the model's rewrite, and the pipeline runs on the
    result; what was outside the region and differed is recorded as the warning flag `violations` (never a discard).
    Module-level regions (multi-module designs): every module of D that the answer omits is appended verbatim from D
    (operator decision 2026-09-15 after the probe) and every module outside the region that the answer changed is replaced
    by D's module text. Block-level regions (single-module designs): every statement-level item of D outside the region
    that the answer changed is replaced by D's item text in place, and every such item the answer dropped is appended
    before `endmodule` (concurrent items are order-independent); the answer's own additions (new declarations, new
    assigns or blocks) stay. -> (text, {"violations": [...pre-splice...], "restored_modules": [...], "added_modules": [...],
    "restored_items": [...], "added_items": [...]}); an answer without violations comes back unchanged with an empty dict."""
    info = {}
    if region is None:
        return c_text, info
    violations = verify(d_text, c_text, region, ordered=False)   # a re-ordering of concurrent items is neither an edit nor a flag
    if not violations:
        return c_text, info
    info["violations"] = violations
    if region.get("kind") == "module":
        return _splice_modules(d_text, c_text, region, violations, info)
    return _splice_items(d_text, c_text, region, violations, info)


def _splice_modules(d_text, c_text, region, violations, info):
    d_offs = module_offsets(d_text)
    changed = {v["module"] for v in violations if v["problem"] != "module missing from the answer" and v["module"] != region["module"]}
    missing = [v["module"] for v in violations if v["problem"] == "module missing from the answer"]
    c_offs = {name: (s, e) for name, s, e in module_offsets(c_text)}
    if region["module"] not in c_offs:
        info["region_missing"] = region["module"]   # not a rewrite of the region: the driver treats the answer as unusable
        return c_text, info
    text = c_text
    for name, ds, de in sorted(d_offs, key=lambda m: -c_offs.get(m[0], (0, 0))[0]):   # replace from the back so offsets stay valid
        if name in changed and name in c_offs:
            cs, ce = c_offs[name]
            text = text[:cs] + d_text[ds:de] + text[ce:]
    pieces = [text.rstrip() + "\n"]
    for name, ds, de in d_offs:
        if name in missing and name != region["module"]:
            pieces.append("\n" + d_text[ds:de] + "\n")
    info["restored_modules"] = sorted(changed)
    info["added_modules"] = [m for m in missing if m != region["module"]]
    return "".join(pieces), info


def _splice_items(d_text, c_text, region, violations, info):
    mod = region["module"]
    d, c = parse_design(d_text), parse_design(c_text)
    dm, cm = d.get(mod), c.get(mod)
    if dm is None or cm is None:
        info["region_missing"] = mod   # the module is absent from the answer: not a rewrite of the region
        return c_text, info
    free = set(region.get("items") or [])
    c_texts = [it["text"] for it in cm["items"]]
    matched = set()
    for i, it in enumerate(dm["items"]):
        if i in free:
            continue
        for j, ct in enumerate(c_texts):
            if j not in matched and ct == it["text"]:
                matched.add(j)
                break
    key = lambda it: (it["kind"], tuple(sorted(it.get("targets") or [])))
    edits = []      # (abs_start, abs_end, replacement) on the candidate text
    appended = []
    restored, added = [], []
    used = set(matched)
    for i, it in enumerate(dm["items"]):
        if i in free or it["text"] in c_texts:
            continue
        j = next((k for k, cit in enumerate(cm["items"]) if k not in used and key(cit) == key(it)), None)
        d_raw = d_text[it["abs_start"]:it["abs_end"]]
        if j is not None:
            used.add(j)
            edits.append((cm["items"][j]["abs_start"], cm["items"][j]["abs_end"], d_raw))
            restored.append({"kind": it["kind"], "line": it["line"], "targets": it.get("targets")})
        else:
            appended.append(d_raw)
            added.append({"kind": it["kind"], "line": it["line"], "targets": it.get("targets")})
    text = c_text
    for cs, ce, rep in sorted(edits, key=lambda e: -e[0]):
        text = text[:cs] + rep + text[ce:]
    if appended:
        b = V.blank_comments(text)
        ms = {name: (s, e) for name, s, e in module_offsets(text)}
        cs, ce = ms[mod]
        em = V._ENDMODULE.search(b, cs, ce)
        at = em.start() if em else ce
        text = text[:at] + "\n" + "\n".join(appended) + "\n" + text[at:]
    info["restored_items"] = restored
    info["added_items"] = added
    return text, info


def verify(d_text, c_text, region, ordered=True):
    """Violations of the region: every item of D outside the region must appear unchanged (token-identical) in the candidate's
    module of the same name, in the same order unless `ordered` is False (concurrent items are order-independent; the
    spliced text appends restored items). -> [{"module", "kind", "line", "snippet", "problem"}] (empty when the scope holds)."""
    d, c = parse_design(d_text), parse_design(c_text)
    out = []
    free_module = region["module"] if region["kind"] == "module" else None
    free_items = set(region.get("items") or []) if region["kind"] == "blocks" else set()
    for name, dm in d.items():
        if name == free_module:
            continue
        cm = c.get(name)
        if cm is None:
            out.append({"module": name, "kind": "module", "line": dm["first_line"], "snippet": "", "problem": "module missing from the answer"})
            continue
        c_items = [it["text"] for it in cm["items"]]
        pos = 0
        for i, it in enumerate(dm["items"]):
            if name == region["module"] and i in free_items:
                continue
            try:
                j = c_items.index(it["text"], pos if ordered else 0)
                pos = j + 1
            except ValueError:
                changed = it["text"] in c_items   # present but out of order
                out.append({"module": name, "kind": it["kind"], "line": it["line"], "snippet": it["text"][:100],
                            "problem": "moved" if changed else "changed or removed", "targets": it.get("targets")})
    return out


SCOPE_FLAG_SQL = "(label='scope_violation' OR COALESCE(json_array_length(json_extract(scope_json,'$.violations')),0) > 0)"   # a candidate carrying the warning flag (or the pre-amendment discard label)


def failure_evidence(rec):
    """(failure type, text for the repair prompt) from an equivalence record; None when the verdict is not repairable."""
    v = rec.get("verdict")
    if v == "rejected":
        return "rejected", f"it does not pass the interface and elaboration check: {str(rec.get('v1_detail') or 'unknown error')[:600]}"
    if v == "sim_fail":
        v2 = rec.get("v2") or {}
        mism = v2.get("mismatches")
        if not mism and rec.get("v2_detail"):
            try:
                mism = json.loads(rec["v2_detail"])
            except (ValueError, TypeError):
                mism = None
        if isinstance(mism, dict) and mism:
            first = v2.get("first_mismatch")
            parts = [f"output {o}: original {m.get('d')}, rewrite {m.get('c')} (first at cycle {m.get('first_cycle')})" for o, m in sorted(mism.items())[:6]]
            return "sim_fail", (f"the lock-step simulation against the original diverges" + (f" from cycle {first} after reset" if first is not None else "") + ": " + "; ".join(parts))
        return "sim_fail", f"the lock-step simulation against the original diverges: {str(rec.get('v2_detail') or v2.get('error') or 'unknown')[:400]}"
    if v == "falsified":
        v3 = rec.get("v3") or {}
        props = v3.get("properties") or {}
        bad = sorted(p.replace("_map_output_", "").replace("seq_assert_", "") for p, st in props.items() if st == "falsified")
        depths = v3.get("cex_depths") or {}
        d = [depths[p] for p in props if p in depths and props[p] == "falsified"]
        text = "sequential equivalence checking found a counterexample"
        if bad:
            text += f": outputs {', '.join(bad[:8])} differ from the original"
        if d:
            text += f" (shortest counterexample {min(d)} cycles after reset)"
        return "falsified", text
    return None, None
