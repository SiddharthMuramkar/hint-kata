"""Keep the status docs honest: regenerate the learning-log index, print a progress block.

Usage: uv run python scripts/docs_status.py --learning-log | --progress | --check

--learning-log  rewrite docs/LEARNING_LOG.md from the merged pull requests.
--progress      print (never write) lessons per track, open PRs and open issues by milestone.
                Paste it into docs/PROGRESS.md by hand. Run it from an up-to-date main checkout.
--check         exit 1 if docs/LEARNING_LOG.md would change. Not wired into CI yet.

A merged PR owns the file docs/learning-log/NNN-*.md, where NNN is the number in its `Closes #N`
line (else the PR number), zero-padded to 3. Rows come in merge order. A file that already has a
row keeps that row's text, so hand-edited labels survive; a new row is "NNN — <PR title>".
Files that no merged PR claims are listed at the end under "Unmatched entries".
Needs the `gh` CLI, logged in. Nothing else is installed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

REPO = "SiddharthMuramkar/hint-kata"
ROOT = Path(__file__).resolve().parent.parent
LIMIT = 300  # gh returns at most this many rows; the script stops if it gets exactly this many

HEADER = (
    "# Learning log\n\n"
    "Every PR adds one file under `docs/learning-log/` with its description "
    "(what changed, why, which file to read first).\n"
    "This page is the index, in merge order. Read the files top to bottom to re-learn how the "
    "site was built.\n\n"
    "| PR | Entry |\n|---|---|\n"
)
UNMATCHED_INTRO = (
    "\n## Unmatched entries\n\n"
    "No merged PR claims these files yet (the PR is still open, or its number does not match).\n\n"
)

# Files whose PR has no `Closes` line and whose number is not the PR number: {PR: file number}.
OVERRIDES = {76: 20}  # the docs pass wrote 020-docs-pass.md

GH_ARGS = {
    "merged": ["pr", "list", "--state", "merged", "--json", "number,title,body,mergedAt"],
    "open_prs": ["pr", "list", "--state", "open", "--json", "number,title,headRefName"],
    "open_issues": ["issue", "list", "--state", "open", "--json", "number,title,milestone"],
}

CLOSES = re.compile(r"\bcloses #(\d+)", re.IGNORECASE)
ROW = re.compile(r"^\| (?:#\d+|—) \| \[(?P<label>.+)\]\(learning-log/(?P<file>[^)]+)\) \|$", re.M)
UNMATCHED = re.compile(r"^- \[", re.M)
TITLE_PREFIX = re.compile(r"^\w+(\([^)]*\))?!?:\s*")
TITLE_SUFFIX = re.compile(r"\s*\(#\d+\)$")


def gh_fetch(kind: str) -> list[dict[str, Any]]:
    """Run one of the `gh ... list --json` queries in GH_ARGS."""
    cmd = ["gh", *GH_ARGS[kind], "--limit", str(LIMIT), "-R", REPO]
    data = json.loads(subprocess.run(cmd, check=True, capture_output=True, text=True).stdout)
    if len(data) >= LIMIT:
        raise SystemExit(f"gh returned {LIMIT} rows for {kind}; raise LIMIT so nothing is dropped")
    return data


def candidates(pr: dict[str, Any]) -> list[int]:
    """File numbers this PR may own, best first."""
    if pr["number"] in OVERRIDES:
        return [OVERRIDES[pr["number"]]]
    return [*map(int, CLOSES.findall(pr["body"] or "")), pr["number"]]


def label_for(pr: dict[str, Any], name: str) -> str:
    title = TITLE_SUFFIX.sub("", TITLE_PREFIX.sub("", pr["title"]))
    return f"{name[:3]} — {title}".replace("|", r"\|")


def build_index(prs: list[dict[str, Any]], log_dir: Path, old: str) -> str:
    """The whole text of docs/LEARNING_LOG.md. `old` supplies the labels to keep."""
    kept = {m["file"]: m["label"] for m in ROW.finditer(old)}
    files = sorted(p.name for p in log_dir.glob("*.md"))
    claimed: set[str] = set()
    rows: list[str] = []
    for pr in sorted(prs, key=lambda p: (p["mergedAt"], p["number"])):
        for number in candidates(pr):
            hit = [f for f in files if f.startswith(f"{number:03d}-") and f not in claimed]
            if hit:
                break
        else:
            continue  # a docs-only PR: no entry file, no row
        claimed.update(hit)
        rows += [
            f"| #{pr['number']} | [{kept.get(f) or label_for(pr, f)}](learning-log/{f}) |"
            for f in hit
        ]
    out = HEADER + "".join(f"{row}\n" for row in rows)
    unmatched = [f for f in files if f not in claimed]
    if unmatched:
        out += UNMATCHED_INTRO + "".join(f"- [{f}](learning-log/{f})\n" for f in unmatched)
    return out


def progress(content: Path, open_prs: list[dict[str, Any]], issues: list[dict[str, Any]]) -> str:
    """The status block for docs/PROGRESS.md (Markdown)."""
    tracks = {
        t.name: len(list(t.glob("*/lesson.md"))) for t in sorted(content.iterdir()) if t.is_dir()
    }
    out = ["### Lessons on main", *(f"- {name}: {n}" for name, n in tracks.items())]
    out += [f"- total: {sum(tracks.values())}", "", f"### Open pull requests ({len(open_prs)})"]
    out += [f"- #{p['number']} {p['title']} (`{p['headRefName']}`)" for p in open_prs]
    out += ["", f"### Open issues by milestone ({len(issues)})"]
    groups: dict[str, list[dict[str, Any]]] = {}
    for issue in sorted(issues, key=lambda i: i["number"]):
        groups.setdefault((issue["milestone"] or {}).get("title", "No milestone"), []).append(issue)
    for title, items in sorted(groups.items(), key=lambda g: (g[0] == "No milestone", g[0])):
        out += [
            "",
            f"#### {title} ({len(items)})",
            *(f"- #{i['number']} {i['title']}" for i in items),
        ]
    return "\n".join(out) + "\n"


def main(
    argv: list[str] | None = None,
    *,
    root: Path = ROOT,
    fetch: Callable[[str], list[dict[str, Any]]] = gh_fetch,
) -> int:
    ap = argparse.ArgumentParser(description="Regenerate or check the docs status pages.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--learning-log", action="store_true", help="rewrite docs/LEARNING_LOG.md")
    mode.add_argument("--progress", action="store_true", help="print the progress block")
    mode.add_argument("--check", action="store_true", help="exit 1 if the index is out of date")
    args = ap.parse_args(argv)
    if args.progress:
        print(progress(root / "content", fetch("open_prs"), fetch("open_issues")), end="")
        return 0
    path = root / "docs" / "LEARNING_LOG.md"
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    new = build_index(fetch("merged"), path.parent / "learning-log", old)
    if args.check:
        if new != old:
            print(
                "docs/LEARNING_LOG.md is out of date. Run: uv run python "
                "scripts/docs_status.py --learning-log",
                file=sys.stderr,
            )
            return 1
        return 0
    path.write_text(new, encoding="utf-8")
    rows = len(ROW.findall(new))
    print(
        f"docs/LEARNING_LOG.md: {rows} rows, {len(UNMATCHED.findall(new))} unmatched, "
        f"{'changed' if new != old else 'unchanged'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
