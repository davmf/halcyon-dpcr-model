"""CLI smoke tests, run as subprocesses. Kept short: no Pilot run here."""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUN = REPO / "tools" / "run.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUN), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO,
    )


def test_bounds_prints_the_bottleneck() -> None:
    completed = _run("bounds")
    assert completed.returncode == 0, completed.stderr
    assert "baseSteady" in completed.stdout
    assert "bottleneck blocks" in completed.stdout


def test_simulate_prints_intervals() -> None:
    completed = _run(
        "simulate",
        "--scenario",
        "baseSteady",
        "--replications",
        "2",
        "--horizon-h",
        "2",
    )
    assert completed.returncode == 0, completed.stderr
    assert "completedPerShift" in completed.stdout
    assert "conservation gap: 0" in completed.stdout
