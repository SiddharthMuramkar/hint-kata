# ruff: noqa: E501
"""Turn a real GitHub pull request into a trace.json, using `gh api` (summaries only).

uv run python traces/scripts/pr_timeline.py --repo owner/name --pr 23 --out path/trace.json
"""

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.traces import Annotation, Checkpoint, Citation, Step, Trace  # noqa: E402

DOCS = "https://docs.github.com/en/pull-requests/"
PR_DOC = Citation(
    url=DOCS
    + "collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests",
    title="About pull requests",
)
CHECKS_DOC = Citation(
    url=DOCS
    + "collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/about-status-checks",
    title="About status checks",
)
REVIEW_DOC = Citation(
    url=DOCS
    + "collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews",
    title="About pull request reviews",
)


def gh(path: str) -> Any:
    out = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def clip(text: str, n: int = 200) -> str:
    text = text.strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def build(repo: str, number: int) -> Trace:
    pr = gh(f"repos/{repo}/pulls/{number}")
    commits = gh(f"repos/{repo}/pulls/{number}/commits?per_page=100")
    reviews = gh(f"repos/{repo}/pulls/{number}/reviews?per_page=100")
    checks = gh(f"repos/{repo}/commits/{pr['head']['sha']}/check-runs")["check_runs"]

    steps: list[Step] = []

    def add(
        kind: str,
        actor: str,
        title: str,
        summary: str,
        why: str,
        tags: list[str],
        cites: list[Citation],
    ) -> Step:
        step = Step(
            idx=len(steps),
            kind=kind,
            actor=actor,
            title=title,
            summary=summary,
            annotation=Annotation(why=why, concept_tags=tags, citations=cites),
        )
        steps.append(step)
        return step

    for c in commits:
        headline = c["commit"]["message"].splitlines()[0]
        add(
            "git_commit",
            c["commit"]["author"]["name"],
            f"Commit {c['sha'][:7]}",
            clip(headline),
            "Each commit is one saved step on the branch. Clear, focused commits make the review easier.",
            ["commits"],
            [PR_DOC],
        )
    add(
        "pr_opened",
        pr["user"]["login"],
        f"PR #{number} opened",
        clip(f"{pr['title']} ({pr['changed_files']} files, +{pr['additions']} -{pr['deletions']})"),
        "Opening a PR asks for the branch to be merged into the base branch. It also starts the CI checks and the review.",
        ["pull request"],
        [PR_DOC],
    )
    for run in checks:
        add(
            "ci_check",
            "github-actions",
            f"Check: {run['name']}",
            f"{run['status']}, conclusion: {run['conclusion']}",
            "A passing check is automatic evidence the change did not break the tests or the build. A failing one should block the merge.",
            ["CI", "status checks"],
            [CHECKS_DOC],
        )
    for r in reviews:
        add(
            "review_comment",
            r["user"]["login"],
            f"Review: {r['state'].lower().replace('_', ' ')}",
            clip(r.get("body") or "(no comment)"),
            "Approvals are human evidence the change is wanted and correct. Changes requested should block the merge.",
            ["code review"],
            [REVIEW_DOC],
        )

    checks_ok = all(c["conclusion"] in {"success", "neutral", "skipped"} for c in checks)
    blocked = any(r["state"] == "CHANGES_REQUESTED" for r in reviews)
    if pr.get("merged"):
        merger = (pr.get("merged_by") or {}).get("login", "unknown")
        merge = add(
            "merge",
            merger,
            f"PR #{number} merged",
            f"Merged into {pr['base']['ref']}.",
            "Merging makes the change part of the base branch. The checks and reviews above are the evidence it was safe to do.",
            ["merge"],
            [PR_DOC],
        )
        ready = checks_ok and not blocked
        merge.checkpoint = Checkpoint(
            type="predict_next",
            prompt="Look at the checks and reviews so far. Was this PR ready to merge?",
            options=[
                "Yes: checks passed and nothing blocked it",
                "No: a check failed or changes were requested",
            ],
            answer=0 if ready else 1,
            explanation=f"{len(checks)} check(s) {'all passed' if checks_ok else 'did not all pass'}; "
            f"{'a review requested changes' if blocked else 'no review requested changes'}.",
        )

    return Trace(
        id=f"pr-{repo.replace('/', '-')}-{number}",
        kind="github_pr",
        title=f"From commits to merge: PR #{number}",
        objectives=[
            "Read the signals on a pull request: commits, checks and reviews.",
            "Decide whether a PR is ready to merge, and say why.",
        ],
        source={
            "generator": "gh api",
            "script": "traces/scripts/pr_timeline.py",
            "repo": repo,
            "pr": number,
            "pr_url": pr["html_url"],
            "captured_at": datetime.now(UTC).strftime("%Y-%m-%d"),
        },
        steps=steps,
        takeaways=[
            "A PR collects its evidence in one place: commits, CI checks and reviews.",
            "Merge when the required checks pass and no review blocks it, not before.",
        ],
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--pr", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    trace = build(args.repo, args.pr)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(trace.model_dump_json(indent=2) + "\n")
    print(f"wrote {args.out} ({len(trace.steps)} steps)")


if __name__ == "__main__":
    main()
