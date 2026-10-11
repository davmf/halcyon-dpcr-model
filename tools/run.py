"""
Command line entry point of the Halcyon dPCR-24 model.

Usage (from the repository root, with .venv/bin/python):

    tools/run.py check                      layer 1 (model) checks
    tools/run.py bounds                     layer 2 analytic bounds
    tools/run.py simulate --scenario X      replications with 95% CIs
    tools/run.py verify                     all layers, JUnit and summary
    tools/run.py plots                      Gantt, utilisation, histogram
    tools/run.py animate --scenario X --video build/media/x.mp4
    tools/run.py animate --scenario X --live
    tools/run.py strictdoc                  export HTML with the JUnit results

Results go to build/. The generator and verification layers do not depend on
this file.
"""

import argparse
import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from generator.analytic import capacity_bounds
from generator.ir import MetricKind
from generator.results import (
    conservation_gap,
    metric_value,
    utilisation_by_resource,
)
from verification.core import (
    Context,
    run_module,
    write_junit,
)

MODEL_DIR = REPO_ROOT / "model"
RESULTS_DIR = REPO_ROOT / "build" / "results"
JUNIT_PATH = RESULTS_DIR / "halcyon-verification.pytest.junit.xml"
LAYERS = (
    ("layer1", "verification.layer1_model"),
    ("layer2", "verification.layer2_bounds"),
    ("layer3", "verification.layer3_simulation"),
    ("layer4", "verification.layer4_self"),
)


def _print_table(rows: list[tuple[str, ...]]) -> None:
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    for row in rows:
        print("  ".join(cell.ljust(width) for cell, width in zip(row, widths)))


def cmd_check(context: Context) -> int:
    module = importlib.import_module("verification.layer1_model")
    results = run_module(context, "layer1", module)
    _print_table(
        [
            ("PASS" if r.passed else "FAIL", r.uid or "-", r.name, r.message)
            for r in results
        ]
    )
    return 0 if all(r.passed for r in results) else 1


def cmd_bounds(context: Context) -> int:
    for name, scenario in sorted(context.model.scenarios.items()):
        try:
            bounds = capacity_bounds(context.model, name)
        except TypeError:
            continue
        print(
            f"{name}: offered {bounds.arrival_rate_per_h:.1f}/h, "
            f"bound {bounds.throughput_bound_per_shift:.1f} per shift, "
            f"bottleneck {bounds.bottleneck}"
        )
        rows = [("resource", "busy s/sample", "utilisation", "bound/shift")]
        for resource in bounds.resources.values():
            rows.append(
                (
                    resource.name,
                    f"{resource.busy_per_sample_s:.1f}",
                    f"{resource.utilisation * 100:.1f}%",
                    f"{resource.throughput_per_shift:.1f}",
                )
            )
        _print_table(rows)
        del scenario
    return 0


def cmd_simulate(context: Context, args: argparse.Namespace) -> int:
    from verification.core import confidence_interval

    scenario = context.model.scenario(args.scenario)
    horizon = args.horizon_h * 3600.0
    runs = [
        context.run(args.scenario, horizon, index)
        for index in range(args.replications)
    ]
    print(
        f"scenario {args.scenario}: {args.replications} replications, "
        f"{args.horizon_h:g} h horizon after "
        f"{scenario.warm_up_s / 3600:g} h warm-up"
    )
    rows = [("metric", "mean", "95% CI")]
    for metric in (
        MetricKind.COMPLETED_PER_SHIFT,
        MetricKind.TIME_TO_FIRST_RESULT,
        MetricKind.MEAN_TURNAROUND,
        MetricKind.MEAN_STAT_TURNAROUND,
        MetricKind.INVALID_RATE,
    ):
        values = [metric_value(run, metric) for run in runs]
        interval = confidence_interval(values, 0.95)
        rows.append(
            (
                metric.value,
                f"{interval.mean:.4g}",
                f"[{interval.lower:.4g}, {interval.upper:.4g}]",
            )
        )
    _print_table(rows)
    last = runs[-1]
    print(f"utilisation (last replication, seed {last.seed}):")
    for name, value in utilisation_by_resource(last).items():
        print(f"  {name}: {value * 100:.1f}%")
    print(f"conservation gap: {conservation_gap(last)}")
    return 0


def cmd_verify(context: Context) -> int:
    all_results = []
    for layer, module_name in LAYERS:
        module = importlib.import_module(module_name)
        all_results += run_module(context, layer, module)
    write_junit(JUNIT_PATH, all_results)
    rows = [("layer", "result", "UID", "check", "bound", "threshold", "detail")]
    for result in all_results:
        bound = result.properties.get("BOUND", "")
        threshold = result.properties.get("THRESHOLD", "")
        rows.append(
            (
                result.layer,
                "PASS" if result.passed else "FAIL",
                result.uid or "-",
                result.name,
                bound,
                threshold,
                "" if result.passed else result.message,
            )
        )
    _print_table(rows)
    failed = sum(1 for r in all_results if not r.passed)
    print(f"{len(all_results) - failed} passed, {failed} failed")
    print(f"JUnit: {JUNIT_PATH.relative_to(REPO_ROOT)}")
    return 0 if failed == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    sub.add_parser("bounds")
    simulate = sub.add_parser("simulate")
    simulate.add_argument("--scenario", required=True)
    simulate.add_argument("--replications", type=int, default=5)
    simulate.add_argument("--horizon-h", type=float, default=8.0)
    sub.add_parser("verify")
    args = parser.parse_args(argv)
    context = Context(MODEL_DIR)
    if args.command == "check":
        return cmd_check(context)
    if args.command == "bounds":
        return cmd_bounds(context)
    if args.command == "simulate":
        return cmd_simulate(context, args)
    if args.command == "verify":
        return cmd_verify(context)
    raise AssertionError(args.command)


if __name__ == "__main__":
    sys.exit(main())
