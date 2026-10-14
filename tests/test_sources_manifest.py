"""Shape checks for content/sources.yaml: every entry is complete and ids are unique."""

import re
from pathlib import Path

import yaml

MANIFEST = Path(__file__).resolve().parent.parent / "content" / "sources.yaml"
REQUIRED = (
    "id",
    "track",
    "title",
    "url",
    "fetch_url",
    "kind",
    "version",
    "license",
    "attribution",
    "sha256",
    "fetched_at",
)
KINDS = {"fastapi_raw", "pydantic_ai_md", "github_article"}


def _entries() -> list[dict[str, str]]:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["sources"]


def test_every_entry_has_the_required_fields() -> None:
    for entry in _entries():
        for field in REQUIRED:
            assert entry.get(field), f"{entry.get('id', entry)}: missing {field}"
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]), f"{entry['id']}: bad sha256"
        assert entry["kind"] in KINDS, f"{entry['id']}: unknown kind {entry['kind']}"
        assert entry["url"] in entry["attribution"], f"{entry['id']}: attribution lacks the url"


def test_ids_are_unique() -> None:
    ids = [e["id"] for e in _entries()]
    assert len(ids) == len(set(ids)), "duplicate source ids"
