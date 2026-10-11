"""
Engine-neutral results of one simulation replication, and the metrics that
the verification layers read.

A backend produces a RunResult. Everything else (metrics, Little's law,
conservation) works on RunResult only, so a second backend can reuse it.
"""

import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from generator.ir import MetricKind


class Outcome:
    """Terminal state of a sample. Plain strings keep records printable."""

    REPORTED = "reported"
    INVALID = "invalid"
    ABORTED = "aborted"


@dataclass(frozen=True)
class SampleRecord:
    sample_id: int
    priority: int
    arrival_s: float
    finish_s: float | None
    outcome: str | None
    runs: int


@dataclass(frozen=True)
class BusyInterval:
    resource: str
    start_s: float
    end_s: float
    sample_id: int


@dataclass(frozen=True)
class TraceEvent:
    sample_id: int
    step: str
    resources: tuple[str, ...]
    start_s: float
    end_s: float


@dataclass(frozen=True)
class RunResult:
    scenario: str
    seed: int
    warm_up_s: float
    end_s: float
    capacities: Mapping[str, int]
    samples: tuple[SampleRecord, ...]
    busy: tuple[BusyInterval, ...]
    queue_mean: Mapping[str, float]
    trace: tuple[TraceEvent, ...] = ()
    arrivals_total: int = 0
    in_process: int = 0
    counters: Mapping[str, int] = field(default_factory=dict)

    @property
    def window_s(self) -> float:
        return self.end_s - self.warm_up_s

    def finished_in_window(self) -> Sequence[SampleRecord]:
        return [
            sample
            for sample in self.samples
            if sample.finish_s is not None
            and self.warm_up_s < sample.finish_s <= self.end_s
        ]


def metric_value(
    result: RunResult,
    metric: MetricKind,
    resource: str | None = None,
) -> float:
    """Value of one metric for one replication."""
    finished = result.finished_in_window()
    if metric is MetricKind.COMPLETED_PER_SHIFT:
        reported = [s for s in finished if s.outcome == Outcome.REPORTED]
        return len(reported) * 8.0 * 3600.0 / result.window_s
    if metric is MetricKind.TIME_TO_FIRST_RESULT:
        reported = [s for s in result.samples if s.outcome == Outcome.REPORTED]
        if not reported:
            return float("inf")
        return min(
            s.finish_s - s.arrival_s for s in reported if s.finish_s is not None
        )
    if metric is MetricKind.MEAN_TURNAROUND:
        return _mean_turnaround(finished, stat=None)
    if metric is MetricKind.MEAN_STAT_TURNAROUND:
        return _mean_turnaround(finished, stat=True)
    if metric is MetricKind.INVALID_RATE:
        if not finished:
            return 0.0
        invalid = [s for s in finished if s.outcome == Outcome.INVALID]
        return len(invalid) / len(finished)
    if metric is MetricKind.UTILISATION:
        if resource is None:
            raise ValueError("utilisation needs a resource")
        return utilisation(result, resource)
    raise ValueError(f"unknown metric: {metric}")


def _mean_turnaround(
    finished: Sequence[SampleRecord],
    stat: bool | None,
) -> float:
    selected = [
        s
        for s in finished
        if s.outcome == Outcome.REPORTED
        and (stat is None or (s.priority > 0) == stat)
    ]
    if not selected:
        return float("inf")
    return statistics.fmean(
        s.finish_s - s.arrival_s for s in selected if s.finish_s is not None
    )


def utilisation(result: RunResult, resource: str) -> float:
    """Busy unit-time inside the window, divided by capacity times window."""
    capacity = result.capacities[resource]
    busy = 0.0
    for interval in result.busy:
        if interval.resource != resource:
            continue
        start = max(interval.start_s, result.warm_up_s)
        end = min(interval.end_s, result.end_s)
        if end > start:
            busy += end - start
    return busy / (capacity * result.window_s)


def utilisation_by_resource(result: RunResult) -> dict[str, float]:
    return {name: utilisation(result, name) for name in result.capacities}


def conservation_gap(result: RunResult) -> int:
    """Arrivals minus outcomes minus samples still in process. Zero when ok."""
    outcomes = sum(1 for s in result.samples if s.outcome is not None)
    return result.arrivals_total - outcomes - result.in_process


def littles_law(result: RunResult) -> tuple[float, float, float]:
    """
    Return (L, lambda * W, lambda) over the measurement window.

    L is the time average of samples in the system inside the window. lambda
    is the arrival rate of samples that arrive in the window. W is the mean
    sojourn of the samples that finish in the window. The window is long
    enough for steady state; the caller sets the tolerance.
    """
    window = result.window_s
    area = 0.0
    for sample in result.samples:
        end = sample.finish_s if sample.finish_s is not None else result.end_s
        start = max(sample.arrival_s, result.warm_up_s)
        stop = min(end, result.end_s)
        if stop > start:
            area += stop - start
    average_in_system = area / window
    arrivals_in_window = [
        s
        for s in result.samples
        if result.warm_up_s <= s.arrival_s < result.end_s
    ]
    arrival_rate = len(arrivals_in_window) / window
    finished = result.finished_in_window()
    if not finished:
        return average_in_system, 0.0, arrival_rate
    mean_sojourn = statistics.fmean(
        s.finish_s - s.arrival_s for s in finished if s.finish_s is not None
    )
    # Throughput of finished samples, multiplied by the mean sojourn time.
    departure_rate = len(finished) / window
    return average_in_system, departure_rate * mean_sojourn, arrival_rate
