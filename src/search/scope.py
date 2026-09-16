"""Scope-limited rewriting (G5 decisions item 1, correctness aid (i); DECISIONS 2026-09-15).

The prompt names the region the model may rewrite — the module on the critical path (multi-module designs) or the
always block(s) holding the critical endpoint registers (single-module designs) — the answer must return the full
file, and every other region is verified textually before any tool runs. "Regions" are the statement-level items of a
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


def parse_design(text):
    """{module: {"first_line", "items": [...], "instances": {...}}} over the comment-stripped design text; item texts are
    normalised (whitespace collapsed) for comparison and carry their first line."""
    out = {}
    for name, first, last, body in V.module_spans(text):
        items, instances = _module_items(body)
        base_line = first
        for it in items:
            it["text"] = normalise(body[it["start"]:it["end"]])
            it["line"] = base_line + body.count("\n", 0, it["start"])
        out[name] = {"first_line": first, "last_line": last, "items": items, "instances": instances}
    return out


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
    """Module-level regions (multi-module designs): an answer may return only the rewritten module(s); every module of D that
    the answer does not contain is taken verbatim from D's text (operator decision 2026-09-15 after the probe: both models
    returned the region module alone in 41 of 41 answers and 55 answers lacked the top module). -> (full_text, spliced
    module names). Block-level regions and answers that contain every module are returned unchanged."""
    if region is None or region.get("kind") != "module":
        return c_text, []
    d_mods = V.module_spans(d_text)
    c_names = set(V.module_names(c_text))
    missing = [m for m in d_mods if m[0] not in c_names]
    if not missing or region["module"] in [m[0] for m in missing]:
        return c_text, []            # nothing to add, or the region itself is absent (the answer is not a rewrite of the region)
    d_raw = d_text
    pieces = [c_text.rstrip() + "\n"]
    for name, first, last, body in missing:
        lines = d_raw.splitlines()
        pieces.append("\n" + "\n".join(lines[first - 1:last]) + "\n")   # the original module text, comments included (line numbers from the comment-stripped scan match the raw text)
    return "".join(pieces), [m[0] for m in missing]


def verify(d_text, c_text, region):
    """Violations of the region: every item of D outside the region must appear unchanged in the candidate's module of the
    same name, in the same order. -> [{"module", "kind", "line", "snippet", "problem"}] (empty when the scope holds)."""
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
                j = c_items.index(it["text"], pos)
                pos = j + 1
            except ValueError:
                changed = it["text"] in c_items   # present but out of order
                out.append({"module": name, "kind": it["kind"], "line": it["line"], "snippet": it["text"][:100],
                            "problem": "moved" if changed else "changed or removed", "targets": it.get("targets")})
    return out


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
