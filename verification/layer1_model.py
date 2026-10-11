"""
Layer 1: model completeness and consistency.

Uses the parsed SysML model (StrictDoc parser) and the IR. The Pilot
conformance gate (tools/sysml_conformance.py) runs here too.
"""

import subprocess
import sys
from pathlib import Path

from strictdoc.backend.sysml.model import (
    SysMLAllocate,
    SysMLElement,
    SysMLSatisfy,
    SysMLVerify,
)

from generator import ir
from generator.loader import _walk
from verification.core import Context

REPO_ROOT = Path(__file__).resolve().parent.parent


def _satisfy_and_verify(
    context: Context,
) -> tuple[dict[str, int], dict[str, int]]:
    satisfies: dict[str, int] = {}
    verifies: dict[str, int] = {}
    for member in _walk(context.packages):
        if isinstance(member, SysMLSatisfy):
            satisfies[member.requirement] = (
                satisfies.get(member.requirement, 0) + 1
            )
        if isinstance(member, SysMLVerify):
            verifies[member.requirement] = (
                verifies.get(member.requirement, 0) + 1
            )
    return satisfies, verifies


def _check_requirement(context: Context, uid: str) -> None:
    satisfies, verifies = _satisfy_and_verify(context)
    assert satisfies.get(uid, 0) >= 1, f"{uid} has no satisfy"
    assert verifies.get(uid, 0) >= 1, f"{uid} has no verify"
    for check in context.model.model_checks:
        if check.requirement_uid == uid:
            _assert_model_check(context, check)
    context.record("SATISFY_COUNT", float(satisfies.get(uid, 0)))
    context.record("VERIFY_COUNT", float(verifies.get(uid, 0)))


def _assert_model_check(context: Context, check: ir.ModelCheck) -> None:
    scenario = context.model.scenario(check.scenario)
    requirement = context.model.requirements[check.requirement_uid]
    observed = ir.evaluate(check.observed, scenario.values, context.model.calcs)
    measured = requirement.measured_name
    assert measured is not None, f"{check.requirement_uid} has no measured"
    environment = {**requirement.thresholds, measured: observed}
    holds = ir.evaluate(
        requirement.constraint, environment, context.model.calcs
    )
    context.record("OBSERVED", observed)
    assert holds, (
        f"{check.requirement_uid}: observed {observed:.6g} does not meet "
        f"the constraint with thresholds {dict(requirement.thresholds)}"
    )


def check_model_loads_from_sysml(context: Context) -> None:
    """Every SysML file parses and the IR validates. No requirement UID."""
    context.record("PACKAGES", float(len(context.packages)))
    context.record("SCENARIOS", float(len(context.model.scenarios)))
    context.record(
        "STEPS",
        float(
            sum(
                isinstance(node, ir.Step)
                for node in context.model.nodes.values()
            )
        ),
    )


def check_pilot_conformance(context: Context) -> None:
    """The OMG Pilot Implementation accepts every model file. No UID."""
    del context
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "tools" / "sysml_conformance.py"),
            str(REPO_ROOT / "model"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout[-2000:]


def check_every_step_is_allocated_or_instant(context: Context) -> None:
    """Every step uses a resource, or takes no time (a marker or retest).

    A step with a duration and no allocation takes time without a unit, so
    the capacity model cannot see it. Such steps fail this check.

    @relation(SYS-THR-001, scope=function)
    """
    unallocated = [
        name
        for name, node in context.model.nodes.items()
        if isinstance(node, ir.Step)
        and not node.allocations
        and node.duration.nominal != ir.Literal(0.0)
    ]
    assert not unallocated, f"steps with time but no resource: {unallocated}"


def check_allocations_reference_resources(context: Context) -> None:
    """Every allocation target is a resource of the configuration. No UID."""
    for scenario in context.model.scenarios.values():
        for node in context.model.nodes.values():
            if isinstance(node, ir.Step):
                for target in node.allocations:
                    assert target in scenario.resources, target


def check_isa88_hierarchy(context: Context) -> None:
    """Each allocation starts at the procedure the configuration performs.

    No requirement UID: this is a model structure check.
    """
    performed: set[str] = set()
    allocations: list[SysMLAllocate] = []
    for member in _walk(context.packages):
        if isinstance(member, SysMLElement) and "perform" in member.modifiers:
            performed.add(member.name or "")
        if isinstance(member, SysMLAllocate):
            allocations.append(member)
    assert performed, "no perform found"
    for allocate in allocations:
        head = allocate.source_path[0] if allocate.source_path else ""
        assert head in performed, f"allocation outside the procedure: {head}"


def check_sys_thr_001_has_satisfy_and_verify(context: Context) -> None:
    """@relation(SYS-THR-001, scope=function)
    SYS-THR-001 has a satisfy and a verify. The model check holds.
    """
    _check_requirement(context, "SYS-THR-001")


def check_sys_utl_001_has_satisfy_and_verify(context: Context) -> None:
    """@relation(SYS-UTL-001, scope=function)
    SYS-UTL-001 has a satisfy and a verify.
    """
    _check_requirement(context, "SYS-UTL-001")


def check_sys_tat_001_has_satisfy_and_verify(context: Context) -> None:
    """@relation(SYS-TAT-001, scope=function)
    SYS-TAT-001 has a satisfy and a verify.
    """
    _check_requirement(context, "SYS-TAT-001")


def check_sys_tat_002_has_satisfy_and_verify(context: Context) -> None:
    """@relation(SYS-TAT-002, scope=function)
    SYS-TAT-002 has a satisfy and a verify.
    """
    _check_requirement(context, "SYS-TAT-002")


def check_sys_tat_003_has_satisfy_and_verify(context: Context) -> None:
    """@relation(SYS-TAT-003, scope=function)
    SYS-TAT-003 has a satisfy and a verify.
    """
    _check_requirement(context, "SYS-TAT-003")


def check_sys_val_001_has_satisfy_and_verify(context: Context) -> None:
    """@relation(SYS-VAL-001, scope=function)
    SYS-VAL-001 has a satisfy and a verify.
    """
    _check_requirement(context, "SYS-VAL-001")


def check_sys_val_002_has_satisfy_and_verify(context: Context) -> None:
    """@relation(SYS-VAL-002, scope=function)
    SYS-VAL-002 has a satisfy and a verify. The model check holds.
    """
    _check_requirement(context, "SYS-VAL-002")


def check_sys_drp_001_has_satisfy_and_verify(context: Context) -> None:
    """@relation(SYS-DRP-001, scope=function)
    SYS-DRP-001 has a satisfy and a verify. The model check holds.
    """
    _check_requirement(context, "SYS-DRP-001")


def check_sys_lys_001_has_satisfy_and_verify(context: Context) -> None:
    """@relation(SYS-LYS-001, scope=function)
    SYS-LYS-001 has a satisfy and a verify. The model check holds.
    """
    _check_requirement(context, "SYS-LYS-001")


def check_sys_ch_001_has_satisfy_and_verify(context: Context) -> None:
    """@relation(SYS-CH-001, scope=function)
    SYS-CH-001 has a satisfy and a verify. The model check holds.
    """
    _check_requirement(context, "SYS-CH-001")


def check_sys_ops_001_has_satisfy_and_verify(context: Context) -> None:
    """@relation(SYS-OPS-001, scope=function)
    SYS-OPS-001 has a satisfy and a verify. The model check holds.
    """
    _check_requirement(context, "SYS-OPS-001")


def check_sys_stat_001_has_satisfy_and_verify(context: Context) -> None:
    """@relation(SYS-STAT-001, scope=function)
    SYS-STAT-001 has a satisfy and a verify. The model check holds.
    """
    _check_requirement(context, "SYS-STAT-001")
