## What changed

The think-deeper grader reads your answer three times. Before, a criterion counted as met only if all three readings said met. Now it counts as met when at least two of the three say met, and it gets an `uncertain` flag whenever the three did not all agree.

- `app/agents/grader.py` (`grade_answer`): per criterion, `met` is a majority vote (2 of 3) and `uncertain` is true for any 2-1 or 1-2 split. A 3-0 or 0-3 split is certain. The `evidence` shown to you comes from the first sample that agrees with the majority, not just the first sample. An unmet criterion still gets its hint from that same sample, or the authored hint for that position when no sample can give one. A met criterion gets no hint.
- Progress: there was no separate "uncertain" state in the route. The old rule (all three must agree) was what made a 2-of-3 pass look like a failure. With the majority rule, `all_met` is true for a 2-of-3 pass, so the model answer shows and the retry button goes away, exactly as for a clean pass.
- `app/static/js/deeper.js` and `app/templates/partials/deeper.html`: a met criterion shows a tick and an unmet one a cross, as before. Any criterion with `uncertain` also gets a small "uncertain" label and one line: "The grader's three readings disagreed; your answer may be borderline." So a criterion that failed 1-2 shows a cross, the "uncertain" badge and its hint. The old "?" mark and "(not sure)" text are gone. The text is added with `textContent` only. The intro line of the section now explains the rule.
- Review queue: grading now creates the cards. `post_deeper` in `app/routes/deeper.py` calls `record_criterion` for every criterion after each graded attempt, the same way the quiz route calls `record_quiz_attempt`. An unmet criterion makes a card (rated Again). A criterion that is met but uncertain makes no card. I kept it simple on purpose: `record_criterion` looks only at `met`. The issue text said the queue could treat an uncertain criterion as a weak point; that is a possible later step. The card key is `<lesson>:<question>#<criterion>` and the store keeps one row per key, so grading the same criterion again updates that card (unmet: Again; met later: a Good review of the existing card) and never adds a second one. A flagged attempt (an "ignore the rubric" answer) is scored 0 but makes no cards, because it is not a real answer.
- Feedback line: the one-line `feedback` used to come from sample 0 no matter what. If sample 0 said "great job" and the other two said a criterion was unmet, you saw a cheerful line next to a cross. Now it comes from the first sample whose verdicts match the majority result on the most criteria. That is a best effort, the sample least likely to contradict the vote, not a guarantee: if every sample ties, the first one wins. The hints already come from agreeing samples, one per unmet criterion, so they stay in step with the crosses.
- `docs/SPEC.md`: the grader wording and feedback rule (section 6.3), the card rule (section 9), the API response shape (section 15) and the acceptance row (section 23) now say what the code does. The API line listed a per-criterion `feedback` that the code never sent; the real shape has `feedback` and `hints` at the top level.
- `evals/run_grader.py` needed no change: it reads only `met` per criterion. It calls the real model, so I checked that it imports and that its dataset loads, and did not run it.

## Why

SPEC section 6.3 says the grader takes the majority of three samples. The code was stricter than that, so a learner whose answer passed 2 of 3 readings was told it failed. The vote exists to smooth out the noise of one model reading. Requiring all three to agree throws that benefit away and punishes the learner for the grader's noise. The `uncertain` flag keeps the honest part: it tells you the verdict was close.

## Read first

`grade_answer` in `app/agents/grader.py`, the loop over `question.rubric`. It is about ten lines. Then `tests/test_grader.py`: `test_two_of_three_is_met_but_uncertain`, `test_one_of_three_is_not_met_but_uncertain` and `test_unanimous_splits` script the 2-1, 1-2, 3-0 and 0-3 splits with `FunctionModel`, and `test_feedback_comes_from_the_sample_closest_to_the_majority` covers the feedback line. The review-queue tests (`test_one_of_three_makes_a_due_review_card`, `test_two_of_three_makes_no_review_card`, `test_regrading_updates_the_card_instead_of_adding_one`, `test_flagged_attempt_makes_no_review_cards`) post to the real route. The route change in `app/routes/deeper.py` is a four-line loop.

## Good to know

Grades stored before this change keep their old `met` and `uncertain` values, because they are saved as JSON with the same fields. Only new attempts use the majority rule. Review cards from think-deeper grading did not exist before this PR: `record_criterion` was written and tested but the route never called it. Cards appear only for attempts graded after this change.

## Lesson learned

A rule written in the spec ("majority") and a rule written in the code ("all must agree") can drift apart without any test failing, because the tests were written against the code. When you vote across noisy samples, decide what the vote means (`met`) and what the disagreement means (`uncertain`) as two separate facts. Folding both into one flag is what made a pass look like a failure.

Closes #112

🤖 Generated with [Claude Code](https://claude.com/claude-code)
