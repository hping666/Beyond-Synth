"""pytest configuration: tests marked `eda` run the real tools (DC / PrimeTime / Yosys, minutes, license seats)
and are skipped unless BS_EDA_TESTS=1 is set (source /hdd1/hping/eda/setup/env.sh first)."""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def pytest_configure(config):
    config.addinivalue_line("markers", "eda: runs real EDA tools; enable with BS_EDA_TESTS=1")


def pytest_collection_modifyitems(config, items):
    if os.environ.get("BS_EDA_TESTS") == "1":
        return
    skip = pytest.mark.skip(reason="EDA tests need BS_EDA_TESTS=1 (and the EDA env.sh sourced)")
    for item in items:
        if "eda" in item.keywords:
            item.add_marker(skip)
