"""
Layer 3: simulation-based verification of the SYS requirements.

For each SimulationVerification in the model: N replications with fixed
seeds, the mean and a 95% confidence interval. The requirement passes only if
its own `require constraint`, evaluated with the confidence bound in the
direction of the constraint (lower for >=, upper for <=), holds.

A +/-20% sweep on all step durations reports the margin at each scale.
"""

import math

from generator import ir
from generator.ir import SimulationVerification
from generator.results import metric_value
from verification.core import Context, Interval, confidence_interval

SENSITIVITY_REPLICATIONS = 5
SENSITIVITY_SCALES = (0.8, 1.2)


def _verification(context: Context, uid: str) -> SimulationVerification:
    for verification in context.model.verifications:
        if verification.requirement_uid == uid:
            return verification
    raise KeyError(f"no simulation verification for {uid}")


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


def _simulated_case(context: Context, uid: str) -> None:
    verification = _verification(context, uid)
    requirement = context.model.requirements[uid]
    replications = context.replications(verification.replications)
    values = _values(context, verification, replications, 1.0)
    interval = _interval(values, verification.confidence)
    bound = _bound(requirement.constraint, interval)
    threshold = _threshold(context, uid)
    holds = _holds(context, uid, bound)
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
        f"{uid}: bound {bound:.6g} does not meet the threshold {threshold:.6g} "
        f"(mean {interval.mean:.6g}, 95% CI "
        f"[{interval.lower:.6g}, {interval.upper:.6g}])"
    )


def check_sys_thr_001_simulated_throughput(context: Context) -> None:
    """@relation(SYS-THR-001, scope=function)
    Completed samples per 8-hour shift, base scenario, nominal load.
    """
    _simulated_case(context, "SYS-THR-001")


def check_sys_utl_001_simulated_imager_utilisation(context: Context) -> None:
    """@relation(SYS-UTL-001, scope=function)
    Mean imager utilisation, base scenario, nominal load.
    """
    _simulated_case(context, "SYS-UTL-001")


def check_sys_tat_001_simulated_first_result(context: Context) -> None:
    """@relation(SYS-TAT-001, scope=function)
    Time to the first result of a batch of 24 loaded at shift start.
    """
    _simulated_case(context, "SYS-TAT-001")


def check_sys_tat_002_simulated_mean_turnaround(context: Context) -> None:
    """@relation(SYS-TAT-002, scope=function)
    Mean turnaround of reported samples, base scenario, nominal load.
    """
    _simulated_case(context, "SYS-TAT-002")


def check_sys_tat_003_simulated_stat_turnaround(context: Context) -> None:
    """@relation(SYS-TAT-003, scope=function)
    Mean turnaround of STAT samples, base scenario, nominal load.
    """
    _simulated_case(context, "SYS-TAT-003")


def check_sys_val_001_simulated_invalid_rate(context: Context) -> None:
    """@relation(SYS-VAL-001, scope=function)
    Share of invalid results after reflex retesting, nominal load.
    """
    _simulated_case(context, "SYS-VAL-001")
