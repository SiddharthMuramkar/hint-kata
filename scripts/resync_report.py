"""Markdown report for the weekly docs re-sync: which sources changed, which lessons may be stale.

Usage: uv run python scripts/resync_report.py [--old-ref HEAD] [--manifest content/sources.yaml]
       [--content content] [--fetch-log FILE] [--ids-only]

Compares the manifest on disk (new) with `git show <old-ref>:<manifest>` (old). Failed ids come from
the `FAILED <id>` lines that scripts/fetch_docs.py prints (pass its output as --fetch-log).
`--ids-only` prints just the changed ids on one line, for shell scripts.
Reporting only: the exit code is always 0.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

# One line per bullet: GitHub shows a single newline in a PR body as a line break.
FOOTER = "\n".join(
    [
        "### Before you merge",
        "- Merging only updates `content/sources.yaml`. If the repository secrets exist, the "
        "`docs-resync` workflow then re-embeds the changed sources.",
        "- CI note: a pull request opened with `GITHUB_TOKEN` does not start the `checks` workflow "
        "by itself (GitHub holds it for approval). Click **Approve workflows to run**, or push an "
        "empty commit to this branch, or close and reopen this PR. Wait for `checks` to pass "
        "before you merge. A fine-grained token can start it automatically; see "
        "`docs/runbooks/docs-resync.md`.",
    ]
)


def changed_ids(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    """Ids whose sha256 differs. An id with no old sha256 (new entry) counts as changed."""
    before = {s["id"]: s.get("sha256") for s in old.get("sources", [])}
    return [s["id"] for s in new.get("sources", []) if s.get("sha256") != before.get(s["id"])]


def failed_ids(log: str) -> list[str]:
    """Ids from the `FAILED <id> ...` lines of a fetch_docs.py run."""
    parts = (line.split() for line in log.splitlines() if line.startswith("FAILED"))
    return [p[1] for p in parts if len(p) > 1]


def lesson_sources(content: Path) -> dict[str, list[str]]:
    """Map lesson id (its folder name) to the source ids in its lesson.md frontmatter."""
    out: dict[str, list[str]] = {}
    for md in sorted(content.rglob("lesson.md")):
        raw = md.read_text(encoding="utf-8")
        if raw.startswith("---"):
            meta = yaml.safe_load(raw.split("---", 2)[1]) or {}
            out[md.parent.name] = list(meta.get("sources") or [])
    return out


def stale_lessons(lessons: dict[str, list[str]], changed: list[str]) -> dict[str, list[str]]:
    """Lessons that cite at least one changed id, with the ids they cite."""
    hit = {name: [s for s in ids if s in changed] for name, ids in lessons.items()}
    return {name: ids for name, ids in hit.items() if ids}


def _short(sha: str | None) -> str:
    return (sha or "")[:8] or "none"


def render(
    old: dict[str, Any],
    new: dict[str, Any],
    failed: list[str],
    lessons: dict[str, list[str]],
) -> str:
    """The Markdown report (also used as the pull request body)."""
    changed = changed_ids(old, new)
    now = {s["id"]: s for s in new.get("sources", [])}
    before = {s["id"]: s.get("sha256") for s in old.get("sources", [])}
    out = ["## Docs re-sync plan", ""]
    out.append(f"{len(changed)} of {len(now)} source pages changed since the last sync.")
    if changed:
        out += ["", f"### Changed sources ({len(changed)})"]
        for sid in changed:
            hashes = f"`{_short(before.get(sid))}` to `{_short(now[sid].get('sha256'))}`"
            out.append(f"- `{sid}`: {now[sid].get('title', '')} ({hashes})")
    stale = stale_lessons(lessons, changed)
    if stale:
        out += ["", f"### Lessons to re-check ({len(stale)})"]
        out.append("These lessons cite a changed source, so their quizzes may be stale.")
        for name, ids in stale.items():
            out.append(f"- `{name}` cites {', '.join(f'`{s}`' for s in ids)}")
    if failed:
        out += ["", f"### Failed to fetch ({len(failed)})"]
        out.append("These pages were skipped and keep their old hash. The run is marked failed.")
        out += [f"- `{sid}`" for sid in failed]
    return "\n".join([*out, "", FOOTER])


def read_old_manifest(ref: str, manifest: str) -> dict[str, Any]:
    """The manifest as of a git ref. Warns and returns an empty one if the ref has none."""
    shown = subprocess.run(
        ["git", "show", f"{ref}:./{manifest}"], capture_output=True, text=True, check=False
    )
    if shown.returncode != 0:
        print(f"warning: no manifest at {ref}; counting every source as changed", file=sys.stderr)
        return {}
    return yaml.safe_load(shown.stdout) or {}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Report what the docs re-sync changed.")
    ap.add_argument("--old-ref", default="HEAD", help="git ref holding the old manifest")
    ap.add_argument("--manifest", default="content/sources.yaml")
    ap.add_argument("--content", type=Path, default=Path("content"))
    ap.add_argument("--fetch-log", type=Path, help="saved output of scripts/fetch_docs.py")
    ap.add_argument("--ids-only", action="store_true", help="print only the changed ids")
    args = ap.parse_args(argv)

    old = read_old_manifest(args.old_ref, args.manifest)
    new = yaml.safe_load(Path(args.manifest).read_text(encoding="utf-8")) or {}
    if args.ids_only:
        print(" ".join(changed_ids(old, new)))
        return 0
    log = args.fetch_log.read_text(encoding="utf-8") if args.fetch_log else ""
    print(render(old, new, failed_ids(log), lesson_sources(args.content)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
