"""Pyverilog front end for the perturbation generator (docs/spec/02-noise-floor.md §1): parse a design's files into
one AST, walk it, list the names declared inside each module (never ports or module names) and emit Verilog again.

Pyverilog preprocesses with Icarus (`iverilog -E`), so `include / `define are resolved in the emitted text; the
emitted code is a normalised re-print of the whole design (comments and layout are lost), which is itself a
surface rewrite common to every perturbation of a design."""
import random
import re
from pathlib import Path

import pyverilog.vparser.ast as A
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator
from pyverilog.vparser.parser import parse

DECL_KINDS = (A.Reg, A.Wire, A.Integer, A.Real, A.Parameter, A.Localparam, A.Genvar, A.Tri, A.Supply)
KEYWORDS = frozenset("""always and assign begin buf bufif0 bufif1 case casex casez cmos deassign default defparam disable
edge else end endcase endfunction endmodule endprimitive endspecify endtable endtask event for force forever fork function
highz0 highz1 if ifnone initial inout input integer join large localparam macromodule medium module nand negedge nmos nor
not notif0 notif1 or output parameter pmos posedge primitive pull0 pull1 pulldown pullup rcmos real realtime reg release
repeat rnmos rpmos rtran rtranif0 rtranif1 scalared signed small specify specparam strong0 strong1 supply0 supply1 table
task time tran tranif0 tranif1 tri tri0 tri1 triand trior trireg unsigned vectored wait wand weak0 weak1 while wire wor
xnor xor logic bit byte int always_ff always_comb always_latch""".split())


_SIGNED_MULTI = re.compile(r"^(?P<indent>\s*)(?P<head>(?:(?:input|output|inout)\s+)?(?:(?:wire|reg)\s+)?signed\s*(?:\[[^\]]*\]\s*)?)"
                           r"(?P<names>[A-Za-z_][A-Za-z_0-9]*(?:\s*,\s*[A-Za-z_][A-Za-z_0-9]*)+)\s*(?P<end>[,;])(?P<rest>.*)$", re.M)
_REG_INIT = re.compile(r"\b(?:reg|integer)\b[^;=]*=\s*[^;]+;")


class Unsupported(Exception):
    """The design uses a construct Pyverilog re-prints with different semantics; no AST perturbations for it."""


def normalise_text(text):
    """Work around two Pyverilog re-print defects seen on the staged designs (DECISIONS 2026-09-12):
    (1) `input signed [7:0] a, b` loses `signed` on every name but the first -> split into one declaration per
    name; (2) `reg [3:0] x = 'd0;` is re-printed as `reg x; assign x = 'd0;` (an initial value becomes a
    continuous assignment) -> raise Unsupported. Returns (text, notes)."""
    notes = []
    if _REG_INIT.search(strip_comments_keep(text)):
        raise Unsupported("register declared with an initial value (Pyverilog re-prints it as a continuous assignment)")

    def split(m):
        names = [n.strip() for n in m.group("names").split(",")]
        head = m.group("head").strip()
        end = m.group("end")
        if end == ";":
            body = " ".join(f"{head} {n};" for n in names)
        else:
            body = ", ".join(f"{head} {n}" for n in names) + ","
        notes.append(f"split multi-name signed declaration: {', '.join(names)}")
        return f"{m.group('indent')}{body}{m.group('rest')}"

    return _SIGNED_MULTI.sub(split, text), notes


def strip_comments_keep(text):
    from src.designs.verilog import strip_comments
    return strip_comments(text)


def parse_files(files, incdirs=None, defines=None, workdir=None):
    """-> (ast, directives, notes) for a list of Verilog files (all modules of the design), after normalise_text();
    the normalised copies are written to `workdir` (a temporary directory by default)."""
    import tempfile
    wd = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="bs_vast_"))
    wd.mkdir(parents=True, exist_ok=True)
    staged, notes = [], []
    for f in files:
        text, n = normalise_text(Path(f).read_text(errors="replace"))
        notes += n
        dst = wd / Path(f).name
        dst.write_text(text)
        staged.append(str(dst.resolve()))
    incs = [str(Path(d).resolve()) for d in (incdirs or [])] + [str(Path(f).resolve().parent) for f in files]
    ast, directives = parse(staged, preprocess_include=sorted(set(incs)), preprocess_define=list(defines or []))
    return ast, directives, notes


def emit(ast, directives=()):
    """Verilog text: the preprocessor directives Pyverilog kept (`timescale, as (line, text) tuples) then the modules."""
    lines = []
    for d in directives or ():
        text = d[1] if isinstance(d, (tuple, list)) else str(d)
        if text.strip():
            lines.append(text.strip())
    return "".join(f"{x}\n" for x in lines) + ASTCodeGenerator().visit(ast)


def walk(node):
    """Depth-first generator over every AST node (the node itself first)."""
    yield node
    for child in node.children():
        if child is not None:
            yield from walk(child)


def modules(ast):
    return [d for d in ast.description.definitions if isinstance(d, A.ModuleDef)]


def port_names(module):
    names = set()
    if module.portlist is not None:
        for p in module.portlist.ports:
            if isinstance(p, A.Ioport):
                names.add(p.first.name)
                if p.second is not None:
                    names.add(p.second.name)
            elif isinstance(p, A.Port):
                names.add(p.name)
    for item in module.items:
        if isinstance(item, A.Decl):
            for d in item.list:
                if isinstance(d, (A.Input, A.Output, A.Inout)):
                    names.add(d.name)
    return names


def declared_names(module):
    """{name: kind} of the nets, registers, integers, parameters, localparams and genvars declared in the module
    body (ports excluded; function / task locals excluded)."""
    ports = port_names(module)
    out = {}
    for item in module.items:
        if isinstance(item, A.Decl):
            for d in item.list:
                if isinstance(d, DECL_KINDS) and d.name not in ports:
                    out[d.name] = type(d).__name__
    if module.paramlist is not None:
        for p in module.paramlist.params:
            for d in (p.list if isinstance(p, A.Decl) else [p]):
                if isinstance(d, (A.Parameter, A.Localparam)):
                    out[d.name] = type(d).__name__
    return out


def all_identifiers(ast):
    """Every identifier string that appears anywhere (declarations, references, module / instance / function names)."""
    names = set()
    for n in walk(ast):
        for attr in ("name",):
            v = getattr(n, attr, None)
            if isinstance(v, str):
                names.add(v)
        if isinstance(n, A.Instance):
            names.add(n.module)
        if isinstance(n, (A.PortArg,)) and n.portname:
            names.add(n.portname)
        if isinstance(n, (A.ParamArg,)) and n.paramname:
            names.add(n.paramname)
    return names


def rng(seed, *parts):
    """A deterministic random generator keyed by the seed and any number of string / int parts."""
    return random.Random("|".join(str(p) for p in (seed,) + parts))
