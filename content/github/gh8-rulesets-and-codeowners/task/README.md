# Task: add CODEOWNERS and a ruleset to your practice repo

You will add a `CODEOWNERS` file that gives you every `.yml` file, create a second ruleset on `main` called `main-guard`, and open a pull request that edits a `.yml` file. Then you look at what GitHub shows for the owner.

You work in your **practice repo**, the one in `PRACTICE_REPO` from lesson GH1. It is a public repo. It already has a ruleset from GH1, and a job called `checks` from GH2. If you do not have those yet, stop here and do GH1 and GH2 first. The new ruleset requires `checks`, and a pull request would wait for it forever if no such job exists. The checker below needs the practice repo.

The commands use bash or zsh quoting. On Windows, open a Git Bash terminal in VS Code.

Nothing in this task is a secret. Your GitHub username is public. Never paste a token or a password anywhere.

## 1. Open the repo and make a branch

1. In VS Code, choose **File > Open Folder** and open your practice repo folder.
2. Open the terminal with **View > Terminal**.
3. Run:

```bash
git switch main
git pull
git switch -c add-codeowners
```

## 2. Add the CODEOWNERS file

1. Find your username. This prints it:

```bash
gh api user --jq .login
```

2. In the Explorer, create the file `.github/CODEOWNERS`. Type the whole path in the new-file box and VS Code makes the folder for you.
3. Put this in it. Replace `YOUR-USERNAME` with the name from step 1, and keep the `@`:

```text
# I own every YAML file.
*.yml @YOUR-USERNAME
```

Two things to notice. The pattern `*.yml` matches `.yml` files in every folder, and it does not match `.yaml`. And the file lives in `.github/`, one of the three places GitHub looks.

4. Commit it, open a pull request, and merge it. GitHub reads the file from the base branch, so it has to be on `main` before it can help any other pull request:

```bash
git add .github/CODEOWNERS
git commit -m "chore: add CODEOWNERS"
git push -u origin add-codeowners
gh pr create --fill
gh pr checks --watch
gh pr merge --squash --delete-branch
git switch main
git pull
```

5. Look at the file on GitHub. Run `gh repo view --web`, open `.github/CODEOWNERS`, and check that no line is marked as an error. A bad line is skipped, so a typo means no owner.

## 3. Create the main-guard ruleset

Your GH1 ruleset already protects `main`. You will add a second one. Rulesets layer, so both apply.

1. Run this from inside your practice repo folder. It sends the JSON on standard input. `gh` fills in `{owner}` and `{repo}` from the repo in the current folder:

```bash
gh api --method POST repos/{owner}/{repo}/rulesets --input - <<'EOF'
{
  "name": "main-guard",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [],
  "conditions": {
    "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] }
  },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": false,
        "required_status_checks": [{ "context": "checks", "integration_id": 15368 }]
      }
    }
  ]
}
EOF
```

Run it once. If you run it twice, GitHub may refuse the second one with a validation error. If you do end up with an extra ruleset, delete it in **Settings > Rules > Rulesets**.

2. List your rulesets. You should see `main-guard`, and the GH1 ruleset next to it:

```bash
gh ruleset list
```

3. See which rules apply to `main`:

```bash
gh ruleset check main
```

Some rules appear twice, once for each ruleset. That is layering. Find `deletion`, `non_fast_forward`, `pull_request` and `required_status_checks` with the context `checks`.

4. Look at the settings of your new ruleset. Put its id in place of `ID`:

```bash
gh ruleset view ID
```

Find the line about the bypass list. Nobody can bypass `main-guard`.

Leave `require_code_owner_review` as `false`. You are the only owner, and you will be the author of the pull request in the next step. Nobody can approve their own pull request. If you turned the requirement on, you could never merge.

## 4. Open a pull request that edits a YAML file

1. Make a branch and a new file:

```bash
git switch -c edit-yaml
printf 'note: owned by me\n' > practice-owned.yml
git add practice-owned.yml
git commit -m "chore: add a YAML file I own"
git push -u origin edit-yaml
gh pr create --fill
```

2. Open the pull request in the browser with `gh pr view --web`. Look at three places and write down in your own words what you see:

- The **Reviewers** section in the right sidebar. Is anyone asked for a review?
- The **Files changed** tab. Is there any sign of an owner?
- The merge box. Does it wait for your approval?

You wrote this pull request, and you are the owner. GitHub's docs say that a pull request author cannot approve their own pull request. This lesson did not check what GitHub shows an owner who is also the author, so write down what you really see. The point is to see where owners show up, and why a one-person repo cannot require them.

3. Wait for `checks` and merge the pull request:

```bash
gh pr checks --watch
gh pr merge --squash --delete-branch
git switch main
git pull
```

Your ruleset requires `checks`. If the merge box says it is waiting for a status to be reported, the job name does not match. See GH2.

## 5. See the owner on a file

After the merge, open the file on GitHub with `gh repo view --web`, browse to `practice-owned.yml`, and hover over the shield icon in the file header. The docs say the tool tip names the owner and the CODEOWNERS line it comes from.

## 6. Optional: read the rules back

Run `gh api repos/{owner}/{repo}/rules/branches/main --jq '[.[].type]'`. It prints the rule types that apply to `main`. These are the same rules the checker looks at.

## Check my work

Set `PRACTICE_REPO` in `.env`, then press **Check my work**. It runs read-only `gh` calls and never changes anything:

- The rules on `main` include `pull_request` and `required_status_checks`.
- The required status checks on `main` include one named `checks`.
- The rules on `main` include `deletion` and `non_fast_forward`.
- The file `.github/CODEOWNERS` has a line that starts with `*.yml`, then spaces, then an owner that starts with `@`. A line that starts with `#` does not count. The check does not confirm that the owner is you, so make sure you replaced the placeholder with your own username.
- At least one pull request, open or closed, changed a file called `practice-owned.yml`.
