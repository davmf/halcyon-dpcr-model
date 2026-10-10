"""SysML v2 conformance gate: validate files with the OMG Pilot Implementation.

Usage:
    .venv/bin/python tools/sysml_conformance.py [PATH ...]

PATH is a `.sysml` file or a directory (searched recursively). The default
is `model/`. All files are loaded into one resource set together with the
standard library, so references between files resolve.

Each issue is printed as `path:line:column: SEVERITY: message`. The exit
status is 1 if any ERROR is reported, 2 on a setup error, 0 otherwise.

Environment:
    SYSML_PILOT_HOME  Directory with the Pilot jar and `sysml.library/`
                      (default: ~/.cache/sysml-pilot/0.62.0/sysml).
    JAVA              Java 21 executable (default: java on PATH).
"""

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
CHECKER_SOURCE = TOOLS_DIR / "PilotCheck.java"
DEFAULT_PILOT_HOME = Path.home() / ".cache/sysml-pilot/0.62.0/sysml"
JAR_NAME = "jupyter-sysml-kernel-0.62.0-all.jar"


@dataclass(frozen=True)
class Issue:
    severity: str
    path: Path
    line: int
    column: int
    message: str

    def format(self, base: Path) -> str:
        try:
            shown = self.path.relative_to(base)
        except ValueError:
            shown = self.path
        return (
            f"{shown}:{self.line}:{self.column}: "
            f"{self.severity}: {self.message}"
        )


@dataclass(frozen=True)
class Result:
    issues: list[Issue]
    file_count: int
    raw_output: str

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "ERROR"]


def pilot_home() -> Path:
    return Path(os.environ.get("SYSML_PILOT_HOME", DEFAULT_PILOT_HOME))


def collect_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.rglob("*.sysml")))
        elif path.is_file():
            files.append(path)
        else:
            raise FileNotFoundError(path)
    return [f.resolve() for f in files]


def build_command(files: list[Path], home: Path) -> list[str]:
    java = os.environ.get("JAVA") or shutil.which("java") or "java"
    return [
        java,
        "-cp",
        str(home / JAR_NAME),
        str(CHECKER_SOURCE),
        str(home / "sysml.library"),
        *[str(f) for f in files],
    ]


def parse_output(output: str) -> list[Issue]:
    issues = []
    for line in output.splitlines():
        if not line.startswith("ISSUE\t"):
            continue
        _, severity, path, row, column, message = line.split("\t", 5)
        issues.append(
            Issue(severity, Path(path), int(row), int(column), message)
        )
    return issues


def check(files: list[Path], home: Path | None = None) -> Result:
    home = home or pilot_home()
    jar = home / JAR_NAME
    if not jar.is_file():
        raise RuntimeError(f"Pilot jar not found: {jar}")
    completed = subprocess.run(
        build_command(files, home),
        capture_output=True,
        text=True,
        check=False,
    )
    output = completed.stdout + completed.stderr
    issues = parse_output(completed.stdout)
    if "SUMMARY\t" not in completed.stdout:
        raise RuntimeError(f"Pilot check did not complete:\n{output}")
    return Result(issues, len(files), output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[REPO_ROOT / "model"],
        help="SysML files or directories (default: model/)",
    )
    args = parser.parse_args(argv)
    try:
        files = collect_files(args.paths)
    except FileNotFoundError as error:
        print(f"error: no such file or directory: {error}", file=sys.stderr)
        return 2
    if not files:
        print("error: no .sysml files found", file=sys.stderr)
        return 2
    try:
        result = check(files)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    for issue in result.issues:
        print(issue.format(Path.cwd()))
    print(
        f"{result.file_count} files checked, {len(result.errors)} errors, "
        f"{len(result.issues) - len(result.errors)} other issues"
    )
    return 1 if result.errors else 0


if __name__ == "__main__":
    sys.exit(main())
