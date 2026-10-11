"""
Layer 2: analytic capacity bounds from the calcs, without simulation.

Reproduces docs/design/capacity_estimate.md. The expected values below are
copied from that note. Differences are reported, not hidden.
"""

from generator.analytic import capacity_bounds, most_likely_path_seconds
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


def check_sys_thr_001_analytic_bound_meets_requirement(
    context: Context,
) -> None:
    """Fail early when the analytic upper bound is below the requirement.

    @relation(SYS-THR-001, scope=function)
    """
    bounds = capacity_bounds(context.model, "baseSteady")
    requirement = context.model.requirements["SYS-THR-001"]
    threshold = requirement.thresholds["requiredSamplesPerShift"]
    context.record("BOUND_PER_SHIFT", bounds.throughput_bound_per_shift)
    context.record("THRESHOLD", threshold)
    assert bounds.throughput_bound_per_shift >= threshold, (
        f"infeasible: bound {bounds.throughput_bound_per_shift:.1f} per shift "
        f"is limited by {bounds.bottleneck}; requires {threshold:.0f}"
    )


def check_sys_utl_001_analytic_imager_utilisation(context: Context) -> None:
    """Imager utilisation at the offered load is within the limit.

    @relation(SYS-UTL-001, scope=function)
    """
    bounds = capacity_bounds(context.model, "baseSteady")
    utilisation = bounds.resources["imagers"].utilisation
    requirement = context.model.requirements["SYS-UTL-001"]
    limit = requirement.thresholds["requiredImagerUtilisation"]
    context.record("OFFERED_UTILISATION", utilisation)
    assert utilisation <= limit, f"offered {utilisation:.3f} > {limit}"


def check_sys_tat_001_most_likely_path_time(context: Context) -> None:
    """The most likely path with no queueing meets the first-result limit.

    Batch waits count the full batch timeout, because a lone sample waits
    for it. Queueing is not in this bound; the simulation layer covers it.

    @relation(SYS-TAT-001, scope=function)
    """
    scenario = context.model.scenario("baseBatch")
    seconds = most_likely_path_seconds(context.model, scenario)
    limit = context.model.requirements["SYS-TAT-001"].thresholds[
        "requiredTimeToFirstResult"
    ]
    context.record("PATH_SECONDS", seconds)
    context.record("LIMIT_SECONDS", limit)
    assert seconds <= limit, f"path {seconds:.0f} s > limit {limit:.0f} s"


def check_sys_val_001_invalid_marking_exists(context: Context) -> None:
    """Some step must mark a sample invalid, or the invalid rate is zero.

    The model has no assignment that sets sample.invalid, so SYS-VAL-001
    would pass without being exercised. This check reports that gap.

    @relation(SYS-VAL-001, scope=function)
    """
    marking = [
        name
        for name, node in context.model.nodes.items()
        if getattr(node, "assignments", ())
    ]
    assert marking, "no step marks a sample invalid; the rate is untested"
