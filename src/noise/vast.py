"""Pyverilog front end for the perturbation generator (docs/spec/02-noise-floor.md §1): parse a design's files into
one AST, walk it, list the names declared inside each module (never ports or module names) and emit Verilog again.

Pyverilog preprocesses with Icarus (`iverilog -E`), so `include / `define are resolved in the emitted text; the
emitted code is a normalised re-print of the whole design (comments and layout are lost), which is itself a
surface rewrite common to every perturbation of a design."""
import random
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


def parse_files(files, incdirs=None, defines=None):
    """-> (ast, directives) for a list of Verilog files (all modules of the design)."""
    return parse([str(Path(f).resolve()) for f in files],
                 preprocess_include=[str(Path(d).resolve()) for d in (incdirs or [])],
                 preprocess_define=list(defines or []))


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
