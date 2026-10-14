The lesson page now has a quiz that gives feedback per answer, not just a score. Each wrong option carries its own message and the misconception behind it, so a learner who picks the wrong choice is told why that idea is tempting and why it fails. Before submitting, the learner tags every answer Sure, Think so or Guessing. A wrong answer tagged Sure is flagged as a "surprise", the strongest signal that a belief needs fixing. A wrong first try gets one second try, and the score counts first tries only. Order items are shown in a fixed scrambled order, and the browser sends positions in that scrambled list, so the page never exposes the true order. Read `app/quiz.py` first: it is small, pure functions that are easy to test. `app/routes/quiz.py` wraps it in two endpoints.

Closes #5

🤖 Generated with [Claude Code](https://claude.com/claude-code)
