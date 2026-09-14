"""Bidirectional tests of the design-set assignment rules (src/designs/sets.py)."""
import pytest

from src.designs import sets as S


def d(name, loc, suite="cktevo", path=None):
    return {"design_id": f"{suite}_{name}", "name": name, "loc": loc, "suite": suite, "source": {"paths": [path or f"x/{name}.v"]}}


def test_cktevo_round_robin_respects_caps_and_size_order():
    pool = [d("a__m1", 900), d("a__m2", 800), d("a__m3", 700), d("b__m1", 500), d("c__m1", 300), d("c__m2", 100)]
    got = [x["name"] for x in S.select_cktevo_set(pool, target_count=4, max_per_repo=2)]
    assert got == ["a__m1", "b__m1", "c__m1", "a__m2"]  # round 1 one per repo (largest), round 2 continues alphabetically
    assert [x["name"] for x in S.select_cktevo_set(pool, 10, 1)] == ["a__m1", "b__m1", "c__m1"]  # cap 1 per repo
    assert [x["name"] for x in S.select_cktevo_set(pool, 10, 5)] == ["a__m1", "b__m1", "c__m1", "a__m2", "c__m2", "a__m3"]
    assert S.select_cktevo_set([], 5, 5) == []


def test_stratified_sample_is_deterministic_and_proportional():
    pool = [d(f"ar{i}", 10, "rtllm", f"Arithmetic/x/ar{i}") for i in range(10)] + \
           [d(f"me{i}", 10, "rtllm", f"Memory/x/me{i}") for i in range(4)] + \
           [d(f"co{i}", 10, "rtllm", f"Control/x/co{i}") for i in range(6)]
    a = S.stratified_sample(pool, 10, seed=1)
    b = S.stratified_sample(pool, 10, seed=1)
    assert a == b and len(a) == 10
    cats = {S.category_of(x) for x in a}
    assert cats == {"Arithmetic", "Memory", "Control"}
    assert sum(S.category_of(x) == "Arithmetic" for x in a) == 5 and sum(S.category_of(x) == "Control" for x in a) == 3
    assert S.stratified_sample(pool, 10, seed=2) != a  # the seed matters
    assert S.stratified_sample(pool, 100, seed=1) == sorted(pool, key=lambda x: x["design_id"])
    assert S.stratified_sample([], 3, seed=1) == []


def test_yaml_list_rewrite_only_touches_the_field():
    text = ("design_sets:\n  suites:\n    drrtl:     {source: \"x\", count: 20, dev: [], held: TBD}\n"
            "    rtllm:     {source: \"RTLLM v2.0\", count: 50, synthesizable_under_e4: TBD, dev: TBD, held: TBD}\n")
    out = S.set_yaml_list(text, "rtllm", "dev", ["rtllm_accu", "rtllm_fsm"])
    assert "dev: [rtllm_accu, rtllm_fsm], held: TBD}" in out and "drrtl:     {source: \"x\", count: 20, dev: [], held: TBD}" in out
    out = S.set_yaml_list(out, "rtllm", "held", ["rtllm_pe"])
    assert "dev: [rtllm_accu, rtllm_fsm], held: [rtllm_pe]}" in out
    out = S.set_yaml_list(out, "drrtl", "held", [])
    assert "drrtl:     {source: \"x\", count: 20, dev: [], held: []}" in out
    out = S.set_yaml_list(out, "rtllm", "held", ["rtllm_a", "rtllm_b"])  # replacing an existing list must not leave a tail
    assert "dev: [rtllm_accu, rtllm_fsm], held: [rtllm_a, rtllm_b]}" in out and out.count("]") == out.count("[")
    import yaml
    assert yaml.safe_load(out)["design_sets"]["suites"]["rtllm"]["held"] == ["rtllm_a", "rtllm_b"]
    with pytest.raises(ValueError):
        S.set_yaml_list(text, "nope", "dev", [])


def test_write_config_round_trips_and_restores_on_error(tmp_path, monkeypatch):
    import importlib.util
    from src import config as C
    spec = importlib.util.spec_from_file_location("phase1_sets", "scripts/phase1_sets.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cfg_copy = tmp_path / "experiments.yaml"
    cfg_copy.write_text(open(C.CONFIG_PATH).read())
    monkeypatch.setattr(C, "CONFIG_PATH", str(cfg_copy))
    mod.write_config([("rtllm", "dev", ["rtllm_accu", "rtllm_fsm"]), ("drrtl", "held", ["drrtl_tv80"])])
    cfg = C.load(str(cfg_copy))
    assert cfg["design_sets"]["suites"]["rtllm"]["dev"] == ["rtllm_accu", "rtllm_fsm"] and cfg["design_sets"]["suites"]["drrtl"]["held"] == ["drrtl_tv80"]
    before = cfg_copy.read_text()
    with pytest.raises(ValueError):
        mod.write_config([("no_such_suite", "dev", ["x"])])
    assert cfg_copy.read_text() == before


def test_knee_ext_jobs_only_for_designs_at_the_tightest_period():
    """DECISIONS 2026-09-14: the two tighter periods are submitted only for designs whose Phi_main is the tightest swept
    period of that library; multi-clock designs are skipped; nothing for a library without an extension."""
    from src import config as C
    from src.designs import jobs as J
    cfg = C.load()
    designs = [{"design_id": "a", "suite": "rtllm", "top": "a", "files": ["a.v"], "incdirs": [], "clk_ports": ["clk"], "tags": [], "loc": 10, "sverilog": False, "_dir": "/x"},
               {"design_id": "m", "suite": "rtllm", "top": "m", "files": ["m.v"], "incdirs": [], "clk_ports": ["clk", "clk2"], "tags": ["multi_clock"], "loc": 10, "sverilog": False, "_dir": "/x"}]
    jobs = J.knee_ext_jobs(cfg, designs, {"nangate45": ["a", "m"], "asap7": ["a"], "sky130hd": []})
    assert sorted((j["design_id"], j["config"], j["payload"]["clock_ns"]) for j in jobs) == [("a", "E4", 0.25), ("a", "E4", 0.35), ("a", "K_asap7", 0.065), ("a", "K_asap7", 0.09)]
