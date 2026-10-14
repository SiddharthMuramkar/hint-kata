"""`uv run fastapi dev` must work from the locked environment (issue #109).

`fastapi` ships the `fastapi` console script, but the script only works when the separate
`fastapi-cli` package is installed. Without it, `fastapi dev` exits with "please install
fastapi[standard]". These tests are fast and need no network or open port.
"""

import re
import shutil
import subprocess
import sys
import sysconfig
import tomllib
from pathlib import Path

import fastapi.cli

ROOT = Path(__file__).resolve().parents[1]


def _run(*cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)


def test_fastapi_cli_package_is_installed() -> None:
    # fastapi.cli swallows the ImportError and sets cli_main to None when fastapi-cli is missing.
    assert fastapi.cli.cli_main is not None


def test_fastapi_console_script_resolves_inside_the_venv() -> None:
    scripts_dir = sysconfig.get_path("scripts")
    assert Path(scripts_dir).is_relative_to(sys.prefix)
    script = shutil.which("fastapi", path=scripts_dir)
    assert script is not None, f"no `fastapi` console script in {scripts_dir}"


def test_fastapi_console_script_lists_dev_and_run() -> None:
    script = shutil.which("fastapi", path=sysconfig.get_path("scripts"))
    assert script is not None
    result = _run(script, "--help")
    assert result.returncode == 0, result.stdout + result.stderr
    assert re.search(r"\bdev\b", result.stdout)
    assert re.search(r"\brun\b", result.stdout)


def test_fastapi_cli_runs_as_a_module() -> None:
    result = _run(sys.executable, "-m", "fastapi_cli", "--help")
    assert result.returncode == 0, result.stdout + result.stderr
    assert re.search(r"\bdev\b", result.stdout)


def test_entrypoint_in_pyproject_points_at_the_app() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert config["tool"]["fastapi"]["entrypoint"] == "app.main:app"
