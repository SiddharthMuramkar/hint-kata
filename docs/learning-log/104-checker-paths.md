## What changed

The hands-on checker builds file paths from the lesson id that comes in the URL. Now it checks the id first and checks every path after it is built.

- `LESSON_ID_RE` and `validate_lesson_id` in `app/checker.py`: an id must be 1 to 64 characters, start with a letter or digit, and use only lowercase letters, digits and `-`. Anything else (`..`, `a/b`, an empty string, `Lesson-A`) raises `ValueError`. `find_task_dir` and `prepare_workspace` call it on their first line.
- `_inside(path, root)`: resolves the path (follows `..` and symlinks) and raises `ValueError` unless the result is still under the root. It guards the task folder (under `content/`), the learner workspace (under `workspace/`), and the `starter` and `tests` folders (under the task folder).
- The route in `app/routes/check.py` needed no change. It already returns 404 for an invalid id before any file work, and it still returns 200 with "no hands-on task" for a valid id that has no task (an existing test relies on that).
- Valid ids behave as before. The only difference is that ids with a leading `-` or more than 64 characters are now refused.

## Why CodeQL flagged it

CodeQL follows data from where it enters the app to where it is used. The lesson id enters from the URL, becomes `workspace_root / lesson_id`, and then reaches `workspace.exists()`, `shutil.copytree(...)` and `workspace.resolve()`. Nothing proved the path stayed inside `workspace/`, so it raised three `py/path-injection` alerts. An id like `../../etc` could have pointed anywhere.

## Read first

`app/checker.py`, from `LESSON_ID_RE` down to `prepare_workspace`. Then the new tests at the bottom of `tests/test_checker.py`: bad ids raise before anything is created on disk, a symlink that leaves its root is refused, and bad ids give 404 through the route.

## Lesson learned

Validate before you build a path. Check the input against a strict allow-list first, then build the path, then check that the final path is still inside the folder you meant. The first check keeps bad input out. The second catches what the first missed, such as symlinks.

Closes #104

🤖 Generated with [Claude Code](https://claude.com/claude-code)
