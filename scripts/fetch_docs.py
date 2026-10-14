"""Download the pages listed in content/sources.yaml into .cache/docs/ and clean them up.

Usage: uv run python scripts/fetch_docs.py [--manifest content/sources.yaml] [--cache .cache/docs]
       [--only <id>] [--update] [--check]

Fetched docs are untrusted data: we only read them, never follow instructions inside them.
Writes only to the cache directory and (with --update) the manifest.
A page that fails to download prints a `FAILED <id>` line and is skipped (its manifest entry is left
as it was); the other pages still run and the exit code is 1.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import posixpath
import re
import sys
import time
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

UA = "hint-kata-fetch/0.1 (+https://github.com/siddharth-0044/hint-kata)"
FASTAPI_RAW = "https://raw.githubusercontent.com/fastapi/fastapi"
GITHUB_HOST = "docs.github.com"
ALERTS = {"tip": "TIP", "note": "NOTE", "warning": "WARNING", "danger": "CAUTION"}
AGENT_SECTIONS = ("Documentation Index", "Querying This Documentation")

INCLUDE_RE = re.compile(r"^\{\*\s*(\S+)\s*(.*)\*\}$")
OLD_INCLUDE_RE = re.compile(r"^\{!>?\s*(\S+?)\s*!\}$")
LN_RE = re.compile(r"ln\[([^\]]*)\]")
HEADING_RE = re.compile(r"^(#{1,6})\s")
ANCHOR_RE = re.compile(r"^(#{1,6} .*?)\s*\{\s*#([\w.:-]+)\s*\}\s*$")
ADMONITION_RE = re.compile(r"^\s*///\s*(\w+)\s*(?:\|\s*(.*?))?\s*$")
TAB_RE = re.compile(r"^\s*////\s*tab\s*\|\s*(.*?)\s*$")


def fetch(url: str) -> str:
    """GET a URL as text (30 s timeout, polite rate for docs.github.com)."""
    if GITHUB_HOST in url:
        time.sleep(1)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


# --- Pydantic AI -----------------------------------------------------------------------


def strip_pydantic(text: str) -> str:
    """Drop the injected agent preamble: everything before the page H1, plus agent sections."""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.startswith("# ")), None)
    if start is None:
        raise ValueError("no H1 found: unexpected Pydantic AI page format")
    out: list[str] = []
    skip_level = 0  # heading level of the section being dropped, 0 = not dropping
    for ln in lines[start:]:
        m = HEADING_RE.match(ln)
        if m:
            level = len(m.group(1))
            if skip_level and level <= skip_level:
                skip_level = 0
            if not skip_level and any(s in ln for s in AGENT_SECTIONS):
                skip_level = level
        if not skip_level:
            out.append(ln)
    return "\n".join(out).strip() + "\n"


# --- FastAPI ---------------------------------------------------------------------------


def select_lines(source: str, spec: str) -> str:
    """Apply an `ln[a:b,c]` spec (1-based, inclusive). Spec `0` or empty means the whole file."""
    lines = source.splitlines()
    chosen: list[str] = []
    prev_end = 0
    for part in (p.strip() for p in spec.split(",") if p.strip() not in ("", "0")):
        a, _, b = part.partition(":")
        first = int(a)
        last = int(b) if b else first
        if chosen and first > prev_end + 1:
            chosen.append("# ...")
        chosen.extend(lines[first - 1 : last])
        prev_end = last
    return "\n".join(chosen if chosen else lines)


def repo_path(path: str) -> str:
    """Resolve an include path (relative to docs/en/) to a path inside the repo."""
    resolved = posixpath.normpath(posixpath.join("docs/en", path))
    if resolved.startswith("..") or resolved.startswith("/"):
        raise ValueError(f"include escapes the repository: {path}")
    return resolved


def resolve_includes(text: str, read: Callable[[str], str]) -> str:
    """Replace `{* path ln[..] *}` and `{!path!}` lines with fenced code blocks."""
    out: list[str] = []
    for ln in text.splitlines():
        body = ln.strip()
        star = INCLUDE_RE.match(body)
        bang = OLD_INCLUDE_RE.match(body)
        m = star or bang
        if m is None:
            out.append(ln)
            continue
        path = m.group(1)
        ln_spec = LN_RE.search(star.group(2)) if star else None
        code = select_lines(read(repo_path(path)), ln_spec.group(1) if ln_spec else "")
        indent = ln[: len(ln) - len(ln.lstrip())]
        lang = "python" if path.endswith(".py") else Path(path).suffix.lstrip(".")
        out.extend(f"{indent}{c}".rstrip() for c in [f"```{lang}", *code.splitlines(), "```"])
    return "\n".join(out)


def convert_blocks(text: str) -> str:
    """Turn `/// tip | Title` admonitions into GitHub alerts and `//// tab | T` into bold lines."""
    out: list[str] = []
    alert: list[str] | None = None  # body lines of the admonition being collected
    head: list[str] = []
    for ln in text.splitlines():
        if alert is not None:
            if ln.strip() == "///":
                body = "\n".join(alert).strip("\n").splitlines()
                out.extend(f"> {a}".rstrip() for a in [*head, *body])
                alert = None
            else:
                alert.append(ln)
            continue
        tab = TAB_RE.match(ln)
        adm = ADMONITION_RE.match(ln)
        if tab:
            out.append(f"**{tab.group(1)}**")
        elif ln.strip() == "////":
            continue
        elif adm:
            kind = ALERTS.get(adm.group(1).lower(), "NOTE")
            head = [f"[!{kind}]"] + ([f"**{adm.group(2)}**"] if adm.group(2) else [])
            alert = []
        else:
            out.append(ln)
    if alert is not None:
        raise ValueError("unterminated /// block")
    return "\n".join(out)


def convert_anchors(text: str) -> str:
    """`# Title { #slug }` -> `# Title <!-- anchor: slug -->`."""
    return "\n".join(ANCHOR_RE.sub(r"\1 <!-- anchor: \2 -->", ln) for ln in text.splitlines())


def clean_fastapi(text: str, read: Callable[[str], str]) -> str:
    text = resolve_includes(text, read)
    text = convert_anchors(convert_blocks(text))
    return text.strip() + "\n"


# --- GitHub Docs -----------------------------------------------------------------------


def clean_github(text: str) -> str:
    text = re.sub(r"<svg\b.*?</svg>", "", text, flags=re.DOTALL)
    text = re.sub(r"\]\(/(?=en/|assets/)", "](https://docs.github.com/", text)
    return text.strip() + "\n"


# --- pipeline --------------------------------------------------------------------------


def build(entry: dict[str, Any], cache: Path) -> str:
    """Download one source and return its final processed text."""
    kind = entry["kind"]
    text = fetch(entry["fetch_url"])
    if kind == "pydantic_ai_md":
        return strip_pydantic(text)
    if kind == "github_article":
        return clean_github(text)
    if kind == "fastapi_raw":

        def read(path: str) -> str:
            cached = cache / "fastapi" / "_src" / entry["version"] / path
            if cached.exists():
                return cached.read_text(encoding="utf-8")
            src = fetch(f"{FASTAPI_RAW}/{entry['version']}/{path}")
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_bytes(src.encode("utf-8"))
            return src

        return clean_fastapi(text, read)
    raise ValueError(f"unknown kind: {kind}")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cache_file(cache: Path, entry: dict[str, Any]) -> Path:
    return cache / entry["track"] / f"{entry['id']}.md"


def _yaml() -> ModuleType:
    try:
        return importlib.import_module("yaml")
    except ImportError:
        raise SystemExit("PyYAML is required for a YAML manifest (or pass a .json file)") from None


def load_manifest(path: Path) -> dict[str, Any]:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return _yaml().safe_load(path.read_text(encoding="utf-8"))


def save_manifest(path: Path, data: dict[str, Any]) -> None:
    if path.suffix == ".json":
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return
    path.write_text(
        _yaml().safe_dump(data, sort_keys=False, allow_unicode=True, width=1000), encoding="utf-8"
    )


def check(entries: list[dict[str, Any]], cache: Path) -> int:
    """Offline: verify cached files against the recorded sha256. Returns the exit code."""
    bad = good = 0
    if not any(e.get("sha256") for e in entries):
        print("FAIL: no entry has a sha256 recorded; run with --update first")
        return 1
    for e in entries:
        if not e.get("sha256"):
            status = "no-sha"
        else:
            f = cache_file(cache, e)
            if not f.exists():
                status = "MISSING"
            elif sha256(f.read_text(encoding="utf-8")) != e["sha256"]:
                status = "MISMATCH"
            else:
                status = "ok"
        bad += status in ("MISSING", "MISMATCH")
        good += status == "ok"
        print(f"{status:<9}{e['id']}")
    print(f"check: {good} ok, {bad} failed, {len(entries) - good - bad} without sha256")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fetch and clean the docs pages in the manifest.")
    ap.add_argument("--manifest", type=Path, default=Path("content/sources.yaml"))
    ap.add_argument("--cache", type=Path, default=Path(".cache/docs"))
    ap.add_argument("--only", help="only this source id")
    ap.add_argument("--update", action="store_true", help="write sha256 + fetched_at to manifest")
    ap.add_argument("--check", action="store_true", help="offline: verify cache against sha256")
    args = ap.parse_args(argv)

    manifest = load_manifest(args.manifest)
    entries: list[dict[str, Any]] = manifest["sources"]
    if args.only:
        entries = [e for e in entries if e["id"] == args.only]
        if not entries:
            raise SystemExit(f"no source with id {args.only!r}")
    if args.check:
        return check(entries, args.cache)

    failed = 0
    for e in entries:
        try:
            text = build(e, args.cache)
        except Exception as exc:  # one bad page must not stop the rest; reported, exit code 1
            failed += 1
            print(f"{'FAILED':<8}{e['id']:<55} {type(exc).__name__}: {' '.join(str(exc).split())}")
            continue
        f = cache_file(args.cache, e)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(text.encode("utf-8"))
        digest = sha256(text)
        note = "changed" if e.get("sha256") and e["sha256"] != digest else "ok"
        print(f"{note:<8}{e['id']:<55}{len(text):>8} B  {digest[:12]}")
        if args.update:
            e["sha256"] = digest
            e["fetched_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    if args.update:
        save_manifest(args.manifest, manifest)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
