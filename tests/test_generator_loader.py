"""The loader reads the Halcyon model into the same IR as the fixture."""

from pathlib import Path

from generator.loader import load_model
from tests.fixtures.halcyon_ir import build_model

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"


def test_loaded_graph_matches_fixture() -> None:
    loaded = load_model(MODEL_DIR)
    fixture = build_model()
    assert set(loaded.nodes) == set(fixture.nodes)
    for name, node in loaded.nodes.items():
        assert node == fixture.nodes[name], name


def test_loaded_scenarios_and_verifications() -> None:
    loaded = load_model(MODEL_DIR)
    assert set(loaded.scenarios) == {
        "baseBatch",
        "baseSteady",
        "highThroughput",
        "highThroughputBatch",
    }
    assert loaded.scenarios["highThroughput"].resources["blocks"].capacity == 3
    cases = sorted(v.case_id for v in loaded.verifications)
    assert cases == [
        "VER-TAT-001-HT",
        "VER-TAT-002-HT",
        "VER-THR-001-HT",
        "VER-UTL-001-HT",
        "verSysTat001",
        "verSysTat002",
        "verSysTat003",
        "verSysThr001",
        "verSysUtl001",
        "verSysVal001",
    ]
    by_case = {v.case_id: v for v in loaded.verifications}
    assert by_case["VER-TAT-001-HT"].scenario == "highThroughputBatch"
    assert by_case["VER-THR-001-HT"].scenario == "highThroughput"
