"""
Verification framework: context, check runner, JUnit writer, statistics.

A check is a function `check_<name>(context) -> None` in a layer module. It
passes when it returns, and fails on AssertionError. Its docstring carries a
`@relation(<UID>, scope=function)` marker, so StrictDoc links the JUnit
result to the requirement. The JUnit testcase names are the function names,
and the classname is the module path, which StrictDoc resolves to the source
file (see docs/design/working_notes.md, "StrictDoc links").
"""

import dataclasses
import re
import statistics
import time
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from xml.etree import ElementTree

from generator import ir
from generator.loader import load_model, parse_model
from generator.results import RunResult
from generator.salabim_backend import RunOptions, simulate

BASE_SEED = 20261011
RELATION = re.compile(r"@relation\(([^,)]+)")

# Two-sided 95% Student t values for 1 to 30 degrees of freedom.
T95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
    7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179,
    13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101,
    19: 2.093, 20: 2.086, 21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064,
    25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
}  # fmt: skip


def t_critical(degrees_of_freedom: int, confidence: float) -> float:
    """Two-sided Student t value. Uses the normal value above 30 df."""
    if abs(confidence - 0.95) > 1e-9:
        raise ValueError("only the 95% level has a table; use 0.95")
    if degrees_of_freedom < 1:
        raise ValueError("need at least two replications")
    return T95.get(degrees_of_freedom, 1.96)


@dataclasses.dataclass(frozen=True)
class Interval:
    mean: float
    lower: float
    upper: float
    half_width: float


def confidence_interval(values: list[float], confidence: float) -> Interval:
    """Mean and confidence interval of replication values."""
    mean = statistics.fmean(values)
    if len(values) < 2:
        return Interval(mean, mean, mean, 0.0)
    spread = statistics.stdev(values) / len(values) ** 0.5
    half = t_critical(len(values) - 1, confidence) * spread
    return Interval(mean, mean - half, mean + half, half)


@dataclasses.dataclass
class CheckResult:
    layer: str
    module: str
    name: str
    uid: str | None
    passed: bool
    message: str
    seconds: float
    properties: dict[str, str]


class Context:
    """Shared state of one verification run: model, runs and properties."""

    def __init__(
        self,
        model_dir: Path,
        replications: int | None = None,
    ) -> None:
        self.model_dir = model_dir
        self.packages = parse_model(model_dir)
        self.model: ir.Model = load_model(model_dir)
        self.replications_override = replications
        self.properties: dict[str, str] = {}
        self._runs: dict[tuple[str, float, float, int], RunResult] = {}

    def record(self, key: str, value: float | str) -> None:
        """Attach a property to the current check (a JUnit property)."""
        if isinstance(value, float):
            text = f"{value:.6g}"
        else:
            text = str(value)
        self.properties[key.upper()] = text

    def run(
        self,
        scenario: str,
        horizon_s: float,
        seed_index: int,
        duration_scale: float = 1.0,
        drain: bool = False,
        model: ir.Model | None = None,
    ) -> RunResult:
        """One replication, cached. Seeds are fixed, so runs repeat."""
        key = (scenario, horizon_s, duration_scale, seed_index)
        source = model or self.model
        if model is None and key in self._runs and not drain:
            return self._runs[key]
        options = RunOptions(
            seed=BASE_SEED + seed_index,
            horizon_s=horizon_s,
            duration_scale=duration_scale,
            drain=drain,
        )
        result = simulate(source, scenario, options)
        if model is None:
            self._runs[key] = result
        return result

    def replications(self, requested: int) -> int:
        if self.replications_override is not None:
            return self.replications_override
        return requested


CheckFunction = Callable[[Context], None]


def _uid_of(function: CheckFunction) -> str | None:
    match = RELATION.search(function.__doc__ or "")
    return match.group(1).strip() if match else None


def module_checks(module: ModuleType) -> list[tuple[str, CheckFunction]]:
    """The check functions of a module, in definition order."""
    return [
        (name, value)
        for name, value in vars(module).items()
        if name.startswith("check_") and callable(value)
    ]


def run_module(
    context: Context,
    layer: str,
    module: ModuleType,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    for name, function in module_checks(module):
        context.properties = {}
        started = time.perf_counter()
        try:
            function(context)
            passed, message = True, "ok"
        except AssertionError as failure:
            passed, message = False, str(failure) or "assertion failed"
        except Exception as error:  # noqa: BLE001 - reported as a failure
            passed = False
            message = f"error: {type(error).__name__}: {error}"
        results.append(
            CheckResult(
                layer=layer,
                module=module.__name__,
                name=name,
                uid=_uid_of(function),
                passed=passed,
                message=message,
                seconds=time.perf_counter() - started,
                properties=dict(context.properties),
            )
        )
    return results


def write_junit(path: Path, results: list[CheckResult]) -> None:
    """Write results as JUnit XML, using the pytest dialect layout."""
    path.parent.mkdir(parents=True, exist_ok=True)
    suite = ElementTree.Element(
        "testsuite",
        name="halcyon-verification",
        tests=str(len(results)),
        failures=str(sum(1 for r in results if not r.passed)),
        errors="0",
        skipped="0",
        time=f"{sum(r.seconds for r in results):.3f}",
    )
    for result in results:
        case = ElementTree.SubElement(
            suite,
            "testcase",
            classname=result.module,
            name=result.name,
            time=f"{result.seconds:.3f}",
        )
        if result.properties:
            properties = ElementTree.SubElement(case, "properties")
            for key, value in result.properties.items():
                ElementTree.SubElement(
                    properties, "property", name=key, value=value
                )
        if not result.passed:
            failure = ElementTree.SubElement(
                case, "failure", message=result.message
            )
            failure.text = result.message
    tree = ElementTree.ElementTree(suite)
    ElementTree.indent(tree)
    tree.write(path, encoding="utf-8", xml_declaration=True)
