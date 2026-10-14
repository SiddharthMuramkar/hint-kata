"""Unit tests for app/ingest/chunk.py: paths, anchors, sizes, fences, merging, stable keys."""

import hashlib
from pathlib import Path

from app.ingest.chunk import (
    MAX_TOKENS,
    MIN_TOKENS,
    Chunk,
    chunk_page,
    slugify,
    tokens,
)
from app.ingest.normalize import FENCE_RE, mark_code, normalize

FIXTURES = Path(__file__).parent / "fixtures" / "ingest"


def words(n_tokens: int, word: str = "word") -> str:
    """Plain prose of about `n_tokens` tokens (len // 4), as short paragraphs."""
    para = " ".join([word] * 40)  # 199 chars, about 50 tokens
    return "\n\n".join([para] * max(1, round(n_tokens / 50)))


def fence(n_lines: int, blank_every: int = 7) -> str:
    """A fenced block with blank lines and `#` comment lines inside, like real code."""
    body = []
    for i in range(n_lines):
        body.append("" if i % blank_every == 3 else f"# step {i}" if i % 5 == 0 else f"x{i} = {i}")
    return "```python\n" + "\n".join(body) + "\n```"


def doc(*parts: str) -> str:
    return "# Page { #page }\n\n" + "\n\n".join(parts) + "\n"


def run(markdown: str, model: str = "m1") -> list[Chunk]:
    return chunk_page("src-1", "fastapi", "Page title", markdown, model)


def fences_of(markdown: str) -> list[str]:
    """Every fenced block in the Markdown, as text."""
    blocks: list[list[str]] = []
    prev = False
    for ln, code in mark_code(markdown):
        if code and not prev:
            blocks.append([])
        if code:
            blocks[-1].append(ln)
        prev = code
    return ["\n".join(b) for b in blocks]


def test_heading_path_and_anchors() -> None:
    md = doc(
        f"Intro text. {words(150)}",
        f"## Setup {{ #setup-id }}\n\n{words(120)}",
        f"### Linux\n\n{words(120)}",
        f"### Mac <!-- anchor: mac-id -->\n\n{words(120)}",
        f"## Run it\n\n{words(120)}",
    )
    got = [(c.heading_path, c.anchor) for c in run(md)]
    assert got == [
        (("FastAPI", "Page title"), "page"),
        (("FastAPI", "Page title", "Setup"), "setup-id"),
        (("FastAPI", "Page title", "Setup", "Linux"), "linux"),
        (("FastAPI", "Page title", "Setup", "Mac"), "mac-id"),
        (("FastAPI", "Page title", "Run it"), "run-it"),
    ]


def test_embed_text_starts_with_the_breadcrumb_and_text_does_not() -> None:
    md = doc(f"## Setup\n\n{words(120)}", f"### Linux\n\n{words(120)}")
    by_anchor = {c.anchor: c for c in run(md)}
    linux = by_anchor["linux"]
    assert linux.embed_text.startswith("FastAPI › Page title › Setup › Linux\n\n")
    assert linux.embed_text.endswith(linux.text) and "›" not in linux.text
    assert by_anchor["setup"].heading_path == ("FastAPI", "Page title", "Setup")


def test_repeated_headings_get_unique_anchors() -> None:
    md = doc(*(f"## Example\n\n{words(120)}" for _ in range(3)))
    assert [c.anchor for c in run(md)] == ["example", "example-1", "example-2"]


def test_hashes_inside_fences_are_not_headings() -> None:
    md = doc(f"## Real\n\n{words(100)}\n\n```python\n# Not a heading\n## Also not\n```\n")
    assert [c.heading_path[-1] for c in run(md)] == ["Real"]


def test_h4_and_deeper_stay_in_their_section() -> None:
    md = doc(f"## A\n\n{words(100)}\n\n#### Deep\n\n{words(100)}")
    chunks = run(md)
    assert len(chunks) == 1 and "#### Deep" in chunks[0].text


def test_small_sections_merge_forward_into_the_next() -> None:
    md = doc(
        "## A\n\nA tiny section.",
        "## B\n\nAnother tiny one.",
        f"## C\n\n{words(400)}",
    )
    (chunk,) = [c for c in run(md) if c.anchor == "a"]
    assert chunk.heading_path[-1] == "A"  # path and anchor are the first section's
    assert "## B" in chunk.text and "## C" in chunk.text
    assert [c.anchor for c in run(md) if c.anchor in {"b", "c"}] == []


def test_a_small_last_section_merges_backward() -> None:
    md = doc(f"## A\n\n{words(400)}", f"## Tail\n\n{words(20)}")
    chunks = run(md)
    assert [c.anchor for c in chunks] == ["a"]
    assert "## Tail" in chunks[0].text


def test_merge_never_crosses_the_hard_max() -> None:
    md = doc(f"## Small\n\n{words(30)}", f"## Big\n\n{words(750)}")
    assert tokens(words(30)) + tokens(words(750)) > MAX_TOKENS
    assert [c.anchor for c in run(md)] == ["small", "big"]


def test_sizes_stay_within_bounds() -> None:
    md = doc(
        f"## One\n\n{words(300)}",
        f"## Two\n\n{words(2500)}",
        f"### Two-a\n\n{words(30)}",
        f"### Two-b\n\n{words(90)}",
        f"## Three\n\n{words(600)}",
        f"## Four\n\n{words(10)}",
    )
    sizes = [tokens(c.text) for c in run(md)]
    assert len(sizes) > 5
    assert max(sizes) <= MAX_TOKENS
    assert min(sizes) >= MIN_TOKENS


def test_a_long_section_is_split_without_overlap_or_loss() -> None:
    body = words(2500)
    chunks = [c for c in run(doc(f"## Long\n\n{body}")) if c.anchor == "long"]
    assert len(chunks) >= 4
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    joined = "".join("".join(c.text.split()) for c in chunks)
    assert joined == "".join(body.split())  # nothing repeated, nothing dropped


def test_fences_are_never_split() -> None:
    blocks = [fence(60), fence(250), fence(40)]
    prose = words(300)
    md = doc(
        f"## Code\n\n{prose}\n\n{blocks[0]}\n\n{prose}\n\n{blocks[1]}\n\n{blocks[2]}\n\n{prose}"
    )
    chunks = run(md)
    assert len(chunks) > 2
    for c in chunks:
        assert sum(1 for ln in c.text.splitlines() if FENCE_RE.match(ln)) % 2 == 0  # balanced
        assert "".join(c.text.split()).count("```") % 2 == 0
    for block in blocks:
        assert sum(block in c.text for c in chunks) == 1  # whole, in exactly one chunk


def test_a_single_oversize_fence_stays_whole() -> None:
    big = fence(1500)
    assert tokens(big) > MAX_TOKENS
    chunks = run(doc(f"## Code\n\n{words(100)}\n\n{big}\n\n{words(100)}"))
    assert sum(big in c.text for c in chunks) == 1


def test_a_fence_in_a_blockquote_is_not_split() -> None:
    quoted = "\n".join(f"> {ln}" if ln else ">" for ln in fence(300).splitlines())
    chunks = run(doc(f"## Q\n\n{words(500)}\n\n{quoted}"))
    assert sum(quoted in c.text for c in chunks) == 1


def test_keys_are_stable_across_runs_and_follow_the_formula() -> None:
    md = doc(f"## A\n\n{words(300)}", f"## B\n\n{words(1500)}")
    first, second = run(md), run(md)
    assert first == second
    for c in first:
        want = hashlib.sha256(f"src-1|{c.anchor}|{c.ordinal}".encode()).hexdigest()
        assert c.chunk_key == want
    assert len({c.chunk_key for c in first}) == len(first)


def test_keys_survive_an_edit_but_the_content_hash_does_not() -> None:
    before = run(doc(f"## A\n\n{words(300)}", f"## B\n\n{words(300, 'beta')}"))
    after = run(doc(f"## A\n\n{words(300)}", f"## B\n\n{words(300, 'gamma')}"))
    assert [c.chunk_key for c in before] == [c.chunk_key for c in after]
    changed = [b.anchor for b, a in zip(before, after, strict=True) if b != a]
    assert changed == ["b"]


def test_content_hash_covers_the_model_name() -> None:
    md = doc(f"## A\n\n{words(300)}")
    a, b = run(md, "model-1"), run(md, "model-2")
    assert [c.chunk_key for c in a] == [c.chunk_key for c in b]
    assert all(x.content_sha256 != y.content_sha256 for x, y in zip(a, b, strict=True))
    for c in a:
        assert c.content_sha256 == hashlib.sha256((c.embed_text + "model-1").encode()).hexdigest()
        assert c.model == "model-1"


def test_slugify_matches_the_site_style() -> None:
    assert slugify("What is “Dependency Injection”?") == "what-is-dependency-injection"
    assert slugify("Import `Depends`") == "import-depends"
    assert slugify("Créer un modèle") == "creer-un-modele"


def test_real_shaped_pages_chunk_cleanly() -> None:
    for kind, name in {
        "fastapi_raw": "fastapi_cached.md",
        "pydantic_ai_md": "pydantic_served.md",
        "github_article": "github_article.md",
    }.items():
        md = normalize(kind, (FIXTURES / name).read_text(encoding="utf-8"))
        chunks = run(md)
        assert chunks and all(c.text.strip() for c in chunks)
        assert all(
            "<!--" not in c.heading_path[-1] and "{#" not in c.heading_path[-1] for c in chunks
        )
        for block in fences_of(md):
            assert any(block in c.text for c in chunks)


def test_an_empty_page_has_no_chunks() -> None:
    assert run("# Only a title\n") == []
