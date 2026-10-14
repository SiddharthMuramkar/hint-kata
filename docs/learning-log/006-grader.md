### PR — feat(grader): rubric grader agent and think-deeper UI
What changed: Each "Think deeper" question on a lesson page now has a textbox. When you submit, the server asks a Pydantic AI agent to judge your answer against the question's rubric, three times in parallel. A criterion counts as met or not met only if all three samples agree; if they disagree it shows "?". You get 3 tries in total, and the model answer appears after the third try or once every criterion is met.
Why: One LLM judgement is noisy, so voting makes it steadier. Your answer is wrapped in `<<<ANSWER>>>` markers and declared untrusted. Phrases like "ignore the rubric" or "full marks" are caught by a regex before any model call and returned as a flagged, zero-score attempt.
Also added: an `evals/` folder that scores the grader against hand-labelled answers (with Cohen's kappa) and a manual-only `evals.yml` workflow. Tests use fake models, so CI never calls a real one.
Read first: `app/agents/grader.py` (the agent and the voting), then `app/routes/deeper.py`.

Closes #6

🤖 Generated with [Claude Code](https://claude.com/claude-code)
