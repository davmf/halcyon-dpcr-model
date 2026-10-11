"""Tests of the verification framework and the fast analytic layer."""

from pathlib import Path
from xml.etree import ElementTree

import pytest

from verification import layer2_bounds
from verification.core import (
    CheckResult,
    Context,
    confidence_interval,
    run_module,
    t_critical,
    write_junit,
)

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"


@pytest.fixture(scope="module")
def context() -> Context:
    return Context(MODEL_DIR)


def test_t_critical_uses_table_then_normal() -> None:
    assert t_critical(9, 0.95) == pytest.approx(2.262)
    assert t_critical(100, 0.95) == pytest.approx(1.96)
    with pytest.raises(ValueError):
        t_critical(9, 0.9)


def test_confidence_interval_is_symmetric_around_the_mean() -> None:
    interval = confidence_interval([1.0, 2.0, 3.0], 0.95)
    assert interval.mean == pytest.approx(2.0)
    assert interval.upper - interval.mean == pytest.approx(
        interval.mean - interval.lower
    )


def test_layer2_reports_the_expected_failures(context: Context) -> None:
    results = {r.name: r for r in run_module(context, "layer2", layer2_bounds)}
    assert results["check_capacity_estimate_reproduced"].passed
    assert results["check_sys_utl_001_analytic_imager_utilisation"].passed
    infeasible = results["check_sys_thr_001_analytic_bound_meets_requirement"]
    assert not infeasible.passed
    assert "blocks" in infeasible.message
    assert not results["check_sys_val_001_invalid_marking_exists"].passed


def test_junit_file_has_one_case_per_check(tmp_path: Path) -> None:
    results = [
        CheckResult(
            layer="layer1",
            module="verification.layer1_model",
            name="check_a",
            uid="SYS-THR-001",
            passed=True,
            message="ok",
            seconds=0.1,
            properties={"MEAN": "3"},
        ),
        CheckResult(
            layer="layer3",
            module="verification.layer3_simulation",
            name="check_b",
            uid="SYS-TAT-001",
            passed=False,
            message="too slow",
            seconds=0.2,
            properties={},
        ),
    ]
    path = tmp_path / "out.pytest.junit.xml"
    write_junit(path, results)
    suite = ElementTree.parse(path).getroot()
    assert suite.get("tests") == "2"
    assert suite.get("failures") == "1"
    cases = suite.findall("testcase")
    assert [case.get("name") for case in cases] == ["check_a", "check_b"]
    assert cases[0].find("properties/property").get("name") == "MEAN"
    assert cases[1].find("failure").get("message") == "too slow"
