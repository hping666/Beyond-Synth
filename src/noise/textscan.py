"""Text-level Verilog scanning without a parser (REQUEST 2026-09-20 (e) item 3, PLAN 6.9; harness note in DECISIONS): comment /
string masking, the declared-identifier table of a design and the segmentation of a module body into items, used by the
text-level perturbations P1_text (src/noise/rename_text.py) and P2_text (src/noise/reorder_text.py) so that neither depends on
the Pyverilog front end (which fails on 7 of the 13 pooled-floor designs). The scanners are conservative: whatever they cannot
delimit with certainty — an always body without begin ... end, a generate-if or case at module level, a compiler directive
inside a module body, a UDP table, a specify block — makes them refuse the module (Refuse), never guess."""
import re

IDENT = r"[A-Za-z_][A-Za-z0-9_$]*"
_ID_RE = re.compile(IDENT)
DECL_KINDS = ("reg", "wire", "integer", "real", "realtime", "time", "genvar", "tri", "tri0", "tri1", "triand", "trior", "trireg",
              "wand", "wor", "supply0", "supply1", "logic", "bit", "byte", "int", "parameter", "localparam", "specparam")
PORT_KINDS = ("input", "output", "inout")
_MODIFIERS = frozenset(("signed", "unsigned", "scalared", "vectored", "var", "const", "automatic", "static") + DECL_KINDS + PORT_KINDS)
_DECL_RE = re.compile(r"(?<![\w$.])(" + "|".join(DECL_KINDS) + r")\b(?P<body>[^;]*);")
_PORT_DECL_RE = re.compile(r"(?<![\w$.])(input|output|inout)\b(?P<body>[^;]*);")
_MODULE_RE = re.compile(r"(?<![\w$.])(module|macromodule)\s+(" + IDENT + ")")
_FUNC_RE = re.compile(r"(?<![\w$.])(function|task)\b(?P<head>[^;(]*)[;(]")
_FUNC_BODY_RE = re.compile(r"(?<![\w$.])function\b.*?\bendfunction\b|(?<![\w$.])task\b.*?\bendtask\b", re.S)
_NAMED_CONN_RE = re.compile(r"\.\s*(" + IDENT + r")\s*\(")
_INSTANCE_RE = re.compile(r"(?<![\w$.#])(" + IDENT + r")\s*(?:#\s*\((?:[^()]|\([^()]*\))*\)\s*)?(" + IDENT + r")\s*\(")
_KW_BLOCK = re.compile(r"\b(begin|end|case[xz]?|endcase|fork|join(?:_any|_none)?)\b")
_ALWAYS_WORDS = ("always", "always_ff", "always_comb", "always_latch", "initial")


class Refuse(Exception):
    """The scanner cannot delimit the module's items with certainty: no reorder in that module."""


def mask(text, escaped=True):
    """Comments and string literals replaced by spaces of the same length (offsets and newlines preserved); with `escaped`,
    escaped identifiers (\\name up to the next whitespace) as well, so that a plain identifier scan never reads inside them."""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", text[i:j]))
            i = j
        elif c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(" " * (j - i))
            i = j
        elif escaped and c == "\\":
            j = i
            while j < n and not text[j].isspace():
                j += 1
            out.append(" " * (j - i))
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def split_depth0(s, sep=","):
    parts, depth, cur = [], 0, []
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return parts


def strip_brackets(s):
    out, depth = [], 0
    for ch in s:
        if ch == "[":
            depth += 1
            continue
        if ch == "]":
            depth -= 1
            continue
        if depth == 0:
            out.append(ch)
    return "".join(out)


def names_in_decl(body):
    """The declared names of `[signed] [range] a [range] [= x], b, ...` (ranges, initialisers and modifiers removed); a piece
    that is a port expression (.name(expr)) yields nothing."""
    names = []
    for piece in split_depth0(body):
        if piece.strip().startswith("."):
            continue
        piece = strip_brackets(piece.split("=", 1)[0])
        toks = [t for t in _ID_RE.findall(piece) if t not in _MODIFIERS]
        if toks:
            names.append(toks[-1])
    return names


def _match_paren(m, i):
    """m[i] == '(' -> the index after the matching ')'."""
    depth = 0
    for j in range(i, len(m)):
        if m[j] == "(":
            depth += 1
        elif m[j] == ")":
            depth -= 1
            if depth == 0:
                return j + 1
    raise Refuse("unbalanced parentheses")


def _skip_ws(m, i):
    while i < len(m) and m[i].isspace():
        i += 1
    return i


def module_headers(m):
    """[(name, header_start, body_start, body_end)] for every module of a masked text: the header ends at its first ';', the
    body at the next endmodule."""
    out = []
    for mo in _MODULE_RE.finditer(m):
        name = mo.group(2)
        j = m.find(";", mo.end())
        if j < 0:
            raise Refuse(f"module {name}: header without ';'")
        end = re.compile(r"\bendmodule\b").search(m, j)
        if end is None:
            raise Refuse(f"module {name}: no endmodule")
        out.append((name, mo.start(), j + 1, end.start()))
    return out


def header_names(m, header_start, body_start):
    """(parameter names, port names) of a module header `module name #(params) (ports);`."""
    head = m[header_start:body_start]
    mo = _MODULE_RE.match(head)
    i = _skip_ws(head, mo.end())
    params, ports = [], []
    if head.startswith("#", i):
        i = _skip_ws(head, i + 1)
        if not head.startswith("(", i):
            raise Refuse("parameter port list without '('")
        j = _match_paren(head, i)
        for piece in split_depth0(head[i + 1:j - 1]):
            params += names_in_decl(re.sub(r"(?<![\w$.])(parameter|localparam)\b", " ", piece))
        i = _skip_ws(head, j)
    if head.startswith("(", i):
        j = _match_paren(head, i)
        for piece in split_depth0(head[i + 1:j - 1]):
            ports += names_in_decl(piece)
    return params, ports


def identifier_table(texts):
    """{name: kind} of the renamable internal identifiers of a design given as texts: every declared net / register / integer /
    parameter / genvar of every module (function and task locals excluded) minus every port name, module name, instance name,
    instantiated module name, function / task name and named-connection name of any module, minus keywords; escaped identifiers
    are never in the table. Mirrors src/noise/vast.declared_names + rename_text.identifier_table without the parser."""
    from src.noise.vast import KEYWORDS
    declared, protected = {}, set(KEYWORDS)
    for text in texts:
        m = mask(text)
        for name, hs, bs, be in module_headers(m):
            protected.add(name)
            params, ports = header_names(m, hs, bs)
            protected |= set(ports)
            for p in params:
                declared.setdefault(p, "Parameter")
        for mo in _FUNC_RE.finditer(m):
            toks = _ID_RE.findall(mo.group("head"))
            if toks:
                protected.add(toks[-1])
        body = _FUNC_BODY_RE.sub(lambda mo: " " * len(mo.group(0)), m)
        for mo in _PORT_DECL_RE.finditer(body):
            protected |= set(names_in_decl(mo.group("body")))
        for mo in _NAMED_CONN_RE.finditer(body):
            protected.add(mo.group(1))
        for mo in _INSTANCE_RE.finditer(body):
            a, b = mo.group(1), mo.group(2)
            if a in KEYWORDS or b in KEYWORDS or a in _MODIFIERS or b in _MODIFIERS:
                continue
            protected.add(a)
            protected.add(b)
        for mo in _DECL_RE.finditer(body):
            kind = mo.group(1)
            for n in names_in_decl(mo.group("body")):
                declared.setdefault(n, kind.capitalize())
    return {n: k for n, k in declared.items() if n not in protected}


def all_identifiers(texts):
    names = set()
    for text in texts:
        names |= set(_ID_RE.findall(mask(text)))
    return names


def _match_block(m, i):
    """m[i:] starts with `begin` -> the index after its matching `end` (case / endcase and fork / join nest inside)."""
    depth = 0
    for mo in _KW_BLOCK.finditer(m, i):
        w = mo.group(1)
        if w == "begin" or w.startswith("case") or w == "fork":
            depth += 1
        else:
            depth -= 1
        if depth == 0:
            return mo.end()
    raise Refuse("unbalanced begin / end")


def _match_kw(m, i, open_kw, close_kw):
    mo = re.compile(r"\b" + close_kw + r"\b").search(m, i + len(open_kw))
    if mo is None:
        raise Refuse(f"{open_kw} without {close_kw}")
    return mo.end()


def _stmt_end(m, i, end):
    depth = 0
    for j in range(i, end):
        c = m[j]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == ";" and depth == 0:
            return j + 1
    raise Refuse("item without ';'")


_PROC_SIMPLE = ("wait", "disable", "force", "release", "deassign", "assign")


def stmt_end_any(m, i, end):
    """The index after one procedural statement starting at i (masked text): a begin ... end block, a case ... endcase, a
    fork ... join, an if / else chain, a for / while / repeat / forever loop, or a simple statement up to its ';'. Refuses timing
    controls (# / @) inside procedural code and anything else it cannot delimit."""
    i = _skip_ws(m, i)
    while m.startswith("(*", i):
        j = m.find("*)", i)
        if j < 0:
            raise Refuse("unterminated attribute")
        i = _skip_ws(m, j + 2)
    if i >= end:
        raise Refuse("statement expected")
    if m[i] == ";":
        return i + 1
    if m[i] in "#@":
        raise Refuse("timing control inside a procedural statement")
    mo = _ID_RE.match(m, i)
    word = mo.group(0) if mo else None
    if word in ("begin", "case", "casex", "casez", "fork"):
        return _match_block(m, i)
    if word == "if":
        j = _skip_ws(m, i + 2)
        if not m.startswith("(", j):
            raise Refuse("if without '('")
        j = stmt_end_any(m, _match_paren(m, j), end)
        k = _skip_ws(m, j)
        if re.match(r"else\b", m[k:]):
            j = stmt_end_any(m, k + 4, end)
        return j
    if word in ("for", "while", "repeat"):
        j = _skip_ws(m, i + len(word))
        if not m.startswith("(", j):
            raise Refuse(f"{word} without '('")
        return stmt_end_any(m, _match_paren(m, j), end)
    if word == "forever":
        return stmt_end_any(m, i + 7, end)
    if word in ("else", "end", "endcase", "join", "endmodule", "always", "initial", "function", "task", "generate"):
        raise Refuse(f"unexpected {word}")
    return _stmt_end(m, i, end)


_NBA_RE = re.compile(r"^\s*(" + IDENT + r")\s*(?:\[[^\]]*\]\s*)*<=")


def nba_statements(m, body_s, body_e):
    """The statements of a `begin ... end` always body (m[body_s] at `begin`) when EVERY statement is a nonblocking assignment to a
    distinct base identifier (`x <= ...;` or `x[i] <= ...;`): [(s, e)] spans, else None (the AST reorder's rule for always blocks)."""
    mo = re.match(r"begin\b(\s*:\s*" + IDENT + r")?", m[body_s:])
    if mo is None:
        return None
    i = _skip_ws(m, body_s + mo.end())
    stmts = []
    inner_end = body_e - 3   # the closing `end`
    while i < inner_end:
        if re.match(r"end\b", m[i:]):
            break
        try:
            e = stmt_end_any(m, i, inner_end + 3)
        except Refuse:
            return None
        stmts.append((i, e))
        i = _skip_ws(m, e)
    names = []
    for s, e in stmts:
        mo = _NBA_RE.match(m[s:e])
        if mo is None or _ID_RE.match(m, s) and _ID_RE.match(m, s).group(0) in ("if", "case", "casex", "casez", "for", "while", "begin", "fork", "repeat", "forever"):
            return None
        names.append(mo.group(1))
    if len(stmts) < 2 or len(set(names)) != len(names):
        return None
    return stmts


def module_items(m, start, end):
    """The items of one module body of a masked text as [(kind, s, e)] with kind assign / always / other, covering the body in
    order; raises Refuse when an item cannot be delimited with certainty."""
    out = []
    i = _skip_ws(m, start)
    while i < end:
        s = i
        if m[i] == "`":
            raise Refuse("compiler directive inside the module body")
        while m.startswith("(*", i):
            j = m.find("*)", i)
            if j < 0:
                raise Refuse("unterminated attribute")
            i = _skip_ws(m, j + 2)
        mo = _ID_RE.match(m, i)
        word = mo.group(0) if mo else None
        if word == "assign":
            e = _stmt_end(m, i, end)
            out.append(("assign", s, e))
        elif word in _ALWAYS_WORDS:
            j = _skip_ws(m, i + len(word))
            if m.startswith("@", j):
                j = _skip_ws(m, j + 1)
                if m.startswith("(", j):
                    j = _match_paren(m, j)
                elif m.startswith("*", j):
                    j += 1
                else:
                    raise Refuse("sensitivity list not understood")
                j = _skip_ws(m, j)
            e = stmt_end_any(m, j, end)   # a begin ... end block or one procedural statement (if / else chain, case, loop, assignment)
            out.append(("always" if word != "initial" else "other", s, e))
        elif word == "generate":
            e = _match_kw(m, i, "generate", "endgenerate")
            out.append(("other", s, e))
        elif word == "function":
            e = _match_kw(m, i, "function", "endfunction")
            out.append(("other", s, e))
        elif word == "task":
            e = _match_kw(m, i, "task", "endtask")
            out.append(("other", s, e))
        elif word == "for":
            j = _skip_ws(m, i + 3)
            if not m.startswith("(", j):
                raise Refuse("generate for without '('")
            j = _skip_ws(m, _match_paren(m, j))
            if not re.match(r"begin\b", m[j:]):
                raise Refuse("generate for without begin ... end")
            e = _match_block(m, j)
            out.append(("other", s, e))
        elif word in ("if", "case", "casex", "casez", "else", "specify", "table", "primitive", "endmodule"):
            raise Refuse(f"{word} at module level")
        else:
            e = _stmt_end(m, i, end)
            out.append(("other", s, e))
        i = _skip_ws(m, e)
    return out
