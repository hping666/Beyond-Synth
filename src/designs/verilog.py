"""Light-weight Verilog text helpers for staging and inventory. Yosys (src/equiv/ports.py) is the parser of record;
these regexes only find module boundaries, instantiations, declared ports and non-synthesizable markers in
comment-stripped text, which is enough to stage files, build module closures and rename a top module."""
import re

_LINE_COMMENT = re.compile(r"//[^\n]*")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_MODULE = re.compile(r"\bmodule\s+([A-Za-z_][A-Za-z_0-9$]*)")
_ENDMODULE = re.compile(r"\bendmodule\b")
_INST = re.compile(r"\b([A-Za-z_][A-Za-z_0-9$]*)\s*(?:#\s*\((?:[^()]|\([^()]*\))*\))?\s+([A-Za-z_][A-Za-z_0-9$]*)\s*(?:\[[^\]]*\]\s*)?\(")  # `mod #(..) inst[N:0] (` instance arrays included
_PORT = re.compile(r"\b(input|output|inout)\b\s*(?:wire|reg|logic|tri|var)?\s*(?:signed|unsigned)?\s*(\[[^\]]*\])?\s*"
                   r"([A-Za-z_][A-Za-z_0-9$]*(?:\s*,\s*(?!input\b|output\b|inout\b)[A-Za-z_][A-Za-z_0-9$]*)*)")
KEYWORDS = frozenset("""module endmodule input output inout wire reg logic integer real time realtime parameter localparam
assign always always_ff always_comb always_latch initial begin end if else case casex casez endcase default for while
repeat forever function endfunction task endtask generate endgenerate genvar posedge negedge or and not xor nor nand
xnor buf bufif0 bufif1 notif0 notif1 supply0 supply1 tri tri0 tri1 wand wor signed unsigned defparam specify endspecify
fork join disable wait deassign force release event edge return typedef enum struct union packed bit byte int
shortint longint string void interface endinterface modport package endpackage import export const automatic static
cover assert assume property endproperty sequence endsequence unique priority table endtable primitive endprimitive
small medium large scalared vectored highz0 highz1 strong0 strong1 pull0 pull1 weak0 weak1 rtran tran tranif0 tranif1
rtranif0 rtranif1 cmos rcmos nmos pmos rnmos rpmos pullup pulldown""".split())


def strip_comments(text):
    """Comments replaced by spaces; block comments keep their newlines so that line numbers survive."""
    text = _BLOCK_COMMENT.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
    return _LINE_COMMENT.sub("", text)


def module_names(text):
    return _MODULE.findall(strip_comments(text))


def module_spans(text):
    """[(name, first_line, last_line, body)] for every `module ... endmodule` (1-based, inclusive; body is comment-free)."""
    s = strip_comments(text)
    out, pos = [], 0
    while True:
        m = _MODULE.search(s, pos)
        if not m:
            break
        e = _ENDMODULE.search(s, m.end())
        end = e.end() if e else len(s)
        out.append((m.group(1), s.count("\n", 0, m.start()) + 1, s.count("\n", 0, end) + 1, s[m.start():end]))
        pos = end
    return out


def instantiated_modules(body):
    """Module names instantiated in a comment-free module body (`name [#(...)] inst (`); keywords are excluded."""
    found = set()
    for m in _INST.finditer(body):
        mod, inst = m.group(1), m.group(2)
        if mod in KEYWORDS or inst in KEYWORDS or mod.startswith("$"):
            continue
        found.add(mod)
    return found


def declared_ports(body):
    """[(name, direction, has_width)] from the port declarations of one comment-free module body (ANSI or classic)."""
    out = []
    for m in _PORT.finditer(body):
        direction, width, names = m.group(1), m.group(2), m.group(3)
        for n in re.split(r"\s*,\s*", names):
            if n and n not in KEYWORDS:
                out.append((n, direction, bool(width)))
    return out


def rename_identifier(text, old, new):
    """Rename an identifier everywhere (word boundaries that respect `$` and digits); used to give an RTLLM
    `verified_<x>` module the name its testbench instantiates."""
    return re.sub(rf"(?<![A-Za-z_0-9$]){re.escape(old)}(?![A-Za-z_0-9$])", new, text)


def flags(text):
    """Markers that make DC synthesize differently or fail (eda-knowledge/06-boundaries.md): initial blocks, delay
    controls, system tasks, `include`, `ifdef` and `timescale`."""
    s = strip_comments(text)
    return {"initial": bool(re.search(r"\binitial\b", s)),
            "delay": bool(re.search(r"#\s*[0-9]", s)),
            "sysfunc": bool(re.search(r"\$(display|finish|readmem[hb]|monitor|stop|fopen|fwrite|fclose|random|urandom)\b", s)),
            "include": bool(re.search(r"`include\b", s)),
            "ifdef": bool(re.search(r"`ifn?def\b", s)),
            "timescale": bool(re.search(r"`timescale\b", s))}


def merge_flags(*flag_dicts):
    out = {}
    for f in flag_dicts:
        for k, v in f.items():
            out[k] = out.get(k, False) or bool(v)
    return out


def count_lines(path):
    with open(path, errors="replace") as f:
        return sum(1 for _ in f)
