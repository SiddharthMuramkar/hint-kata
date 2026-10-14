# Runbook: deploy Hint Kata on Vercel

Config lives in `vercel.json`, `.vercelignore`, `.python-version` and `[tool.vercel]` in `pyproject.toml`. Nothing here holds secrets.

## What the owner must do
- [ ] Link the GitHub repo `siddharth-0044/hint-kata` to a new Vercel project (steps below).
- [ ] Set the environment variables below in Project > Settings > Environment Variables.
- [ ] Open the first preview URL and check `/healthz` returns `{"ok": true}`.
- [ ] Before phase 3 (payments): flip production protection (see Deployment Protection) and move to Pro.

## Link the project
1. Sign in at vercel.com with GitHub. Pick Hobby while the site is non-commercial. Hobby forbids commercial use, so move to Pro before selling anything.
2. Click Add New > Project and import the repo.
3. Framework preset: FastAPI. Root directory: `/`. Leave build and install commands empty.
4. Deploy. Vercel finds `app.main:app` in `pyproject.toml`, installs with uv and uses Python 3.13.

## Environment variables (names only)
Set each for Production, Preview and Development as needed. Changes apply to new deployments only.
- `OPENROUTER_API_KEY`, `OPENROUTER_ZDR`
- `TUTOR_MODEL`, `GRADER_MODEL`, `AUTHOR_MODEL`, `JUDGE_MODEL`
- `HINTKATA_DB_PATH=/tmp/hintkata.db` (demo only, see below)
- Later: `DATABASE_URL`, `DATABASE_URL_UNPOOLED` (the Neon integration adds them)
- Later: `PRACTICE_REPO`
- Optional: `LOGFIRE_TOKEN`

Pull them into your local env file from the VS Code terminal:

```
vercel link
vercel env pull
```

Never commit the pulled file. It is git-ignored.

## Deployment Protection
- Standard Protection is the default. Vercel Authentication guards every preview URL, so only your team can open them.
- Production domains stay public under Standard Protection. To keep production owner-only until phase 3, open Project > Settings > Deployment Protection and switch Standard Protection to All Deployments.
- To open production to the public later, switch it back to Standard Protection. That is the one setting to flip.
- For scripts, send the bypass header `x-vercel-protection-bypass`.

## Preview deployments
Every push to a non-production branch and every pull request gets its own preview URL. Vercel posts it on the PR. Preview variables can differ from Production.

## What breaks on Vercel today
- SQLite lives in `/tmp` and is wiped when an instance recycles. Instances do not share it. Progress resets per instance until `PostgresStore` and Neon land. `connect()` creates the parent folder, so the `/tmp` path just works.
- Streaming responses stop at 300 s, the Hobby maximum. `vercel.json` sets `maxDuration` to 300.
- The hands-on checker runs pytest in a `workspace/` folder. The bundle leaves that out and the disk is read-only. Hands-on checks will not work here.
- The bundle limit is 500 MB. `excludeFiles` and `.vercelignore` drop tests, docs, caches, evals and traces.
