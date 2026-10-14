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

from app.traces import Annotation, Checkpoint, Citation, Step, StepKind, Trace  # noqa: E402

DOCS = "https://docs.github.com/en/pull-requests/"
PR_DOC = Citation(url=DOCS + "get-started/about-pull-requests", title="About pull requests")
CHECKS_DOC = Citation(url=DOCS + "reference/status-checks", title="Status checks")
REVIEW_DOC = Citation(url=DOCS + "reference/pull-request-reviews", title="Pull request reviews")
MERGE_DOC = Citation(url=DOCS + "reference/pull-request-merges", title="Pull request merges")

CHECK_WHY = {
    "success": "This check passed. A passing check is automatic evidence that the change did not break the tests or the build.",
    "neutral": "This check finished with a neutral result. GitHub Actions treats neutral like a success for dependent checks, but read its details before you rely on it.",
    "skipped": "This check was skipped. GitHub reports a skipped job as a success, so it does not block the merge.",
}
CHECK_WHY_DEFAULT = "This check did not succeed. Open its details before you merge: a failed, cancelled or timed-out check usually means someone must act."


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
    checks = sorted(
        gh(f"repos/{repo}/commits/{pr['head']['sha']}/check-runs")["check_runs"],
        key=lambda c: c["name"],
    )

    steps: list[Step] = []

    def add(
        kind: StepKind,
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
            CHECK_WHY.get(run["conclusion"], CHECK_WHY_DEFAULT),
            ["CI", "status checks"],
            [CHECKS_DOC],
        )
    for r in reviews:
        add(
            "review_comment",
            r["user"]["login"],
            f"Review: {r['state'].lower().replace('_', ' ')}",
            clip(r.get("body") or "(no comment)"),
            "An approval is human evidence that the change is wanted and correct. A review that requests changes should be settled before the merge.",
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
            "Merging makes the change part of the base branch. "
            + (
                "The reviews and checks above are the evidence it was safe to do."
                if reviews
                else "Nobody reviewed this PR. A solo repo can allow that, because an author cannot approve their own PR. The checks above were the main evidence."
            ),
            ["merge", "merge methods"],
            [MERGE_DOC, PR_DOC],
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
            f"{'a review requested changes' if blocked else 'no review requested changes'}"
            f"{'' if reviews else ' (no review was left at all)'}.",
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
            "captured_at": (
                pr.get("merged_at") or pr.get("created_at") or datetime.now(UTC).isoformat()
            )[:10],
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
