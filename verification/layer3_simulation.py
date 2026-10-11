"""
Layer 3: simulation-based verification of the SYS requirements.

Every SimulationVerification in the model is run: N replications with fixed
seeds, the mean and a 95% confidence interval. The requirement passes only if
its own `require constraint`, evaluated with the confidence bound in the
direction of the constraint (lower for >=, upper for <=), holds.

Each case has its own check function, so each JUnit testcase has a unique
name and StrictDoc links it to the requirement. The case id is in the CASE
property. A +/-20% sweep on all step durations reports the margin.
"""

import math

from generator import ir
from generator.ir import SimulationVerification
from generator.results import metric_value
from verification.core import Context, Interval, confidence_interval

SENSITIVITY_REPLICATIONS = 5
SENSITIVITY_SCALES = (0.8, 1.2)


def _verification(context: Context, case_id: str) -> SimulationVerification:
    for verification in context.model.verifications:
        if verification.case_id == case_id:
            return verification
    raise KeyError(f"no simulation verification with case id {case_id}")


def _values(
    context: Context,
    verification: SimulationVerification,
    replications: int,
    duration_scale: float,
) -> list[float]:
    values: list[float] = []
    for index in range(replications):
        result = context.run(
            verification.scenario,
            verification.horizon_s,
            index,
            duration_scale=duration_scale,
        )
        values.append(
            metric_value(result, verification.metric, verification.resource)
        )
    return values


def _bound(constraint: ir.Expr, interval: Interval) -> float:
    if isinstance(constraint, ir.Binary) and constraint.operator in (">=", ">"):
        return interval.lower
    if isinstance(constraint, ir.Binary) and constraint.operator in ("<=", "<"):
        return interval.upper
    raise ValueError("the constraint is not an inequality")


def _interval(values: list[float], confidence: float) -> Interval:
    if any(math.isinf(value) for value in values):
        return Interval(math.inf, math.inf, math.inf, math.inf)
    return confidence_interval(values, confidence)


def _margin(constraint: ir.Expr, bound: float, threshold: float) -> float:
    """Relative margin: positive when the requirement holds."""
    assert isinstance(constraint, ir.Binary)
    if constraint.operator in (">=", ">"):
        return (bound - threshold) / abs(threshold)
    return (threshold - bound) / abs(threshold)


def _holds(context: Context, uid: str, bound: float) -> bool:
    requirement = context.model.requirements[uid]
    assert requirement.measured_name is not None
    environment = {
        **requirement.thresholds,
        requirement.measured_name: bound,
    }
    return bool(
        ir.evaluate(requirement.constraint, environment, context.model.calcs)
    )


def _threshold(context: Context, uid: str) -> float:
    thresholds = context.model.requirements[uid].thresholds
    return next(iter(thresholds.values()))


def _simulated_case(context: Context, case_id: str) -> None:
    verification = _verification(context, case_id)
    uid = verification.requirement_uid
    requirement = context.model.requirements[uid]
    replications = context.replications(verification.replications)
    values = _values(context, verification, replications, 1.0)
    interval = _interval(values, verification.confidence)
    bound = _bound(requirement.constraint, interval)
    threshold = _threshold(context, uid)
    holds = _holds(context, uid, bound)
    context.record("CASE", case_id)
    context.record("SCENARIO", verification.scenario)
    context.record("N", float(replications))
    context.record("MEAN", interval.mean)
    context.record("CI_LOWER", interval.lower)
    context.record("CI_UPPER", interval.upper)
    context.record("BOUND", bound)
    context.record("THRESHOLD", threshold)
    context.record("MARGIN", _margin(requirement.constraint, bound, threshold))
    for scale in SENSITIVITY_SCALES:
        label = "MINUS20" if scale < 1 else "PLUS20"
        scaled = _values(context, verification, SENSITIVITY_REPLICATIONS, scale)
        scaled_interval = _interval(scaled, verification.confidence)
        scaled_bound = _bound(requirement.constraint, scaled_interval)
        context.record(f"SENS_{label}_MEAN", scaled_interval.mean)
        context.record(
            f"SENS_{label}_MARGIN",
            _margin(requirement.constraint, scaled_bound, threshold),
        )
    assert holds, (
        f"{uid} {case_id}: bound {bound:.6g} does not meet the threshold "
        f"{threshold:.6g} (mean {interval.mean:.6g}, 95% CI "
        f"[{interval.lower:.6g}, {interval.upper:.6g}])"
    )


def check_sys_thr_001_ver_sys_thr_001(context: Context) -> None:
    """@relation(SYS-THR-001, scope=function)
    Completed samples per shift, baseSteady. Case verSysThr001.
    """
    _simulated_case(context, "verSysThr001")


def check_sys_thr_001_ver_thr_001_ht(context: Context) -> None:
    """@relation(SYS-THR-001, scope=function)
    Completed samples per shift, highThroughput. Case VER-THR-001-HT.
    """
    _simulated_case(context, "VER-THR-001-HT")


def check_sys_utl_001_ver_sys_utl_001(context: Context) -> None:
    """@relation(SYS-UTL-001, scope=function)
    Mean imager utilisation, baseSteady. Case verSysUtl001.
    """
    _simulated_case(context, "verSysUtl001")


def check_sys_utl_001_ver_utl_001_ht(context: Context) -> None:
    """@relation(SYS-UTL-001, scope=function)
    Mean imager utilisation, highThroughput. Case VER-UTL-001-HT.
    """
    _simulated_case(context, "VER-UTL-001-HT")


def check_sys_tat_001_ver_sys_tat_001(context: Context) -> None:
    """@relation(SYS-TAT-001, scope=function)
    Time to first result of a batch, baseBatch. Case verSysTat001.
    """
    _simulated_case(context, "verSysTat001")


def check_sys_tat_001_ver_tat_001_ht(context: Context) -> None:
    """@relation(SYS-TAT-001, scope=function)
    Time to first result of a batch, highThroughputBatch. Case VER-TAT-001-HT.
    """
    _simulated_case(context, "VER-TAT-001-HT")


def check_sys_tat_002_ver_sys_tat_002(context: Context) -> None:
    """@relation(SYS-TAT-002, scope=function)
    Mean turnaround, baseSteady. Case verSysTat002.
    """
    _simulated_case(context, "verSysTat002")


def check_sys_tat_002_ver_tat_002_ht(context: Context) -> None:
    """@relation(SYS-TAT-002, scope=function)
    Mean turnaround, highThroughput. Case VER-TAT-002-HT.
    """
    _simulated_case(context, "VER-TAT-002-HT")


def check_sys_tat_003_ver_sys_tat_003(context: Context) -> None:
    """@relation(SYS-TAT-003, scope=function)
    Mean STAT turnaround, baseSteady. Case verSysTat003.
    """
    _simulated_case(context, "verSysTat003")


def check_sys_val_001_ver_sys_val_001(context: Context) -> None:
    """@relation(SYS-VAL-001, scope=function)
    Invalid results after reflex retesting, baseSteady. Case verSysVal001.
    """
    _simulated_case(context, "verSysVal001")
