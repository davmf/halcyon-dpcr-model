"""Tests of the IR: expression evaluation, durations and graph validation."""

import dataclasses

import pytest

from generator import ir
from tests.fixtures.halcyon_ir import build_model


def test_priming_time_calc_matches_hand_value() -> None:
    model = build_model()
    values = {
        "pressure": 20000.0,
        "viscosity": 0.002,
        "length": 0.3,
        "diameter": 0.1e-3,
    }
    priming = ir.evaluate(
        ir.Call(
            "PrimingTime",
            tuple(
                (name, ir.Ref(name))
                for name in ("diameter", "length", "pressure", "viscosity")
            ),
        ),
        values,
        model.calcs,
    )
    assert priming == pytest.approx(28.8, rel=1e-3)


def test_thermal_run_is_2800_seconds() -> None:
    model = build_model()
    scenario = model.scenario("baseSteady")
    duration = model.nodes["thermalCycle"].duration
    assert duration.mean(scenario.values, model.calcs) == pytest.approx(2800)


def test_unknown_reference_raises() -> None:
    with pytest.raises(ir.ExpressionError):
        ir.evaluate(ir.Ref("missing"), {}, {})


def test_validate_rejects_dangling_successor() -> None:
    model = build_model()
    broken = dataclasses.replace(
        model,
        nodes={
            **model.nodes,
            "report": ir.Step(
                name="report",
                duration=ir.Duration(ir.Distribution.FIXED, ir.Literal(0.0)),
                next=("nowhere",),
            ),
        },
    )
    with pytest.raises(ValueError, match="unknown node nowhere"):
        ir.validate(broken)


def test_join_inputs_count_incoming_successions() -> None:
    model = build_model()
    assert model.join_inputs("joined") == 2
    assert model.join_inputs("partitioned") == 3
