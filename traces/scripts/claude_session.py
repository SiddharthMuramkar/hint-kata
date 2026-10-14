"""Turn a Claude Code session transcript (JSONL) into a redacted trace.json draft.

uv run python traces/scripts/claude_session.py --transcript s.jsonl --out trace.json

The transcript format is internal and changes between versions, so this keeps only a whitelist of
fields and skips anything it does not recognise. A human must still review the output.
"""

import argparse
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pr_timeline  # noqa: E402

from app.traces import Step, StepKind, Trace  # noqa: E402

SECRETS = [
    (re.compile(p), r)
    for p, r in [
        (r"\bsk-[A-Za-z0-9_-]{8,}", "[redacted]"),
        (r"\bgh[pousr]_[A-Za-z0-9]{8,}", "[redacted]"),
        (r"\bAKIA[0-9A-Z]{16}\b", "[redacted]"),
        (r"\bxox[a-z]-[A-Za-z0-9-]{8,}", "[redacted]"),
        (r"\bBearer\s+\S+", "Bearer [redacted]"),
        (
            r"(?i:\b(\w*(?:KEY|TOKEN|SECRET|PASSW(?:OR)?D)\w*)\s*[=:]\s*\S+)",
            r"\1=[redacted]",
        ),
        (r"\b[A-Fa-f0-9]{32,}\b", "[redacted]"),
        # base64-ish run with a digit, an upper and a lower case letter (so plain paths survive)
        (
            r"(?=[A-Za-z0-9+/]*\d)(?=[A-Za-z0-9+/]*[A-Z])(?=[A-Za-z0-9+/]*[a-z])[A-Za-z0-9+/]{32,}={0,2}",
            "[redacted]",
        ),
    ]
]
HOME = re.compile(r"(?:/Users|/home)/[^/\s\"']+")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


USER = Path.home().name


def redact(text: str) -> str:
    text = HOME.sub("~", text)
    if len(USER) >= 3:  # also catches `ls -l` owners and dash-encoded project dirs
        text = re.sub(rf"\b{re.escape(USER)}\b", "user", text)
    text = EMAIL.sub("[email]", text)
    for pattern, repl in SECRETS:
        text = pattern.sub(repl, text)
    return text


def clip(text: str, n: int) -> str:
    text = redact(text).strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def summarise_input(name: str, args: Any) -> str:
    if not isinstance(args, dict):
        return clip(json.dumps(args, sort_keys=True), 120)
    if name == "Bash":
        return clip(str(args.get("command", "")), 160)
    if name in ("Edit", "Write") and args.get("file_path"):
        return clip(Path(str(args["file_path"])).name, 160)
    return clip(json.dumps(args, sort_keys=True), 120)


def result_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = [b.get("text") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(t for t in texts if isinstance(t, str))
    return ""


def records(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(errors="replace") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict):
                yield rec


def normalise(path: Path, title: str = "Claude Code session") -> Trace:
    steps: list[Step] = []
    version: str | None = None
    captured: str | None = None

    def add(kind: StepKind, actor: str, step_title: str, summary: str) -> None:
        steps.append(
            Step(idx=len(steps), kind=kind, actor=actor, title=step_title, summary=summary)
        )

    for rec in records(path):
        if version is None and isinstance(rec.get("version"), str):
            version = rec["version"]
        ts = rec.get("timestamp")
        if captured is None and isinstance(ts, str):
            captured = ts[:10]
        role, msg = rec.get("type"), rec.get("message")
        if role not in ("user", "assistant") or not isinstance(msg, dict) or rec.get("isMeta"):
            continue
        content = msg.get("content")
        blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content
        if not isinstance(blocks, list):
            continue
        for b in blocks:
            if not isinstance(b, dict):
                continue
            kind, text = b.get("type"), b.get("text")
            if kind == "text" and isinstance(text, str) and text.strip():
                if role == "user":
                    add("user_prompt", "user", "User prompt", clip(text, 600))
                else:
                    add("model_text", "claude", "Claude", clip(text, 600))
            elif kind == "tool_use" and role == "assistant":
                name = redact(str(b.get("name", "tool")))
                add("tool_call", "claude", name, summarise_input(name, b.get("input")))
            elif kind == "tool_result" and role == "user":
                out = result_text(b.get("content"))
                add(
                    "tool_result",
                    "tool",
                    "Tool result",
                    clip(out, 300) if out else "[binary/omitted]",
                )

    return Trace(
        id=f"claude-session-{path.stem[:8]}",
        kind="claude_code_session",
        title=title,
        objectives=[],
        source={
            "generator": "claude-code",
            "claude_code_version": version or "unknown",
            "captured_at": captured or "unknown",
            "redaction": {"ruleset_version": 1, "human_reviewed": False},
        },
        steps=steps,
        takeaways=[],
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--transcript", type=Path, required=True)
    ap.add_argument("--repo")
    ap.add_argument("--pr", type=int)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--title", default="Claude Code session")
    args = ap.parse_args()
    if bool(args.repo) != bool(args.pr):
        ap.error("--repo and --pr go together")
    trace = normalise(args.transcript, args.title)
    if args.repo and args.pr:
        for step in pr_timeline.build(args.repo, args.pr).steps:
            trace.steps.append(
                step.model_copy(update={"idx": len(trace.steps), "checkpoint": None})
            )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(trace.model_dump_json(indent=2) + "\n")
    print(f"wrote {args.out} ({len(trace.steps)} steps; review it by hand before committing)")


if __name__ == "__main__":
    main()
