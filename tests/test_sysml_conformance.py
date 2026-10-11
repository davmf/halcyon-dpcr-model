import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import sysml_conformance

FIXTURES = Path(__file__).parent / "fixtures" / "sysml_conformance"

pytestmark = pytest.mark.skipif(
    shutil.which("java") is None
    or not sysml_conformance.pilot_jar().is_file(),
    reason="Java or the SysML v2 Pilot Implementation is not available",
)


def run(*paths: Path) -> tuple[int, str]:
    import contextlib
    import io

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        status = sysml_conformance.main([str(p) for p in paths])
    return status, buffer.getvalue()


def test_valid_files_with_library_types_and_cross_file_import_pass():
    status, output = run(FIXTURES / "valid")

    assert status == 0, output
    assert "2 files checked, 0 errors" in output


def test_syntax_error_fails_with_file_and_line():
    status, output = run(FIXTURES / "syntax_error" / "broken.sysml")

    assert status == 1
    assert "broken.sysml:4:" in output
    assert "ERROR" in output


def test_unresolved_reference_fails_with_file_and_line():
    status, output = run(FIXTURES / "unresolved")

    assert status == 1
    assert "unresolved.sysml:8:" in output
    assert "Couldn't resolve reference" in output
    assert "Pmup" in output


def test_missing_path_is_a_setup_error():
    status, _ = run(FIXTURES / "does_not_exist.sysml")

    assert status == 2
