"""
Layer 4: simulator self-verification.

These checks test the simulator, not the instrument. Each one supports the
requirement it is linked to, because a wrong simulator would make that
requirement's result wrong.
"""

import dataclasses
import math

from generator import ir
from generator.analytic import capacity_bounds
from generator.ir import BatchArrivals, PoissonArrivals
from generator.results import conservation_gap, littles_law, utilisation
from verification.core import Context

# Hand-calculated path of one sample through an empty instrument, from
# docs/design/capacity_estimate.md (seconds):
#   intake: scan 10, transfer 30, prime 28.8, plus the batch timeout of 600
#     for the thermal step below is counted in amplification only.
#   extraction: 1190 (the elution branch, 260 s, is longer than masterMix)
#   partitioning: meter 30, generate 166.67, transfer 30
#   amplification: batch timeout 600, thermal run 2800, transfer 30
#   readout: imaging 180, analysis 60, transfer 30
HAND_PATH_S = (
    10.0 + 30.0 + 28.8
    + 1190.0
    + 30.0 + 166.6667 + 30.0
    + 600.0 + 2800.0 + 30.0
    + 180.0 + 60.0 + 30.0
)  # fmt: skip
PATH_TOLERANCE_S = 0.5
STABLE_RATE_PER_H = 6.0
UTILISATION_TOLERANCE = 0.03


def _single_sample_model(context: Context) -> ir.Model:
    """The base scenario with one sample and no random branches."""
    scenario = dataclasses.replace(
        context.model.scenarios["baseBatch"],
        arrivals=BatchArrivals(count=1, time_s=0.0),
        values={
            **context.model.scenarios["baseBatch"].values,
            "pBubble": 0.0,
            "pLowDroplets": 0.0,
        },
    )
    return dataclasses.replace(
        context.model,
        scenarios={**context.model.scenarios, "single": scenario},
    )


def _stable_model(context: Context) -> ir.Model:
    """The base scenario at a load the two blocks carry without queueing."""
    scenario = dataclasses.replace(
        context.model.scenarios["baseSteady"],
        arrivals=PoissonArrivals(rate_per_s=STABLE_RATE_PER_H / 3600.0),
    )
    return dataclasses.replace(
        context.model,
        scenarios={**context.model.scenarios, "stable": scenario},
    )


def check_sim_conservation(context: Context) -> None:
    """Arrivals equal outcomes plus samples still in process.

    @relation(SYS-THR-001, scope=function)
    """
    result = context.run("baseSteady", 4 * 3600.0, 0)
    gap = conservation_gap(result)
    context.record("ARRIVALS", float(result.arrivals_total))
    context.record("GAP", float(gap))
    assert gap == 0, f"conservation gap {gap}"


def check_sim_littles_law(context: Context) -> None:
    """Little's law holds for a drained, stable run.

    With no samples left in process, the time integral of the number in the
    system equals the sum of sojourn times, so L = lambda W is exact.

    @relation(SYS-THR-001, scope=function)
    """
    result = context.run(
        "stable",
        4 * 3600.0,
        0,
        drain=True,
        model=_stable_model(context),
    )
    average, product, _ = littles_law(result)
    context.record("L_AVERAGE", average)
    context.record("LAMBDA_W", product)
    assert result.in_process == 0, "run did not drain"
    assert math.isclose(average, product, rel_tol=1e-9), (
        f"L {average:.9g} differs from lambda W {product:.9g}"
    )


def check_sim_fixed_seed_reproducibility(context: Context) -> None:
    """The same seed gives the same records.

    @relation(SYS-THR-001, scope=function)
    """
    first = context.run("baseSteady", 2 * 3600.0, 3, model=context.model)
    second = context.run("baseSteady", 2 * 3600.0, 3, model=context.model)
    assert first.samples == second.samples, "records differ for one seed"
    assert first.busy == second.busy, "busy intervals differ for one seed"


def check_sim_single_sample_path_time(context: Context) -> None:
    """One sample through an empty instrument matches the hand path.

    @relation(SYS-TAT-001, scope=function)
    """
    result = context.run(
        "single",
        3 * 3600.0,
        0,
        model=_single_sample_model(context),
    )
    (sample,) = result.samples
    assert sample.finish_s is not None, "the sample did not finish"
    context.record("SIMULATED_S", sample.finish_s)
    context.record("HAND_S", HAND_PATH_S)
    assert abs(sample.finish_s - HAND_PATH_S) <= PATH_TOLERANCE_S, (
        f"simulated {sample.finish_s:.2f} s, hand {HAND_PATH_S:.2f} s"
    )


def check_sim_utilisation_matches_analytic(context: Context) -> None:
    """Imager utilisation at a stable load matches the analytic value.

    @relation(SYS-UTL-001, scope=function)
    """
    model = _stable_model(context)
    result = context.run("stable", 8 * 3600.0, 1, model=model)
    simulated = utilisation(result, "imagers")
    analytic = capacity_bounds(model, "stable").resources["imagers"]
    context.record("SIMULATED", simulated)
    context.record("ANALYTIC", analytic.utilisation)
    assert abs(simulated - analytic.utilisation) <= UTILISATION_TOLERANCE, (
        f"simulated {simulated:.3f} vs analytic {analytic.utilisation:.3f}"
    )
