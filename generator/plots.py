"""
Plots of simulation results (matplotlib, headless Agg backend).

- gantt_chart: one row per cartridge, the steps it spent time in.
- utilisation_bars: utilisation per resource, one series.
- turnaround_histogram: turnaround of reported samples.
- scenario_comparison: throughput per shift per scenario, with the
  requirement threshold drawn as a reference line.

Colour follows the entity, not its rank. Resource groups use the first
three categorical slots of the reference palette (validated in light mode,
see docs/design/working_notes.md). Every chart with two or more series has a
legend and direct value labels, because two of the slots sit below 3:1
contrast on the light surface.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from generator.results import (
    Outcome,
    RunResult,
    utilisation_by_resource,
)

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
NEUTRAL = "#9a9892"
SERIES_BLUE = "#2a78d6"
SERIES_ORANGE = "#eb6834"
SERIES_AQUA = "#1baf7a"

GROUP_COLOURS = {
    "stations": SERIES_BLUE,
    "blocks": SERIES_ORANGE,
    "imagers": SERIES_AQUA,
}


def _style(axes: plt.Axes) -> None:
    axes.set_facecolor(SURFACE)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color(NEUTRAL)
    axes.tick_params(colors=TEXT_SECONDARY, labelsize=9)
    axes.grid(axis="x", color=GRID, linewidth=0.8)
    axes.set_axisbelow(True)


def _save(figure: plt.Figure, path: Path) -> list[Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    written = []
    for suffix in (".png", ".svg"):
        target = path.with_suffix(suffix)
        figure.savefig(target, dpi=150, facecolor=SURFACE)
        written.append(target)
    plt.close(figure)
    return written


def gantt_chart(
    result: RunResult,
    path: Path,
    max_cartridges: int = 12,
) -> list[Path]:
    """One row per cartridge. Bars are steps, coloured by resource group."""
    if not result.trace:
        raise ValueError("the run has no trace; simulate with record_trace")
    sample_ids = sorted({event.sample_id for event in result.trace})
    sample_ids = sample_ids[:max_cartridges]
    row_of = {sample: row for row, sample in enumerate(sample_ids)}
    figure, axes = plt.subplots(figsize=(10, 0.45 * len(sample_ids) + 1.6))
    _style(axes)
    used: dict[str, str] = {}
    for event in result.trace:
        if event.sample_id not in row_of:
            continue
        group = next(
            (name for name in event.resources if name in GROUP_COLOURS),
            "other",
        )
        colour = GROUP_COLOURS.get(group, NEUTRAL)
        used[group] = colour
        axes.barh(
            row_of[event.sample_id],
            (event.end_s - event.start_s) / 60.0,
            left=event.start_s / 60.0,
            height=0.6,
            color=colour,
            edgecolor=SURFACE,
            linewidth=0.5,
        )
    axes.set_yticks(range(len(sample_ids)))
    axes.set_yticklabels([f"#{sample}" for sample in sample_ids])
    axes.invert_yaxis()
    axes.set_xlabel("time (min)", color=TEXT_SECONDARY)
    axes.set_title(
        f"Cartridges, {result.scenario}, seed {result.seed}",
        color=TEXT_PRIMARY,
        loc="left",
    )
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=colour) for colour in used.values()
    ]
    axes.legend(
        handles,
        list(used),
        frameon=False,
        fontsize=8,
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
    )
    figure.tight_layout()
    return _save(figure, path)


def utilisation_bars(result: RunResult, path: Path) -> list[Path]:
    """Utilisation per resource over the measurement window."""
    values = utilisation_by_resource(result)
    names = list(values)
    figure, axes = plt.subplots(figsize=(8, 0.4 * len(names) + 1.4))
    _style(axes)
    bars = axes.barh(
        names,
        [values[name] * 100 for name in names],
        height=0.6,
        color=SERIES_BLUE,
    )
    for bar, name in zip(bars, names):
        axes.text(
            bar.get_width() + 1,
            bar.get_y() + bar.get_height() / 2,
            f"{values[name] * 100:.1f}%",
            va="center",
            fontsize=8,
            color=TEXT_PRIMARY,
        )
    axes.invert_yaxis()
    axes.set_xlim(0, max(105.0, max(values.values()) * 100 + 12))
    axes.set_xlabel("utilisation (%)", color=TEXT_SECONDARY)
    axes.set_title(
        f"Utilisation, {result.scenario}, seed {result.seed}",
        color=TEXT_PRIMARY,
        loc="left",
    )
    figure.tight_layout()
    return _save(figure, path)


def turnaround_histogram(result: RunResult, path: Path) -> list[Path]:
    """Histogram of turnaround (arrival to report), reported samples only."""
    minutes = [
        (sample.finish_s - sample.arrival_s) / 60.0
        for sample in result.samples
        if sample.outcome == Outcome.REPORTED and sample.finish_s is not None
    ]
    figure, axes = plt.subplots(figsize=(8, 4))
    _style(axes)
    axes.grid(axis="y", color=GRID, linewidth=0.8)
    axes.grid(axis="x", visible=False)
    if minutes:
        axes.hist(minutes, bins=20, color=SERIES_BLUE, edgecolor=SURFACE)
    axes.set_xlabel("turnaround (min)", color=TEXT_SECONDARY)
    axes.set_ylabel("reported samples", color=TEXT_SECONDARY)
    axes.set_title(
        f"Turnaround, {result.scenario}, n = {len(minutes)}",
        color=TEXT_PRIMARY,
        loc="left",
    )
    figure.tight_layout()
    return _save(figure, path)


def scenario_comparison(
    throughput: dict[str, float],
    threshold: float,
    path: Path,
) -> list[Path]:
    """Samples per shift per scenario, with the requirement as a line."""
    names = list(throughput)
    figure, axes = plt.subplots(figsize=(8, 4))
    _style(axes)
    axes.grid(axis="x", visible=False)
    axes.grid(axis="y", color=GRID, linewidth=0.8)
    bars = axes.bar(
        names,
        [throughput[name] for name in names],
        width=0.55,
        color=SERIES_BLUE,
    )
    for bar, name in zip(bars, names):
        axes.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1.5,
            f"{throughput[name]:.1f}",
            ha="center",
            fontsize=9,
            color=TEXT_PRIMARY,
        )
    axes.axhline(threshold, color=NEUTRAL, linestyle="--", linewidth=1)
    axes.text(
        len(names) - 0.5,
        threshold + 1.5,
        f"SYS-THR-001: {threshold:.0f} per shift",
        ha="right",
        fontsize=8,
        color=TEXT_SECONDARY,
    )
    axes.set_ylabel("samples per 8-hour shift", color=TEXT_SECONDARY)
    axes.set_title(
        "Throughput per shift by scenario",
        color=TEXT_PRIMARY,
        loc="left",
    )
    figure.tight_layout()
    return _save(figure, path)
