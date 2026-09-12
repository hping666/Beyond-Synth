"""Phase 1.2 inventory (docs/PLAN.md): per staged design the lines of code, the Yosys-parsed interface (ports,
their hash, clock and reset inference), testbench / SDC availability and the DC-relevant markers; the values are
written back into design.json (`inventory`, clk_ports, rst_port, tags multi_clock / no_clock / yosys_failed /
sverilog_only) and upserted into results.sqlite.designs. E4 synthesizability and the knee periods are filled by
later Phase 1 steps from the evaluation records."""
import hashlib
import json
from pathlib import Path

from src import config as C
from src.db import core as db
from src.designs import catalog as K
from src.designs import verilog as V
from src.designs import yosys_probe as YP
from src.equiv.ports import PortError, _CLOCK, infer_control_ports

AUTO_TAGS = ("multi_clock", "no_clock", "yosys_failed", "sverilog_only")


def ports_hash(ports):
    items = [(n, i["dir"], int(i["width"])) for n, i in ports.items()]
    return hashlib.sha256(json.dumps(items).encode()).hexdigest()[:16]


def inventory_design(d, cfg, workdir=None, timeout=300):
    files = K.abs_paths(d, d["files"])
    incdirs = K.abs_paths(d, d["incdirs"])
    texts = [f.read_text(errors="replace") for f in files]
    inv = {"loc": sum(V.count_lines(f) for f in files), "n_files": len(files),
           "tb_available": int(bool(d.get("tb"))), "sdc_available": int(bool(d.get("sdc"))),
           "flags": V.merge_flags(*(V.flags(t) for t in texts))}
    ports, err, used, pr = None, None, None, None
    for sv in ([True] if d["sverilog"] else [False, True]):
        try:
            pr = YP.probe(files, d["top"], cfg, sverilog=sv, incdirs=incdirs, workdir=workdir, timeout=timeout)
            ports, used = pr["ports"], sv
            break
        except PortError as e:
            err = str(e)[:500]
        except Exception as e:  # yosys missing, timeout, ...
            err = f"{type(e).__name__}: {e}"[:500]
    if ports is None:
        inv.update(yosys_ok=0, yosys_error=err, ports=None, ports_hash=None)
        return inv
    clks = list(pr["clock_ports"])  # by use (flip-flop clock pins), not by name
    name_clks = [n for n, i in ports.items() if i["dir"] == "input" and int(i["width"]) == 1 and _CLOCK.match(n)]
    _, rst, sense = infer_control_ports({n: i for n, i in ports.items() if n not in clks})
    if pr["async_resets"]:  # an asynchronous reset seen by Yosys is authoritative, polarity included
        n0 = next(iter(pr["async_resets"]))
        rst = n0
        sense = pr["async_resets"][n0] if pr["async_resets"][n0] in ("low", "high") else sense
    ins = [i for i in ports.values() if i["dir"] == "input"]
    outs = [i for i in ports.values() if i["dir"] == "output"]
    inv.update(yosys_ok=1, yosys_error=None, ports=ports, ports_hash=ports_hash(ports), sverilog=used,
               clk_ports=clks, clk_ports_by_name=name_clks, async_resets=pr["async_resets"], n_cells=pr["n_cells"],
               n_ff_bits=pr["n_ff_bits"], rst_port=rst, rst_sense=sense, n_inputs=len(ins), n_outputs=len(outs),
               in_bits=sum(int(i["width"]) for i in ins), out_bits=sum(int(i["width"]) for i in outs))
    return inv


def apply_inventory(d, inv):
    tags = [t for t in d["tags"] if t not in AUTO_TAGS]
    if inv["yosys_ok"]:
        d["clk_ports"] = inv["clk_ports"]
        if inv["rst_port"]:  # Yosys / name inference found a reset; otherwise the staged value (design_all.json, regex) stays
            d["rst_port"], d["rst_sense"] = inv["rst_port"], inv["rst_sense"]
        if inv["sverilog"] and not d["sverilog"]:
            d["sverilog"] = True
            tags.append("sverilog_only")
        if len(inv["clk_ports"]) > 1:
            tags.append("multi_clock")
        if not inv["clk_ports"]:
            tags.append("no_clock")
    else:
        tags.append("yosys_failed")
    d["tags"] = tags
    d["loc"] = inv["loc"]
    d["inventory"] = dict(inv)
    return K.write_design(d)


def designs_row(d):
    s = d["source"]
    inv = d.get("inventory") or {}
    ddir = Path(d["_dir"])
    try:
        path = str(ddir.relative_to(C.ROOT))
    except ValueError:  # catalogue outside the project (tests)
        path = str(ddir)
    return {"design_id": d["design_id"], "suite": d["suite"], "name": d["name"],
            "path": path, "loc": d["loc"], "ports_hash": inv.get("ports_hash"),
            "tb_available": int(bool(d.get("tb"))), "sdc_available": int(bool(d.get("sdc"))),
            "source_url": s["url"], "source_commit": s["commit"], "license": s["license"], "tags": json.dumps(d["tags"])}


def upsert_design(conn, row):
    """Insert or refresh the inventory columns of a designs row; e4_* / phi_main_* / knee_table_json / split are
    never touched here (they are written by the steps that measure them)."""
    row = dict(row)
    row.update(db.stamp())
    cols = list(row)
    upd = ", ".join(f"{c}=excluded.{c}" for c in cols if c not in ("design_id", "created_at"))
    conn.execute(f"INSERT INTO designs ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)}) "
                 f"ON CONFLICT(design_id) DO UPDATE SET {upd}", tuple(row.values()))
    return conn.execute("SELECT * FROM designs WHERE design_id=?", (row["design_id"],)).fetchone()


SV_HINTS = ("The construct '", "C-style unpacked", "post-increment", "pre-increment", "Type query about", "SystemVerilog")


def needs_sv_retry(design, reason):
    """DC read the design as Verilog-2001 and stopped at a SystemVerilog construct ("The construct '++' is not
    supported", C-style unpacked dimensions, type queries): retry once as SystemVerilog. Only for read errors of
    designs not yet marked sverilog; genuine RTL errors (hierarchical names, width mismatches, non-register
    assignments, unsupported event lists) are not retried."""
    if design.get("sverilog") or not reason or "Error" not in reason:
        return False
    return any(h in reason for h in SV_HINTS)


def mark_sverilog(d, reason):
    d["sverilog"] = True
    if "sverilog_only" not in d["tags"]:
        d["tags"].append("sverilog_only")
    d["notes"].append(f"read as SystemVerilog after DC rejected the Verilog-2001 read: {reason[:160]}")
    return K.write_design(d)
