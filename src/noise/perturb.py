"""Semantics-preserving surface perturbations on the Pyverilog AST (docs/spec/02-noise-floor.md §1).

  P1 rename    internal nets / registers / integers / parameters / genvars (never ports, module, instance,
               function or task names) get names from a fixed word list plus index; deterministic per (seed, k)
  P2 reorder   the concurrent module items (assign / always / instances) of each run between declarations are
               permuted, and inside always blocks made only of nonblocking assignments to distinct registers the
               assignments are permuted (both are semantics-preserving by construction)
  P3 expr      De Morgan on bitwise / logical not-of-and / not-of-or; decimal <-> hexadecimal constants;
               constant part-selects x[m:l] (width <= 8, right-hand side only) -> {x[m], ..., x[l]}
  P4 ctrl      x <= c ? a : b  ->  if (c) x <= a; else x <= b;   case with default and constant labels -> if chain;
               if (c) x = a; else x = b;  ->  x = c ? a : b
Every transform raises NotApplicable when the design offers no site; the caller records that. Whether a
perturbation is really equivalent is decided afterwards by the equivalence stack (spec 02 §2), never assumed.
"""
import copy
import re

import pyverilog.vparser.ast as A

from src.noise import vast as V

WORDS = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliet", "kilo", "lima",
         "mike", "november", "oscar", "papa", "quebec", "romeo", "sierra", "tango", "uniform", "victor", "whiskey",
         "xray", "yankee", "zulu"]
TYPES = ("P1_rename", "P2_reorder", "P3_expr", "P4_ctrl")


class NotApplicable(Exception):
    pass


# ----------------------------------------------------------------------------- generic tree editing
def child_slots(node):
    """[(attr, index_or_None, child)] for every AST child of `node`, so that a child can be replaced in place."""
    out = []
    for attr, value in vars(node).items():
        if attr.startswith("_"):
            continue
        if isinstance(value, A.Node):
            out.append((attr, None, value))
        elif isinstance(value, (list, tuple)):
            for i, v in enumerate(value):
                if isinstance(v, A.Node):
                    out.append((attr, i, v))
    return out


def replace_child(parent, attr, index, new):
    if index is None:
        setattr(parent, attr, new)
    else:
        seq = list(getattr(parent, attr))
        seq[index] = new
        setattr(parent, attr, tuple(seq) if isinstance(getattr(parent, attr), tuple) else seq)


def sites(root, predicate, skip_under=()):
    """[(parent, attr, index, node)] for every node satisfying predicate, not below a node of a type in skip_under."""
    found = []

    def rec(node, under_skip):
        for attr, idx, child in child_slots(node):
            skip = under_skip or isinstance(child, skip_under)
            if not skip and predicate(child):
                found.append((node, attr, idx, child))
            rec(child, skip)

    rec(root, False)
    return found


def _protected_names(ast):
    names = set()
    for n in V.walk(ast):
        if isinstance(n, (A.Function, A.Task, A.ModuleDef)):
            names.add(n.name)
        if isinstance(n, A.Instance):
            names.add(n.name)
        if isinstance(n, (A.Input, A.Output, A.Inout)):
            names.add(n.name)
    return names


# ----------------------------------------------------------------------------- P1
def p1_rename(ast, seed, k):
    ast = copy.deepcopy(ast)
    r = V.rng(seed, "P1", k)
    taken = V.all_identifiers(ast) | V.KEYWORDS
    protected = _protected_names(ast)
    details = {}
    for m in V.modules(ast):
        decl = {n: kind for n, kind in V.declared_names(m).items() if n not in protected}
        if not decl:
            continue
        words = WORDS[:]
        r.shuffle(words)
        mapping = {}
        for i, name in enumerate(sorted(decl)):
            new = f"{words[i % len(words)]}_{i}"
            while new in taken:
                new += "x"
            mapping[name] = new
            taken.add(new)
        for n in V.walk(m):
            if isinstance(n, A.Identifier) and n.name in mapping:
                n.name = mapping[n.name]
            elif isinstance(n, V.DECL_KINDS) and n.name in mapping:
                n.name = mapping[n.name]
        details[m.name] = mapping
    if not details:
        raise NotApplicable("no internal names to rename")
    return ast, {"renamed": details}


# ----------------------------------------------------------------------------- P2
PROCESS_ITEMS = (A.Assign, A.Always, A.InstanceList)


def _base_name(lv):
    node = lv.var if isinstance(lv, A.Lvalue) else lv
    while isinstance(node, (A.Pointer, A.Partselect)):
        node = node.var
    return node.name if isinstance(node, A.Identifier) else None


def _permute(seq, r):
    perm = list(seq)
    r.shuffle(perm)
    if perm == list(seq):
        perm = perm[1:] + perm[:1]
    return perm


def p2_reorder(ast, seed, k):
    ast = copy.deepcopy(ast)
    r = V.rng(seed, "P2", k)
    details = {}
    for m in V.modules(ast):
        items = list(m.items)
        runs, run = [], []
        for i, it in enumerate(items):
            if isinstance(it, PROCESS_ITEMS):
                run.append(i)
            else:
                if len(run) >= 2:
                    runs.append(run)
                run = []
        if len(run) >= 2:
            runs.append(run)
        changed = 0
        for run in runs:
            perm = _permute(run, r)
            new_items = list(items)
            for dst, src in zip(run, perm):
                new_items[dst] = items[src]
            items = new_items
            changed += 1
        if changed:
            m.items = tuple(items) if isinstance(m.items, tuple) else items
        blocks = 0
        for it in items:
            if isinstance(it, A.Always) and isinstance(it.statement, A.Block):
                stmts = list(it.statement.statements)
                if len(stmts) >= 2 and all(isinstance(s, A.NonblockingSubstitution) for s in stmts):
                    lhs = [_base_name(s.left) for s in stmts]
                    if all(lhs) and len(set(lhs)) == len(lhs):
                        it.statement.statements = tuple(_permute(stmts, r))
                        blocks += 1
        if changed or blocks:
            details[m.name] = {"item_runs": changed, "always_blocks": blocks}
    if not details:
        raise NotApplicable("nothing to reorder")
    return ast, {"reordered": details}


# ----------------------------------------------------------------------------- P3
_CONST = re.compile(r"^(\d*)'([sS]?)([dDhH])([0-9a-fA-F_]+)$")


def _const_swap(value):
    m = _CONST.match(value)
    if not m:
        return None
    size, signed, base, digits = m.groups()
    digits = digits.replace("_", "")
    try:
        n = int(digits, 10 if base in "dD" else 16)
    except ValueError:
        return None
    return f"{size}'{signed}{'h' + format(n, 'x') if base in 'dD' else 'd' + str(n)}"


def _int_value(node):
    if isinstance(node, A.IntConst):
        m = _CONST.match(node.value)
        if m:
            return int(m.group(4).replace("_", ""), 10 if m.group(3) in "dD" else 16)
        if node.value.isdigit():
            return int(node.value)
    return None


def _demorgan(node):
    inner = node.right
    if isinstance(node, A.Unot) and isinstance(inner, (A.And, A.Or)):
        cls = A.Or if isinstance(inner, A.And) else A.And
        return cls(A.Unot(inner.left), A.Unot(inner.right))
    if isinstance(node, A.Ulnot) and isinstance(inner, (A.Land, A.Lor)):
        cls = A.Lor if isinstance(inner, A.Land) else A.Land
        return cls(A.Ulnot(inner.left), A.Ulnot(inner.right))
    return None


def _partselect_to_concat(node):
    if not (isinstance(node, A.Partselect) and isinstance(node.var, A.Identifier)):
        return None
    msb, lsb = _int_value(node.msb), _int_value(node.lsb)
    if msb is None or lsb is None or msb < lsb or msb - lsb + 1 > 8:
        return None
    return A.Concat([A.Pointer(A.Identifier(node.var.name), A.IntConst(str(i))) for i in range(msb, lsb - 1, -1)])


def p3_expr(ast, seed, k, max_sites=4):
    ast = copy.deepcopy(ast)
    r = V.rng(seed, "P3", k)
    cands = []
    for parent, attr, idx, node in sites(ast, lambda n: isinstance(n, (A.IntConst, A.Unot, A.Ulnot, A.Partselect)), skip_under=(A.Lvalue, A.Width, A.Length, A.Dimensions, A.Parameter, A.Localparam)):
        if isinstance(node, A.IntConst) and _const_swap(node.value):
            cands.append(("const", parent, attr, idx, node))
        elif isinstance(node, (A.Unot, A.Ulnot)) and _demorgan(node) is not None:
            cands.append(("demorgan", parent, attr, idx, node))
        elif isinstance(node, A.Partselect) and _partselect_to_concat(node) is not None:
            cands.append(("partselect", parent, attr, idx, node))
    if not cands:
        raise NotApplicable("no expression site")
    n = min(len(cands), 1 + r.randrange(0, max_sites))
    chosen = r.sample(cands, n)
    applied = []
    for kind, parent, attr, idx, node in chosen:
        if kind == "const":
            new = A.IntConst(_const_swap(node.value))
        elif kind == "demorgan":
            new = _demorgan(node)
        else:
            new = _partselect_to_concat(node)
        replace_child(parent, attr, idx, new)
        applied.append(kind)
    return ast, {"expr_sites": applied}


# ----------------------------------------------------------------------------- P4
def _is_const_label(node):
    return isinstance(node, A.IntConst) or (isinstance(node, A.Identifier) and node.scope is None)


def _case_to_if(case):
    if type(case) is not A.CaseStatement:
        return None
    default = [c for c in case.caselist if c.cond is None]
    labelled = [c for c in case.caselist if c.cond is not None]
    if len(default) != 1 or not labelled:
        return None
    for c in labelled:
        if not all(_is_const_label(x) for x in c.cond):
            return None
    comp = case.comp
    chain = default[0].statement
    for c in reversed(labelled):
        cond = None
        for lab in c.cond:
            eq = A.Eq(copy.deepcopy(comp), copy.deepcopy(lab))
            cond = eq if cond is None else A.Lor(cond, eq)
        chain = A.IfStatement(cond, c.statement, chain)
    return chain


def _ternary_to_if(stmt):
    if not isinstance(stmt, (A.BlockingSubstitution, A.NonblockingSubstitution)):
        return None
    rhs = stmt.right.var if isinstance(stmt.right, A.Rvalue) else stmt.right
    if not isinstance(rhs, A.Cond):
        return None
    cls = type(stmt)
    t = cls(copy.deepcopy(stmt.left), A.Rvalue(rhs.true_value))
    f = cls(copy.deepcopy(stmt.left), A.Rvalue(rhs.false_value))
    return A.IfStatement(rhs.cond, t, f)


def _single_subst(node):
    if isinstance(node, A.Block) and len(node.statements) == 1:
        node = node.statements[0]
    return node if isinstance(node, (A.BlockingSubstitution, A.NonblockingSubstitution)) else None


def _if_to_ternary(stmt):
    if not isinstance(stmt, A.IfStatement) or stmt.false_statement is None:
        return None
    t, f = _single_subst(stmt.true_statement), _single_subst(stmt.false_statement)
    if t is None or f is None or type(t) is not type(f):
        return None
    if V.emit(t.left) != V.emit(f.left):
        return None
    tv = t.right.var if isinstance(t.right, A.Rvalue) else t.right
    fv = f.right.var if isinstance(f.right, A.Rvalue) else f.right
    return type(t)(copy.deepcopy(t.left), A.Rvalue(A.Cond(stmt.cond, tv, fv)))


def _async_reset_blocks(ast):
    """Always blocks whose sensitivity list has two or more edge events (clock + asynchronous reset): their reset
    `if` must stay an `if` (a ternary is not an async reset for Yosys / DC)."""
    out = []
    for n in V.walk(ast):
        if isinstance(n, A.Always) and n.sens_list is not None:
            edges = [s for s in n.sens_list.list if getattr(s, "type", None) in ("posedge", "negedge")]
            if len(edges) >= 2:
                out.append(n)
    return out


def p4_ctrl(ast, seed, k, max_sites=2):
    ast = copy.deepcopy(ast)
    r = V.rng(seed, "P4", k)
    async_blocks = _async_reset_blocks(ast)
    in_async = set()
    for blk in async_blocks:
        for n in V.walk(blk):
            in_async.add(id(n))
    cands = []
    for parent, attr, idx, node in sites(ast, lambda n: isinstance(n, (A.CaseStatement, A.BlockingSubstitution, A.NonblockingSubstitution, A.IfStatement)), skip_under=(A.Function, A.Task)):
        if _case_to_if(node) is not None:
            cands.append(("case_to_if", parent, attr, idx, node))
        elif _ternary_to_if(node) is not None:
            cands.append(("ternary_to_if", parent, attr, idx, node))
        elif _if_to_ternary(node) is not None and id(node) not in in_async:
            cands.append(("if_to_ternary", parent, attr, idx, node))
    if not cands:
        raise NotApplicable("no control-structure site")
    n = min(len(cands), 1 + r.randrange(0, max_sites))
    chosen = r.sample(cands, n)
    applied = []
    # apply outermost-first is unsafe when sites nest: apply in reverse discovery order (inner nodes were found later)
    for kind, parent, attr, idx, node in sorted(chosen, key=lambda c: -cands.index(c)):
        new = {"case_to_if": _case_to_if, "ternary_to_if": _ternary_to_if, "if_to_ternary": _if_to_ternary}[kind](node)
        if new is None:
            continue
        replace_child(parent, attr, idx, new)
        applied.append(kind)
    if not applied:
        raise NotApplicable("no control-structure site")
    return ast, {"ctrl_sites": applied}


TRANSFORMS = {"P1_rename": p1_rename, "P2_reorder": p2_reorder, "P3_expr": p3_expr, "P4_ctrl": p4_ctrl}
