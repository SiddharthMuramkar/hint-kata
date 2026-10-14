"""Turn a cached docs page into clean Markdown, one normaliser per source `kind`.

Input is the text that `scripts/fetch_docs.py` wrote to `.cache/docs/`. That script already inlines
FastAPI's `{* path ln[..] *}` includes (it fetches the `docs_src` files at the pinned tag into the
cache), turns `///` admonitions into `> [!TIP]` alerts and `//// tab` into bold lines, strips the
Pydantic AI agent preamble, and keeps heading ids as `<!-- anchor: id -->`. So here we check that
nothing raw is left and finish the job: plain labels instead of alert markers, no HTML, and the
Pydantic AI syntax that fetch_docs does not touch.

Fetched docs are untrusted data. We only read them, never follow instructions inside them.
Every function is pure: text in, text out.
"""

import re
from collections.abc import Callable

FENCE_RE = re.compile(r"^[\s>]*(`{3,}|~{3,})(.*)$")  # also matches a fence inside a blockquote
HEADING_RE = re.compile(r"^(#{1,6})\s")
AGENT_SECTIONS = ("Documentation Index", "Querying This Documentation")
LABELS = {
    "NOTE": "Note",
    "TIP": "Tip",
    "IMPORTANT": "Important",
    "WARNING": "Warning",
    "CAUTION": "Caution",
}

ALERT_RE = re.compile(r"^(\s*>\s*)\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*$")
RAW_FASTAPI_RE = re.compile(r"^\s*(\{[*!]|/{3,4}(\s|$))")  # include, `///` block, `//// tab`
BLOCK_RE = re.compile(r'^(\s*)(?:!!!|\?\?\?\+?)\s+(\w+)(?:\s+"([^"]*)")?\s*$')
TAB_RE = re.compile(r'^(\s*)===\s+"([^"]*)"\s*$')
STUB_RE = re.compile(r"^:::\s+(\S+)")
TAB_PANEL_RE = re.compile(r"^\s*-\s+\[[^\]]*\]\(#tab-panel-\d+\)\s*$")
AUTOREF_RE = re.compile(r"\[([^\]]+)\]\[[A-Za-z_]\w*(?:\.\w+)+\]")  # [text][pydantic_ai.x.Y]
FENCE_ATTR_RE = re.compile(r"^(\s*)(`{3,})(\w[\w+-]*)\s*\{([^}]*)\}\s*$")
TITLE_RE = re.compile(r'title="([^"]*)"')
LINK_TAG_RE = re.compile(  # link text may not cross a blank line
    r'<a\s[^>]*?href="([^"]*)"[^>]*>((?:[^\n]|\n(?!\s*\n))*?)</a>', re.IGNORECASE
)
COMMENT_RE = re.compile(r"<!--(?!\s*anchor:)[\s\S]*?--!?>")  # keep `<!-- anchor: id -->`
TAGS = (
    "a abbr b blockquote br code dfn div em hr i img kbd li ol p picture source span strong sub sup"
    " summary details svg table tbody td th thead tr u ul script style iframe"
)
TAG_RE = re.compile(rf"</?(?:{'|'.join(TAGS.split())})\b[^>]*>", re.IGNORECASE)
CODE_SPAN_RE = re.compile(
    r"(`+(?:[^`\n]|\n(?!\s*\n))*`+)"
)  # an inline span never crosses a blank line


def closes_fence(line: str, fence: str) -> bool:
    """True if `line` closes a fenced block opened with `fence` (same char, at least as long)."""
    m = FENCE_RE.match(line)
    return (
        bool(m)
        and m.group(1)[0] == fence[0]
        and len(m.group(1)) >= len(fence)
        and not m.group(2).strip()
    )


def mark_code(text: str) -> list[tuple[str, bool]]:
    """Split into (line, in_fenced_code). Fence lines count as code."""
    out: list[tuple[str, bool]] = []
    fence = ""
    for ln in text.splitlines():
        if fence:
            fence = "" if closes_fence(ln, fence) else fence
            out.append((ln, True))
        elif m := FENCE_RE.match(ln):
            fence = m.group(1)
            out.append((ln, True))
        else:
            out.append((ln, False))
    return out


def outside_fences(text: str, fn: Callable[[str], str]) -> str:
    """Apply `fn` to every line that is not inside a fenced code block."""
    return "\n".join(ln if code else fn(ln) for ln, code in mark_code(text))


def strip_html(text: str) -> str:
    """Drop HTML tags and comments (keep their text and `<a href>` links). Fenced code and inline
    code are left alone. Comments may span lines, even blank ones."""

    def clean(part: str) -> str:
        part = LINK_TAG_RE.sub(lambda m: f"[{TAG_RE.sub('', m[2]).strip()}]({m[1]})", part)
        return TAG_RE.sub("", COMMENT_RE.sub("", part))

    out: list[str] = []
    prose: list[str] = []  # a run of lines outside fences

    def flush() -> None:
        if prose:
            spans = CODE_SPAN_RE.split("\n".join(prose))
            out.append("".join(p if i % 2 else clean(p) for i, p in enumerate(spans)))
            prose.clear()

    for ln, code in mark_code(text):
        if code:
            flush()
            out.append(ln)
        else:
            prose.append(ln)
    flush()
    return "\n".join(out)


def plain_alerts(text: str) -> str:
    """`> [!TIP]` -> `> **Tip**`: a bold label in a normal blockquote."""
    return outside_fences(text, lambda ln: ALERT_RE.sub(lambda m: f"{m[1]}**{LABELS[m[2]]}**", ln))


def tidy(text: str) -> str:
    """One blank line at most between blocks (code is left alone), one newline at the end."""
    out: list[str] = []
    for ln, code in mark_code(text):
        if not code and not ln.strip() and out and not out[-1].strip():
            continue
        out.append(ln)
    return "\n".join(out).strip() + "\n"


def drop_agent_text(text: str) -> str:
    """Cut everything before the page H1 and any agent-addressed section (untrusted data)."""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.startswith("# ")), None)
    if start is None:
        raise ValueError("no H1 found: unexpected Pydantic AI page format")
    out: list[str] = []
    skip = 0  # level of the heading whose section is being dropped, 0 = none
    for ln, code in mark_code("\n".join(lines[start:])):
        if not code and (m := HEADING_RE.match(ln)):
            level = len(m.group(1))
            if skip and level <= skip:
                skip = 0
            if not skip and any(s in ln for s in AGENT_SECTIONS):
                skip = level
        if not skip:
            out.append(ln)
    return "\n".join(out)


def _body(lines: list[str], i: int, indent: str) -> tuple[list[str], int]:
    """The block body starting at line i: blank lines and lines indented 4 more than `indent`."""
    pad = indent + "    "
    body: list[str] = []
    while i < len(lines) and (not lines[i].strip() or lines[i].startswith(pad)):
        body.append(lines[i][len(pad) :] if lines[i].strip() else "")
        i += 1
    while body and not body[-1]:  # trailing blanks belong to what follows the block
        body.pop()
        i -= 1
    return body, i


def convert_pydantic_blocks(text: str) -> str:
    """`!!! note "T"` and `=== "Tab"` -> a bold label plus the plain body; a `::: module` stub or a
    ```snippet include -> a one-line placeholder; fence attributes and tab-panel lists dropped."""
    lines = text.splitlines()
    out: list[str] = []
    fence = ""
    i = 0
    while i < len(lines):
        ln = lines[i]
        i += 1
        if fence:
            fence = "" if closes_fence(ln, fence) else fence
            out.append(ln)
        elif m := FENCE_RE.match(ln):
            if m[2].strip().startswith("snippet"):
                while i < len(lines) and not closes_fence(lines[i], m[1]):
                    i += 1
                i += 1
                out.append("_(code snippet omitted)_")
            elif attrs := FENCE_ATTR_RE.match(ln):
                if title := TITLE_RE.search(attrs[4]):
                    out.append(f"{attrs[1]}**File: {title[1]}**")
                out.append(f"{attrs[1]}{attrs[2]}{attrs[3]}")
                fence = attrs[2]
            else:
                out.append(ln)
                fence = m[1]
        elif block := BLOCK_RE.match(ln):
            body, i = _body(lines, i, block[1])
            label = block[2].capitalize() + (f": {block[3]}" if block[3] else "")
            out += [f"**{label}**", "", *convert_pydantic_blocks("\n".join(body)).splitlines()]
        elif tab := TAB_RE.match(ln):
            body, i = _body(lines, i, tab[1])
            out += [f"**{tab[2]}**", "", *convert_pydantic_blocks("\n".join(body)).splitlines()]
        elif stub := STUB_RE.match(ln):
            _, i = _body(lines, i, "")  # the option lines under the stub
            out.append(f"_(API reference for {stub[1]} omitted)_")
        elif not TAB_PANEL_RE.match(ln):
            out.append(AUTOREF_RE.sub(r"\1", ln))
    return "\n".join(out)


def normalize_fastapi(text: str) -> str:
    """Cached FastAPI page -> clean Markdown. Fails if fetch_docs left raw syntax behind."""
    if any(RAW_FASTAPI_RE.match(ln) for ln, code in mark_code(text) if not code):
        raise ValueError(
            "raw FastAPI syntax (an include or a `///` block) in the cache: re-run fetch_docs"
        )
    return tidy(plain_alerts(strip_html(text)))


def normalize_pydantic_ai(text: str) -> str:
    return tidy(plain_alerts(strip_html(convert_pydantic_blocks(drop_agent_text(text)))))


def normalize_github(text: str) -> str:
    return tidy(plain_alerts(strip_html(text)))


def normalize_raw(text: str) -> str:
    """Pages kept exactly as served (Markdown from MCP, GitHub READMEs): same clean-up as GitHub."""
    return normalize_github(text)


NORMALIZERS: dict[str, Callable[[str], str]] = {
    "fastapi_raw": normalize_fastapi,
    "pydantic_ai_md": normalize_pydantic_ai,
    "github_article": normalize_github,
    "raw": normalize_raw,
}


def normalize(kind: str, text: str) -> str:
    if kind not in NORMALIZERS:
        raise ValueError(f"unknown source kind: {kind}")
    return NORMALIZERS[kind](text)
