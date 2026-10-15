## What changed

The whole site shell now uses the same GitHub dark dimmed colors that lesson text already had. Only one stylesheet changed in a big way:

- `app/static/css/app.css` now holds nine color tokens (canvas, raised surface, text, muted text, blue, border, learning amber, mastered green, wrong red) and every rule uses them. The header is a quiet bar with a near-white site name and muted nav links. Each track is one raised card, and each lesson is a row you can scan: title, minutes, then a small rounded status pill at the right edge. Blue now only means "link or hover". Buttons, inputs, text boxes, and dropdowns on the other pages share the same surface, border, and corner radius, and keyboard focus gets a 2px blue outline.
- `app/templates/home.html` gained two class names (`track-card` and `track-lessons`) so track lessons can be styled without touching any other list, such as the sources list at the bottom of a lesson. No words, links, routes, or JavaScript changed, and nothing inside `.markdown-body` (the lesson prose) is restyled.
- `tests/test_ui_css.py` is a new guard test: it fails if a color outside the nine tokens appears, if a selector the quiz/review/tutor JavaScript depends on disappears, or if a rule starts styling inside `.markdown-body`.

## Why

The Tracks page looked like a different site from the lessons: blue link text everywhere, bullets, and status boxes with only colored borders. Now the shell matches the markdown, and the test keeps it that way.

Checks run: `pytest` (832 passed), `ruff check`, `ruff format --check`, `ty check`, plus a local run of the site with screenshots of the Tracks page and a lesson.

Read first: `app/static/css/app.css`, the `.track-card` and `.track-lessons` rules.

Closes #142

🤖 Generated with [Claude Code](https://claude.com/claude-code)
