"""Deterministic and self-check tests of the Salabim backend."""

import dataclasses

import pytest

from generator import ir
from generator.ir import BatchArrivals, MetricKind
from generator.results import (
    conservation_gap,
    littles_law,
    metric_value,
)
from generator.salabim_backend import RunOptions, simulate
from tests.fixtures.halcyon_ir import build_model

HAND_PATH_SECONDS = 5185.4667
DETERMINISTIC = {"pBubble": 0.0, "pLowDroplets": 0.0}


def _single_sample_model() -> ir.Model:
    model = build_model()
    scenario = dataclasses.replace(
        model.scenarios["baseBatch"],
        arrivals=BatchArrivals(count=1, time_s=0.0),
    )
    return dataclasses.replace(
        model,
        scenarios={**model.scenarios, "single": scenario},
    )


def test_single_sample_matches_hand_calculated_path() -> None:
    result = simulate(
        _single_sample_model(),
        "single",
        RunOptions(seed=1, horizon_s=3 * 3600, overrides=DETERMINISTIC),
    )
    (sample,) = result.samples
    assert sample.outcome == "reported"
    assert sample.finish_s == pytest.approx(HAND_PATH_SECONDS, abs=1e-3)


def test_same_seed_gives_identical_records() -> None:
    model = build_model()
    options = RunOptions(seed=11, horizon_s=2 * 3600)
    first = simulate(model, "baseSteady", options)
    second = simulate(model, "baseSteady", options)
    assert first.samples == second.samples
    assert first.busy == second.busy


def test_conservation_holds_for_a_steady_run() -> None:
    result = simulate(
        build_model(), "baseSteady", RunOptions(seed=2, horizon_s=4 * 3600)
    )
    assert conservation_gap(result) == 0


def test_littles_law_holds_exactly_for_a_drained_stable_run() -> None:
    model = build_model()
    slow = dataclasses.replace(
        model.scenarios["baseSteady"],
        arrivals=ir.PoissonArrivals(rate_per_s=6.0 / 3600.0),
    )
    model = dataclasses.replace(
        model, scenarios={**model.scenarios, "slow": slow}
    )
    result = simulate(
        model,
        "slow",
        RunOptions(seed=5, horizon_s=4 * 3600, drain=True),
    )
    average, product, _ = littles_law(result)
    assert result.in_process == 0
    assert average == pytest.approx(product, rel=1e-9)


def test_utilisation_is_between_zero_and_one() -> None:
    result = simulate(
        build_model(), "baseSteady", RunOptions(seed=3, horizon_s=4 * 3600)
    )
    value = metric_value(result, MetricKind.UTILISATION, "blocks")
    assert 0.0 <= value <= 1.0


def test_forced_invalid_draw_gives_invalid_after_one_retest() -> None:
    """With pLowDroplets = 1 the readout draw is always invalid, so the first
    run and the one retest both end in reflexRetest. The sample is INVALID.
    """
    result = simulate(
        _single_sample_model(),
        "single",
        RunOptions(
            seed=1,
            horizon_s=3 * 3600,
            overrides={"pBubble": 0.0, "pLowDroplets": 1.0},
        ),
    )
    (sample,) = result.samples
    assert sample.outcome == "invalid"
    assert sample.runs == 2


def test_no_invalid_draw_reports_the_sample() -> None:
    result = simulate(
        _single_sample_model(),
        "single",
        RunOptions(
            seed=1,
            horizon_s=3 * 3600,
            overrides={"pBubble": 0.0, "pLowDroplets": 0.0},
        ),
    )
    (sample,) = result.samples
    assert sample.outcome == "reported"
    assert sample.runs == 1
