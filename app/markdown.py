from markdown_it import MarkdownIt
from markupsafe import Markup, escape
from mdit_py_plugins.anchors import anchors_plugin
from mdit_py_plugins.gfm import gfm_plugin
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

_fmt = HtmlFormatter(nowrap=True)


def _highlight(code: str, lang: str, attrs: str) -> str:
    try:
        lexer = get_lexer_by_name(lang)
    except ClassNotFound:
        return ""  # markdown-it escapes and wraps it
    body = highlight(code, lexer, _fmt)
    return f'<pre class="highlight"><code class="language-{escape(lang)}">{body}</code></pre>'


# "js-default" means html=False. Never use MarkdownIt() or "commonmark": they allow raw HTML.
_md = (
    MarkdownIt("js-default", {"highlight": _highlight})
    .use(gfm_plugin)  # tables, strikethrough, autolinks, tasklists, > [!NOTE] alerts, footnotes
    .use(anchors_plugin, max_level=3)
)


def render_markdown(text: str) -> Markup:
    return Markup(_md.render(text))
