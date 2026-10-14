"""Heading-aware chunking of normalised Markdown (see app/ingest/normalize.py).

One chunk per H2/H3 section, with its heading path and anchor. Target 300-500 tokens, hard max about
800, no overlap. A fenced code block is never split. A section under about 80 tokens is merged into
its neighbour. Tokens are approximated as `len(text) // 4`: no tokenizer dependency.

The one exception to the hard max is a single fence (or a single huge line) that is longer than that
on its own: it stays whole.
"""

import hashlib
import re
import unicodedata
from dataclasses import dataclass, replace

from app.ingest.normalize import FENCE_RE, HEADING_RE, closes_fence

MIN_TOKENS = 80
TARGET_TOKENS = 500
MAX_TOKENS = 800
SEP = " › "
TRACKS = {"fastapi": "FastAPI", "pydantic-ai": "Pydantic AI", "github": "GitHub"}
ANCHOR_RE = re.compile(r"\s*(?:\{\s*#([\w.:-]+)\s*\}|<!--\s*anchor:\s*([\w.:-]+)\s*-->)\s*$")
LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def tokens(text: str) -> int:
    return len(text) // 4


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slugify(text: str) -> str:
    """Python-Markdown / GitHub style: ascii, lowercase, words joined by single hyphens."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[-\s]+", "-", re.sub(r"[^\w\s-]", "", text).strip().lower())


@dataclass(frozen=True)
class Chunk:
    chunk_key: str
    source_id: str
    anchor: str
    heading_path: tuple[str, ...]
    ordinal: int
    text: str
    embed_text: str
    content_sha256: str
    model: str


@dataclass(frozen=True)
class Section:
    level: int
    title: str
    anchor: str
    path: tuple[str, ...]
    body: str

    @property
    def heading(self) -> str:
        return f"{'#' * self.level} {self.title}"


def _plain(heading: str) -> str:
    return LINK_RE.sub(r"\1", heading).replace("*", "").replace("`", "").strip()


def sections(markdown: str, root: tuple[str, ...]) -> list[Section]:
    """Split on H2/H3 (outside code fences). Text under the H1 becomes the first section.
    Anchors are the explicit id, else a slug of the heading; repeats get -1, -2."""
    seen: dict[str, int] = {}

    def unique(anchor: str) -> str:
        n = seen.get(anchor, -1) + 1
        seen[anchor] = n
        return anchor if n == 0 else f"{anchor}-{n}"

    heads: list[tuple[int, str, str]] = []  # (level, title, anchor)
    bodies: list[list[str]] = [[]]  # bodies[0] is the text under the H1
    h1_anchor = ""
    h1_seen = False
    fence = ""
    for ln in markdown.splitlines():
        m = None if fence else HEADING_RE.match(ln)
        if fence:
            fence = "" if closes_fence(ln, fence) else fence
        elif f := FENCE_RE.match(ln):
            fence = f[1]
        if not m or len(m[1]) > 3 or (len(m[1]) == 1 and h1_seen):
            bodies[-1].append(ln)
            continue
        text = ln[len(m[1]) :].strip()
        found = ANCHOR_RE.search(text)
        title = _plain(ANCHOR_RE.sub("", text))
        anchor = (found[1] or found[2]) if found else slugify(title)
        if len(m[1]) == 1:
            h1_seen, h1_anchor = True, anchor
        else:
            heads.append((len(m[1]), title, anchor))
            bodies.append([])

    out = [Section(1, root[-1], unique(h1_anchor or slugify(root[-1])), root, "\n".join(bodies[0]))]
    h2 = h3 = ""
    for (level, title, anchor), body in zip(heads, bodies[1:], strict=True):
        h2, h3 = (title, "") if level == 2 else (h2, title)
        path = (*root, *([h2] if h2 else []), *([h3] if h3 else []))
        out.append(Section(level, title, unique(anchor), path, "\n".join(body)))
    return [replace(s, body=s.body.strip()) for s in out if s.body.strip()]


def _join(a: Section, b: Section) -> Section:
    """Merge b into a: a's path and anchor stay; b's heading line stays in the text."""
    return replace(a, body=f"{a.body}\n\n{b.heading}\n\n{b.body}")


def merge_small(secs: list[Section]) -> list[Section]:
    """Merge a section under MIN_TOKENS into the next one (or the previous, at the end)."""
    out: list[Section] = []
    pending: Section | None = None
    for s in secs:
        if pending:
            if tokens(pending.body) + tokens(s.body) <= MAX_TOKENS:
                s = _join(pending, s)
            else:
                out.append(pending)
            pending = None
        if tokens(s.body) < MIN_TOKENS:
            pending = s
        else:
            out.append(s)
    if pending:
        if out and tokens(out[-1].body) + tokens(pending.body) <= MAX_TOKENS:
            out[-1] = _join(out[-1], pending)
        else:
            out.append(pending)
    return out


def units(body: str) -> list[tuple[str, str]]:
    """Split a section into (text, separator-before): paragraphs and whole fences. A paragraph that
    is over the hard max is cut into its lines (list items, table rows)."""
    parts: list[str] = []
    cur: list[str] = []
    fence = ""
    for ln in body.splitlines():
        if fence:
            cur.append(ln)
            if closes_fence(ln, fence):
                parts.append("\n".join(cur))
                cur, fence = [], ""
        elif m := FENCE_RE.match(ln):
            if cur:
                parts.append("\n".join(cur))
            cur, fence = [ln], m[1]
        elif ln.strip():
            cur.append(ln)
        elif cur:
            parts.append("\n".join(cur))
            cur = []
    if cur:
        parts.append("\n".join(cur))
    out: list[tuple[str, str]] = []
    for p in parts:
        if tokens(p) > MAX_TOKENS and not FENCE_RE.match(p.splitlines()[0]):
            out += [(ln, "\n\n" if i == 0 else "\n") for i, ln in enumerate(p.splitlines())]
        else:
            out.append((p, "\n\n"))
    return out


def split_body(body: str) -> list[str]:
    """Pack units into pieces of about TARGET_TOKENS. A tiny last piece joins the one before."""
    pieces: list[str] = []
    size = 0
    for text, sep in units(body):
        if pieces and size + tokens(text) <= TARGET_TOKENS:
            pieces[-1] += sep + text
            size += tokens(text)
        else:
            pieces.append(text)
            size = tokens(text)
    if len(pieces) > 1 and tokens(pieces[-1]) < MIN_TOKENS:
        if tokens(pieces[-2]) + tokens(pieces[-1]) <= MAX_TOKENS:
            pieces[-2:] = [pieces[-2] + "\n\n" + pieces[-1]]
    return pieces


def chunk_page(
    source_id: str, track: str, page_title: str, markdown: str, model: str
) -> list[Chunk]:
    """Chunk one normalised page. `model` goes into content_sha256, so a new model re-embeds."""
    root = (TRACKS.get(track, track), page_title)
    chunks: list[Chunk] = []
    for sec in merge_small(sections(markdown, root)):
        pieces = split_body(sec.body) if tokens(sec.body) > MAX_TOKENS else [sec.body]
        for ordinal, text in enumerate(pieces):
            embed_text = f"{SEP.join(sec.path)}\n\n{text}"
            chunks.append(
                Chunk(
                    chunk_key=sha256(f"{source_id}|{sec.anchor}|{ordinal}"),
                    source_id=source_id,
                    anchor=sec.anchor,
                    heading_path=sec.path,
                    ordinal=ordinal,
                    text=text,
                    embed_text=embed_text,
                    content_sha256=sha256(embed_text + model),
                    model=model,
                )
            )
    return chunks
