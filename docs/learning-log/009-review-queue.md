Wrong answers now come back. When you miss a quiz item, the app makes a review card for it and schedules the next look with FSRS, a spaced-repetition algorithm that spaces reviews further apart as you remember. How you answered sets the rating: wrong is Again, a right second try or a guess is Hard, a right answer is Good, and a fast, sure, right answer is Easy. If you were sure and still wrong, the card is never pushed more than a day out, because that is the belief most worth fixing. The new Today page lists what is due, grouped by lesson, and lets you answer right there; the nav link shows how many are due. A right first try creates no card, so you are only quizzed on what you missed. Read `app/review.py` first: the rating table, the card scheduling and the lookup from a stored card back to lesson content all live there, and `app/routes/review.py` is a thin wrapper around it.

Closes #9

🤖 Generated with [Claude Code](https://claude.com/claude-code)
