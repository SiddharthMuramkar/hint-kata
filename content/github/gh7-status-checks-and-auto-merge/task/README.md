# Task: require a check, get blocked, then let auto-merge finish the job

You will make sure `checks` is a required check on `main`, turn on auto-merge in your practice repo, and open a pull request with a test that fails on purpose. You watch GitHub block it, arm auto-merge, fix the test, and watch GitHub merge the pull request by itself.

You work in your **practice repo**, the one in `PRACTICE_REPO` from lesson GH1. It is a public repo with a ruleset on `main` (GH1) and a workflow with a job named `checks` (GH2). If you do not have those yet, stop here and do GH1 and GH2 first. The checker below needs them.

The commands use bash or zsh quoting. On Windows, open a Git Bash terminal in VS Code.

## 1. Open the repo and update main

1. In VS Code, choose **File > Open Folder** and open your practice repo folder.
2. Open the terminal with **View > Terminal**.
3. Run:

```bash
git switch main
git pull
```

## 2. See what main already requires

In lesson GH2 you may have made `checks` a required check. Look:

```bash
gh ruleset check main
```

**If the list shows `required_status_checks` with `checks`,** you are done with the rule. Do not add anything. Read it once, and find the two values from the lesson, `integration_id` and `strict_required_status_checks_policy`:

```bash
gh api repos/{owner}/{repo}/rules/branches/main --jq '.[] | select(.type=="required_status_checks") | .parameters'
```

You should see `"integration_id": 15368` (the GitHub Actions app) and `"strict_required_status_checks_policy": false`. Skip to step 3.

**If the list has no `required_status_checks`,** add a second ruleset that holds only this rule. Rulesets stack, so you do not have to edit the first one. The `{owner}` and `{repo}` words are filled in by `gh`, because you are inside the cloned repo:

```bash
gh api -X POST repos/{owner}/{repo}/rulesets --input - <<'EOF'
{
  "name": "require-checks",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [],
  "conditions": {
    "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] }
  },
  "rules": [
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": false,
        "required_status_checks": [
          { "context": "checks", "integration_id": 15368 }
        ]
      }
    }
  ]
}
EOF
```

What the JSON says: the rule applies to the default branch, nobody may bypass it, the required check is named `checks`, and it must come from the GitHub Actions app (`15368`). Strict mode is off. Run `gh ruleset check main` again and you should now see `required_status_checks`.

If the command says the name `require-checks` is taken, change the `"name"` line to something else and run it again.

## 3. Turn on auto-merge

`gh repo edit` changes the repo in your current folder. The first flag allows auto-merge. The second makes GitHub delete a pull request's branch after it merges, because `--delete-branch` does nothing together with `--auto`.

```bash
gh repo edit --enable-auto-merge --delete-branch-on-merge
gh api repos/{owner}/{repo} --jq '{allow_auto_merge, delete_branch_on_merge}'
```

The second command should print `true` for both fields.

## 4. Open a pull request with a test that fails on purpose

1. Make a branch:

```bash
git switch -c add-tests
```

2. In the Explorer, create the file `test_math.py` at the top of the repo, and paste this into it. The `5` is wrong on purpose:

```python
import unittest


class TestMath(unittest.TestCase):
    def test_add(self):
        self.assertEqual(2 + 2, 5)  # wrong on purpose


if __name__ == "__main__":
    unittest.main()
```

3. Open `.github/workflows/ci.yml`. At the bottom of the `checks` job, change the last step from `- run: python3 -c "print('ok')"` to:

```yaml
      - run: python3 -m unittest -v
```

   `python3 -m unittest` finds files that start with `test` and runs them. A failing test makes the step fail, so the job `checks` fails.

4. Commit, push and open the pull request:

```bash
git add test_math.py .github/workflows/ci.yml
git commit -m "test: add a test that fails on purpose"
git push -u origin add-tests
gh pr create --fill
```

5. Watch only the checks that can block the merge:

```bash
gh pr checks --watch --required
```

   Right after you open the pull request, `gh` may print one of two messages. They mean different things:

   - `no checks reported on the '<branch>' branch` means the run has not started yet. Wait ten seconds and run the command again.
   - `no required checks reported on the '<branch>' branch` means checks exist, but none of them counts as required. The usual cause is the name mismatch from the lesson: the name in the rule matches no check that was posted. Go back to step 2 and compare the `context` in the rule with the name of your job, `checks`, letter by letter.

   When it works, `checks` ends with `fail`, and the command exits with code 1.

6. Look at the block. Try a normal merge and read the refusal:

```bash
gh pr merge --squash
gh pr view --json mergeStateStatus --jq .mergeStateStatus
```

   `gh` says the pull request is not mergeable because the base branch policy prohibits the merge, and it suggests `--auto`. The state is `BLOCKED`. That is your required check doing its job.

7. Read why it failed. This is the habit from GH2:

```bash
gh run list --limit 1
gh run view <run-id> --log-failed
```

   You should see `AssertionError: 4 != 5`.

## 5. Arm auto-merge, then fix the test

Arm auto-merge **before** you fix anything. The pull request is blocked right now, so `gh` turns auto-merge on instead of merging. (If you did it after the fix, a fast check could finish first, and then `gh` would merge at once and leave no auto-merge record for the checker.)

```bash
gh pr merge --auto --squash
gh pr view --json autoMergeRequest,mergeStateStatus
```

You should see "will be automatically merged via squash when all requirements are met". The second command shows an `autoMergeRequest` with `"mergeMethod":"SQUASH"` and the state `BLOCKED`. The pull request is still red, so nothing merges. That is what auto-merge does when a check fails: it waits.

Now fix the test. In `test_math.py`, change `5` to `4` and remove the comment:

```python
        self.assertEqual(2 + 2, 4)
```

Then push it:

```bash
git commit -am "test: fix the expected value"
git push
```

## 6. Watch it merge itself

```bash
gh pr checks --watch --required
```

When `checks` shows `pass`, wait a few seconds. GitHub merges the pull request by itself, and deletes the branch. You do not click anything. Confirm it, and tidy your local copy:

```bash
gh pr view --json state,mergedAt --jq '.state'
git switch main
git pull
git branch -D add-tests
git ls-remote --heads origin add-tests
```

The first command prints `MERGED`. The last one prints nothing, because GitHub already deleted the remote branch. You use `-D` for the local branch, because a squash merge made a new commit and plain `-d` thinks the branch is not merged.

## 7. Optional: see the record the checker reads

```bash
gh pr list --state merged --json number,autoMergeRequest --jq '.[] | select(.autoMergeRequest != null)'
```

Your pull request is in the list, with the method and the time auto-merge was enabled. A pull request that you merged by hand shows `null` here.

## Check my work

Set `PRACTICE_REPO` in `.env`, then press **Check my work**. It runs read-only `gh` calls and shows one line per check:

1. **`checks` is a required status check on `main`.** It reads the rules that apply to `main` and looks for the context `checks`. If it fails, repeat step 2 and make sure the check is named exactly `checks`.
2. **Auto-merge is allowed and head branches are deleted on merge.** It expects `true true`. If it prints `false` for one of them, repeat step 3.
3. **A pull request run of a workflow failed.** It counts the runs started by pull requests that ended with `failure`. It expects at least one. This is the proof that you broke CI on purpose in step 4.
4. **A merged pull request has an auto-merge record.** It looks at your merged pull requests for one that went through auto-merge. It expects at least one. If it says `0`, the pull request was merged by hand, or `gh` merged it at once. Do steps 4 to 6 again with a new branch and a different one-line change, and arm auto-merge while the pull request is still blocked.
