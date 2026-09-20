"""scripts/netlist_structure_compare.py <netlist_a.v> <netlist_b.v> — Name-independent structural comparison of two DC gate-level netlists: parse cell instances (type, pin -> net), build the
driver graph, hash every instance by (cell type, per input pin: the driver's hash and output pin) over k rounds (Weisfeiler-Lehman
style; primary inputs and constants are labelled by their kind), compare the multisets of instance hashes. Read-only."""
import re, sys, hashlib, collections
INST = re.compile(r"^\s*([A-Za-z_][\w$]*)\s+([\\]?[^\s(]+)\s*\((.*?)\)\s*;", re.S | re.M)
PIN = re.compile(r"\.([A-Za-z_]\w*)\s*\(\s*([^()]*?)\s*\)")
KW = {"module", "endmodule", "input", "output", "inout", "wire", "reg", "assign", "tri", "supply0", "supply1"}
OUT_PINS = {"ZN", "Z", "Q", "QN", "CO", "S", "GCLK", "Y", "ZA", "ZB"}

def parse(path):
    text = open(path, errors="replace").read()
    text = re.sub(r"//.*", "", text)
    ports = {}
    for m in re.finditer(r"\b(input|output|inout)\b([^;]*);", text):
        for n in re.split(r",", re.sub(r"\[[^\]]*\]", "", m.group(2))):
            n = n.strip()
            if n: ports[n] = m.group(1)
    assigns = []
    for m in re.finditer(r"\bassign\s+([^=;]+?)\s*=\s*([^;]+);", text):
        assigns.append((m.group(1).strip(), m.group(2).strip()))
    insts = []
    for m in INST.finditer(text):
        ctype, name, body = m.group(1), m.group(2), m.group(3)
        if ctype in KW: continue
        pins = {p: n.strip() for p, n in PIN.findall(body)}
        insts.append((ctype, name, pins))
    return ports, assigns, insts

def structure(path, rounds=6):
    ports, assigns, insts = parse(path)
    driver = {}   # net -> (inst index, pin) | ("PI", name) | ("CONST", v)
    alias = dict(assigns)
    for i, (ctype, name, pins) in enumerate(insts):
        for p, n in pins.items():
            if p in OUT_PINS: driver[n] = (i, p)
    def drv(n):
        seen = 0
        while n in alias and seen < 10: n = alias[n]; seen += 1
        if n in driver: return driver[n]
        if re.match(r"^1'b[01]$", n): return ("CONST", n)
        base = re.sub(r"\[.*$", "", n)
        if ports.get(base) == "input" or ports.get(n) == "input": return ("PI", base if base in ports else n)
        return ("FLOAT", "")
    h = [hashlib.sha1(ctype.encode()).hexdigest()[:16] for ctype, _, _ in insts]
    for _ in range(rounds):
        nh = []
        for i, (ctype, name, pins) in enumerate(insts):
            parts = [ctype]
            for p in sorted(pins):
                if p in OUT_PINS: continue
                d = drv(pins[p])
                parts.append(p + ":" + (f"{h[d[0]]}.{d[1]}" if isinstance(d[0], int) else f"{d[0]}:{'PIN' if d[0]=='PI' else d[1]}"))
            nh.append(hashlib.sha1("|".join(parts).encode()).hexdigest()[:16])
        h = nh
    # output cones: which instance drives each output port
    outs = {}
    for n, kind in ports.items():
        if kind == "output":
            d = drv(n)
            outs[n] = (h[d[0]] + "." + d[1]) if isinstance(d[0], int) else str(d)
    return {"n_inst": len(insts), "types": collections.Counter(c for c, _, _ in insts), "hashes": collections.Counter(h), "outs": outs, "names": [n for _, n, _ in insts], "ports": ports}

def compare(a, b):
    A, B = structure(a), structure(b)
    same_types = A["types"] == B["types"]
    same_struct = A["hashes"] == B["hashes"]
    diff = sum((A["hashes"] - B["hashes"]).values()) + sum((B["hashes"] - A["hashes"]).values())
    out_same = sum(1 for k in A["outs"] if A["outs"][k] == B["outs"].get(k))
    same_names = set(A["names"]) == set(B["names"])
    return {"instances": (A["n_inst"], B["n_inst"]), "same_cell_multiset": same_types, "same_structure_hashes": same_struct, "instances_with_differing_structure": diff,
            "output_cones_identical": f"{out_same} of {len(A['outs'])}", "instance_names_identical": same_names, "ports_identical": A["ports"] == B["ports"]}

if __name__ == "__main__":
    print(compare(sys.argv[1], sys.argv[2]))
