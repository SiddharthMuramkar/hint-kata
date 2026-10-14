This change adds the first working version of the website. It is a small FastAPI app that shows a home page with three placeholder tracks, a licenses page, and a health check at /healthz. Every page shares one base template with a dark theme that borrows its colours from GitHub's dimmed dark palette. We added a Markdown renderer that turns lesson text into HTML, and it refuses raw HTML on purpose, so a tricky tutor answer cannot inject a script into the page. Code blocks are coloured with Pygments. All the libraries we will need in phase 1 are now pinned in one place, so later tasks will not touch pyproject.toml. Read app/markdown.py first: it is short, and its one line choosing the "js-default" setting is the safety switch that matters most. Tests check the pages, the CSS file, and that script tags and javascript: links never come out of the renderer.

Closes #2

🤖 Generated with [Claude Code](https://claude.com/claude-code)
