"""Shape checks for content/sources.yaml: every entry is complete and ids are unique."""

import re
from pathlib import Path

import yaml

MANIFEST = Path(__file__).resolve().parent.parent / "content" / "sources.yaml"
ALWAYS = ("id", "track", "title", "url", "kind", "version", "license", "attribution")
FETCHED = ("fetch_url", "sha256", "fetched_at")  # every kind except `link`
KINDS = {"fastapi_raw", "pydantic_ai_md", "github_article", "raw", "link"}
RAW_PIN = re.compile(r"https://raw\.githubusercontent\.com/[\w.-]+/[\w.-]+/([0-9a-f]{40})/")


def _entries() -> list[dict[str, str]]:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["sources"]


def test_every_entry_has_the_required_fields() -> None:
    for entry in _entries():
        for field in ALWAYS:
            assert entry.get(field), f"{entry.get('id', entry)}: missing {field}"
        assert entry["kind"] in KINDS, f"{entry['id']}: unknown kind {entry['kind']}"
        assert entry["url"] in entry["attribution"], f"{entry['id']}: attribution lacks the url"
        if entry["kind"] == "link":
            continue
        for field in FETCHED:
            assert entry.get(field), f"{entry['id']}: missing {field}"
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]), f"{entry['id']}: bad sha256"


def test_link_entries_are_title_and_url_only() -> None:
    """Pages with no reuse licence are linked, never fetched: no fetch_url, hash or fetch time."""
    links = [e for e in _entries() if e["kind"] == "link"]
    assert links, "expected the Claude Code docs to be listed as link-only"
    for entry in links:
        for field in FETCHED:
            assert field not in entry, f"{entry['id']}: a link entry must not have {field}"
        assert "all rights reserved" in entry["license"], f"{entry['id']}: wrong licence text"


def test_raw_github_files_are_pinned_to_a_commit() -> None:
    """A branch name would let the page change under its recorded hash."""
    for entry in _entries():
        url = entry.get("fetch_url", "")
        if entry["kind"] == "raw" and "raw.githubusercontent.com" in url:
            m = RAW_PIN.match(url)
            assert m, f"{entry['id']}: fetch_url must name a full commit sha"
            assert m.group(1).startswith(entry["version"]), f"{entry['id']}: version != sha"


def test_ids_are_unique() -> None:
    ids = [e["id"] for e in _entries()]
    assert len(ids) == len(set(ids)), "duplicate source ids"
