"""Tests for scripts/ingest.py that need no database and no network."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
import yaml
from pydantic_ai import Embedder
from pydantic_ai.embeddings import TestEmbeddingModel

from app.config import settings
from app.ingest.normalize import NORMALIZERS
from app.ingest.pipeline import as_markdown

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "ingest.py"
FIXTURES = Path(__file__).parent / "fixtures" / "ingest"
PAGES = [
    ("fastapi-dependencies", "fastapi", "fastapi_raw", "fastapi_cached.md"),
    ("pydantic-ai-install", "pydantic-ai", "pydantic_ai_md", "pydantic_served.md"),
    ("github-protected-branches", "github", "github_article", "github_article.md"),
]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ingest_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ing = _load()


LINK = {  # as in content/sources.yaml: title and url only, no fetch_url, no sha256
    "id": "claude-code-docs-memory",
    "track": "github",
    "title": "How Claude remembers your project",
    "url": "https://code.example/docs/memory",
    "kind": "link",
    "version": "live",
}


def make_site(tmp_path: Path, pages: int = 3, links: int = 0) -> tuple[Path, Path]:
    """A manifest and a cache laid out like scripts/fetch_docs.py leaves them. Link entries get
    no cache file."""
    cache = tmp_path / "cache"
    entries: list[dict[str, str]] = [dict(LINK, id=f"{LINK['id']}-{i}") for i in range(links)]
    for id_, track, kind, name in PAGES[:pages]:
        entries.append(
            {
                "id": id_,
                "track": track,
                "title": f"Title of {id_}",
                "url": f"https://docs.example/{id_}/",
                "kind": kind,
                "version": "1.0",
            }
        )
        (cache / track).mkdir(parents=True, exist_ok=True)
        (cache / track / f"{id_}.md").write_text((FIXTURES / name).read_text(encoding="utf-8"))
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(yaml.safe_dump({"sources": entries}), encoding="utf-8")
    return manifest, cache


@pytest.fixture(autouse=True)
def _blank_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "database_url_unpooled", "")
    monkeypatch.setattr(settings, "openrouter_api_key", "")


def test_dry_run_prints_counts_and_sizes_without_a_key_or_a_database(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest, cache = make_site(tmp_path)
    assert ing.main(["--manifest", str(manifest), "--cache", str(cache), "--dry-run"]) == 0
    out = capsys.readouterr().out
    for id_, *_ in PAGES:
        assert id_ in out
    assert "chunks  tokens min" in out and "avg" in out and "max" in out
    assert "dry-run: 3 pages" in out and "nothing embedded" in out


def test_only_limits_the_run_and_takes_commas(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest, cache = make_site(tmp_path)
    args = ["--manifest", str(manifest), "--cache", str(cache), "--dry-run"]
    ing.main([*args, "--only", "fastapi-dependencies,github-protected-branches"])
    assert "dry-run: 2 pages" in capsys.readouterr().out
    ing.main([*args, "--only", "pydantic-ai-install"])
    assert "dry-run: 1 pages" in capsys.readouterr().out


def test_unknown_id_is_an_error(tmp_path: Path) -> None:
    manifest, cache = make_site(tmp_path)
    with pytest.raises(SystemExit, match="no source with id: nope"):
        ing.main(
            ["--manifest", str(manifest), "--cache", str(cache), "--dry-run", "--only", "nope"]
        )


def test_a_missing_cached_page_names_it_and_says_how_to_fetch_it(tmp_path: Path) -> None:
    manifest, cache = make_site(tmp_path)
    (cache / "github" / "github-protected-branches.md").unlink()
    with pytest.raises(SystemExit) as exc:
        ing.main(["--manifest", str(manifest), "--cache", str(cache), "--dry-run"])
    message = str(exc.value)
    assert "github-protected-branches" in message and "scripts/fetch_docs.py" in message


def test_check_and_ingest_need_the_database_url(tmp_path: Path) -> None:
    manifest, cache = make_site(tmp_path, pages=1)
    args = ["--manifest", str(manifest), "--cache", str(cache)]
    with pytest.raises(SystemExit, match="DATABASE_URL_UNPOOLED"):
        ing.main([*args, "--check"])


def test_ingest_needs_the_api_key_before_anything_else(tmp_path: Path) -> None:
    manifest, cache = make_site(tmp_path, pages=1)
    with pytest.raises(SystemExit, match="OPENROUTER_API_KEY"):
        ing.main(["--manifest", str(manifest), "--cache", str(cache)])


def test_the_modes_exclude_each_other(tmp_path: Path) -> None:
    manifest, cache = make_site(tmp_path, pages=1)
    with pytest.raises(SystemExit) as exc:
        ing.main(["--manifest", str(manifest), "--cache", str(cache), "--dry-run", "--check"])
    assert exc.value.code == 2


def test_every_kind_in_the_real_manifest_is_ingestable_or_a_link() -> None:
    manifest = Path(__file__).resolve().parent.parent / "content" / "sources.yaml"
    kinds = {e["kind"] for e in yaml.safe_load(manifest.read_text(encoding="utf-8"))["sources"]}
    assert kinds - {"link"} <= set(NORMALIZERS)


def test_link_entries_are_skipped_not_reported_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest, cache = make_site(tmp_path, links=2)
    args = ["--manifest", str(manifest), "--cache", str(cache), "--dry-run"]
    assert ing.main(args) == 0
    out = capsys.readouterr().out
    assert "skipped 2 link-only source(s)" in out and "dry-run: 3 pages" in out
    assert "claude-code-docs-memory" not in out  # no chunk line for them
    assert (
        ing.main([*args, "--only", "claude-code-docs-memory-0"]) == 0
    )  # only a link: nothing to do
    assert "dry-run: 0 pages" in capsys.readouterr().out


def test_a_link_only_ingest_has_nothing_to_do_and_needs_no_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest, cache = make_site(tmp_path, pages=0, links=1)
    assert ing.main(["--manifest", str(manifest), "--cache", str(cache)]) == 0
    assert "nothing to ingest" in capsys.readouterr().out


def test_raw_pages_are_ingested_and_non_markdown_becomes_one_code_block(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cache = tmp_path / "cache" / "github"
    cache.mkdir(parents=True)
    (cache / "mcp-intro.md").write_text("# Intro\n\n## Why\n\nBecause.\n")
    (cache / "example-workflow.md").write_text("# a yaml comment\non:\n  push:\n")
    base = {"track": "github", "url": "https://x.example/", "version": "1", "kind": "raw"}
    entries = [
        dict(base, id="mcp-intro", title="Intro", fetch_url="https://x.example/intro.md"),
        dict(base, id="example-workflow", title="Workflow", fetch_url="https://x.example/c.yml"),
    ]
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(yaml.safe_dump({"sources": entries}), encoding="utf-8")
    assert (
        ing.main(["--manifest", str(manifest), "--cache", str(tmp_path / "cache"), "--dry-run"])
        == 0
    )
    assert "dry-run: 2 pages, 2 chunks" in capsys.readouterr().out
    wrapped = as_markdown(entries[1], "# a yaml comment\non:\n")
    assert wrapped == "```yml\n# a yaml comment\non:\n```\n"
    assert as_markdown(entries[0], "# Intro\n") == "# Intro\n"


def test_prune_needs_the_whole_manifest_and_a_database(tmp_path: Path) -> None:
    manifest, cache = make_site(tmp_path)
    base = ["--manifest", str(manifest), "--cache", str(cache), "--prune"]
    for extra in (["--only", "fastapi-dependencies"], ["--check"]):
        with pytest.raises(SystemExit) as exc:
            ing.main([*base, *extra])
        assert exc.value.code == 2
    with pytest.raises(SystemExit, match="DATABASE_URL_UNPOOLED"):
        ing.main(base)


def test_prune_refuses_when_the_manifest_has_nothing_to_keep(tmp_path: Path) -> None:
    manifest, cache = make_site(tmp_path, pages=0, links=2)
    with pytest.raises(SystemExit, match="no ingestable sources"):
        ing.main(["--manifest", str(manifest), "--cache", str(cache), "--prune"])


def test_a_connection_failure_does_not_claim_pages_were_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, cache = make_site(tmp_path, pages=1)
    monkeypatch.setattr(
        settings, "database_url_unpooled", "postgresql://u:p@127.0.0.1:1/db?connect_timeout=2"
    )
    embedder = Embedder(TestEmbeddingModel(dimensions=settings.embed_dims))
    with pytest.raises(SystemExit) as exc:
        ing.main(["--manifest", str(manifest), "--cache", str(cache)], embedder=embedder)
    message = str(exc.value)
    assert message.startswith("error:") and "kept" not in message and "written" not in message
