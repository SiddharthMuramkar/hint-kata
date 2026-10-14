"""SessionEnd hook: copy the session transcript to ~/hint-kata-inbox/ (outside the repo)."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path


def main() -> None:
    data = json.load(sys.stdin)
    src = Path(data["transcript_path"])
    session = re.sub(r"[^A-Za-z0-9_-]", "", str(data.get("session_id") or src.stem))
    inbox = Path.home() / "hint-kata-inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    dest = inbox / f"{session}.jsonl"
    if session and src.is_file() and not dest.exists():
        shutil.copyfile(src, dest)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
