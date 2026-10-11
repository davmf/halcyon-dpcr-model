"""The loader reads the Halcyon model into the same IR as the fixture."""

from pathlib import Path

from generator.loader import load_model
from tests.fixtures.halcyon_ir import build_model

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"


def test_loaded_graph_matches_fixture_except_invalid_marking() -> None:
    loaded = load_model(MODEL_DIR)
    fixture = build_model()
    assert set(loaded.nodes) == set(fixture.nodes)
    for name, node in loaded.nodes.items():
        if name == "markInvalid":
            # The model has no assignment that sets sample.invalid.
            assert node.assignments == ()
            continue
        assert node == fixture.nodes[name], name


def test_loaded_scenarios_and_verifications() -> None:
    loaded = load_model(MODEL_DIR)
    assert set(loaded.scenarios) == {
        "baseBatch",
        "baseSteady",
        "highThroughput",
    }
    assert loaded.scenarios["highThroughput"].resources["blocks"].capacity == 3
    uids = sorted(v.requirement_uid for v in loaded.verifications)
    assert uids == [
        "SYS-TAT-001",
        "SYS-TAT-002",
        "SYS-TAT-003",
        "SYS-THR-001",
        "SYS-UTL-001",
        "SYS-VAL-001",
    ]
