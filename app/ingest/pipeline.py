"""Cached page -> normalised Markdown -> chunks. No database, no network."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.ingest.chunk import Chunk, chunk_page, sha256
from app.ingest.normalize import normalize

Entry = dict[str, Any]


@dataclass(frozen=True)
class Page:
    """One source page: its row in `pages` plus its chunks. `source` is the track, `path` the id."""

    source: str
    path: str
    url: str
    title: str
    version_ref: str
    content_sha256: str
    chunks: list[Chunk]


def load_entries(manifest: Path, only: list[str] | None = None) -> list[Entry]:
    entries: list[Entry] = yaml.safe_load(manifest.read_text(encoding="utf-8"))["sources"]
    if only:
        unknown = sorted(set(only) - {e["id"] for e in entries})
        if unknown:
            raise ValueError(f"no source with id: {', '.join(unknown)}")
        entries = [e for e in entries if e["id"] in only]
    return entries


def cache_file(cache: Path, entry: Entry) -> Path:
    """Where scripts/fetch_docs.py put this page."""
    return cache / entry["track"] / f"{entry['id']}.md"


def missing_pages(entries: list[Entry], cache: Path) -> list[Entry]:
    return [e for e in entries if not cache_file(cache, e).is_file()]


def build_page(entry: Entry, cache: Path, model: str) -> Page:
    markdown = normalize(entry["kind"], cache_file(cache, entry).read_text(encoding="utf-8"))
    return Page(
        source=entry["track"],
        path=entry["id"],
        url=entry["url"],
        title=entry["title"],
        version_ref=str(entry.get("version", "")),
        content_sha256=sha256(markdown),
        chunks=chunk_page(entry["id"], entry["track"], entry["title"], markdown, model),
    )
