"""
Layer 2: analytic capacity bounds from the calcs, without simulation.

Reproduces docs/design/capacity_estimate.md. The expected values below are
copied from that note. Differences are reported, not hidden.
"""

from generator import ir
from generator.analytic import (
    CapacityBounds,
    capacity_bounds,
    expected_visits,
    invalid_rate,
    most_likely_path_seconds,
)
from verification.core import Context

# Busy seconds per cartridge, from docs/design/capacity_estimate.md.
DOC_BUSY_S = {
    "shuttle": 150.0,
    "gantry": 160.0,
    "stations": 1190.0,
    "pneumatics": 232.0,
    "generators": 202.0,
    "blocks": 700.0,
    "imagers": 180.0,
}
# Utilisation at 12 per hour, Base and HighThroughput, as in the note.
DOC_UTILISATION_BASE = {"blocks": 1.17, "stations": 0.99, "imagers": 0.60}
DOC_UTILISATION_HT = {"blocks": 0.78, "stations": 0.99, "imagers": 0.30}
DOC_THROUGHPUT_BASE = 82.0
DOC_THROUGHPUT_HT = 97.0
BUSY_TOLERANCE = 0.02  # relative
UTILISATION_TOLERANCE = 0.01  # absolute, one percentage point
THROUGHPUT_TOLERANCE = 1.0  # samples per shift


def check_capacity_estimate_reproduced(context: Context) -> None:
    """Busy time, utilisation and throughput match the capacity note.

    @relation(SYS-THR-001, scope=function)
    """
    base = capacity_bounds(context.model, "baseSteady")
    high = capacity_bounds(context.model, "highThroughput")
    problems: list[str] = []
    for name, doc in DOC_BUSY_S.items():
        computed = base.resources[name].busy_per_sample_s
        if abs(computed - doc) > BUSY_TOLERANCE * doc:
            problems.append(f"busy {name} {computed:.1f} vs {doc:.1f}")
    for name, doc in DOC_UTILISATION_BASE.items():
        computed = base.resources[name].utilisation
        if abs(computed - doc) > UTILISATION_TOLERANCE:
            problems.append(f"base util {name} {computed:.3f} vs {doc:.2f}")
    for name, doc in DOC_UTILISATION_HT.items():
        computed = high.resources[name].utilisation
        if abs(computed - doc) > UTILISATION_TOLERANCE:
            problems.append(f"HT util {name} {computed:.3f} vs {doc:.2f}")
    if abs(base.throughput_bound_per_shift - DOC_THROUGHPUT_BASE) > (
        THROUGHPUT_TOLERANCE
    ):
        problems.append(
            f"base throughput {base.throughput_bound_per_shift:.1f} vs 82"
        )
    if abs(high.throughput_bound_per_shift - DOC_THROUGHPUT_HT) > (
        THROUGHPUT_TOLERANCE
    ):
        problems.append(
            f"HT throughput {high.throughput_bound_per_shift:.1f} vs 97"
        )
    context.record("BASE_BOUND_PER_SHIFT", base.throughput_bound_per_shift)
    context.record("BASE_BOTTLENECK", base.bottleneck)
    context.record("HT_BOUND_PER_SHIFT", high.throughput_bound_per_shift)
    context.record("HT_BOTTLENECK", high.bottleneck)
    assert not problems, "; ".join(problems)


def _bounds(context: Context, scenario: str) -> CapacityBounds:
    return capacity_bounds(context.model, scenario)


def _threshold(context: Context, uid: str) -> float:
    return next(iter(context.model.requirements[uid].thresholds.values()))


def _throughput_bound(context: Context, scenario: str) -> None:
    bounds = _bounds(context, scenario)
    threshold = _threshold(context, "SYS-THR-001")
    context.record("BOUND_PER_SHIFT", bounds.throughput_bound_per_shift)
    context.record("THRESHOLD", threshold)
    context.record("BOTTLENECK", bounds.bottleneck)
    assert bounds.throughput_bound_per_shift >= threshold, (
        f"infeasible: bound {bounds.throughput_bound_per_shift:.1f} per shift "
        f"is limited by {bounds.bottleneck}; requires {threshold:.0f}"
    )


def check_sys_thr_001_bound_base_steady(context: Context) -> None:
    """Fail early when the analytic bound of baseSteady is below the limit.

    @relation(SYS-THR-001, scope=function)
    """
    _throughput_bound(context, "baseSteady")


def check_sys_thr_001_bound_high_throughput(context: Context) -> None:
    """Fail early when the analytic bound of highThroughput is below the limit.

    @relation(SYS-THR-001, scope=function)
    """
    _throughput_bound(context, "highThroughput")


def _imager_utilisation(context: Context, scenario: str) -> None:
    bounds = _bounds(context, scenario)
    utilisation = bounds.resources["imagers"].utilisation
    limit = _threshold(context, "SYS-UTL-001")
    context.record("OFFERED_UTILISATION", utilisation)
    context.record("THRESHOLD", limit)
    assert utilisation <= limit, f"offered {utilisation:.3f} > {limit}"


def check_sys_utl_001_bound_base_steady(context: Context) -> None:
    """Imager utilisation at the offered load, baseSteady.

    @relation(SYS-UTL-001, scope=function)
    """
    _imager_utilisation(context, "baseSteady")


def check_sys_utl_001_bound_high_throughput(context: Context) -> None:
    """Imager utilisation at the offered load, highThroughput.

    @relation(SYS-UTL-001, scope=function)
    """
    _imager_utilisation(context, "highThroughput")


def _first_result_path(context: Context, scenario: str) -> None:
    seconds = most_likely_path_seconds(
        context.model, context.model.scenario(scenario)
    )
    limit = _threshold(context, "SYS-TAT-001")
    context.record("PATH_SECONDS", seconds)
    context.record("LIMIT_SECONDS", limit)
    assert seconds <= limit, f"path {seconds:.0f} s > limit {limit:.0f} s"


def check_sys_tat_001_path_base_batch(context: Context) -> None:
    """The most likely path with no queueing meets the first-result limit.

    Batch waits count the full batch timeout, because a lone sample waits
    for it. Queueing is not in this bound; the simulation layer covers it.

    @relation(SYS-TAT-001, scope=function)
    """
    _first_result_path(context, "baseBatch")


def check_sys_tat_001_path_high_throughput_batch(context: Context) -> None:
    """The same bound for the high-throughput batch scenario.

    @relation(SYS-TAT-001, scope=function)
    """
    _first_result_path(context, "highThroughputBatch")


def check_sys_val_001_invalid_path_reachable(context: Context) -> None:
    """The readout draw can send a partition to a retest, so invalid results
    can occur. A reachable Bernoulli branch into a retest step is required.

    @relation(SYS-VAL-001, scope=function)
    """
    model = context.model
    scenario = model.scenario("baseSteady")
    visits = expected_visits(model, scenario)
    retest_names = {
        name
        for name, node in model.nodes.items()
        if isinstance(node, ir.Step) and node.retest
    }
    reachable = [
        (name, branch.target)
        for name, node in model.nodes.items()
        if isinstance(node, ir.Decision) and visits[name] > 0
        for branch in node.branches
        if branch.target in retest_names
        and isinstance(branch.guard, ir.BernoulliGuard)
        and ir.evaluate(branch.guard.probability, scenario.values, model.calcs)
        > 0
    ]
    assert reachable, "no reachable invalid draw into a retest"
    context.record("INVALID_DRAW", reachable[0][0])


def _analytic_invalid(context: Context, scenario: str) -> None:
    model = context.model
    rate = invalid_rate(model, model.scenario(scenario))
    limit = _threshold(context, "SYS-VAL-001")
    context.record("ANALYTIC_INVALID_RATE", rate)
    context.record("THRESHOLD", limit)
    assert rate <= limit, f"analytic invalid rate {rate:.3g} > {limit}"


def check_sys_val_001_analytic_invalid_base(context: Context) -> None:
    """Analytic invalid rate, baseSteady: retest probability to the power
    of two, against the 2% limit.

    @relation(SYS-VAL-001, scope=function)
    """
    _analytic_invalid(context, "baseSteady")


def check_sys_val_001_analytic_invalid_high_throughput(
    context: Context,
) -> None:
    """Analytic invalid rate, highThroughput.

    @relation(SYS-VAL-001, scope=function)
    """
    _analytic_invalid(context, "highThroughput")
