"""PostToolUse hook: format and lint an edited .py file; exit 2 with the errors if any remain."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run(args: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def main() -> int:
    path = json.load(sys.stdin).get("tool_input", {}).get("file_path", "")
    if not path.endswith(".py") or not Path(path).is_file():
        return 0
    top = run(["git", "rev-parse", "--show-toplevel"], str(Path(path).parent))
    if top.returncode != 0:
        return 0
    root = top.stdout.strip()
    run(["uv", "run", "--frozen", "ruff", "format", path], root)
    check = run(["uv", "run", "--frozen", "ruff", "check", "--fix", path], root)
    if check.returncode != 0:
        print(check.stdout + check.stderr, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
