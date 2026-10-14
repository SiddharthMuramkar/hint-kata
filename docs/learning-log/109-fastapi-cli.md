## What changed

`uv run fastapi dev` now works on a fresh clone. Before, it printed "please install fastapi[standard]" and quit.

- `pyproject.toml`: added `fastapi-cli==0.0.32` as a direct dependency, next to `fastapi==0.143.0`. `uv.lock` gained four packages and nothing else changed: `fastapi-cli` 0.0.32, `typer` 0.27.3, `rich-toolkit` 0.20.6 and `shellingham` 1.5.4.
- `tests/test_cli.py` (new, no network, no open port): checks that `fastapi.cli` found `fastapi_cli`, that the `fastapi` console script exists in the venv and its `--help` lists `dev` and `run`, that `python -m fastapi_cli --help` works, and that `[tool.fastapi] entrypoint` is `app.main:app`. With `fastapi-cli` removed from the venv, three of the five tests fail. With it installed, all five pass.
- `docs/RESUME.md`: new section E with the run command, the local URL, `fastapi run`, and the `uvicorn` fallback.

`[tool.fastapi] entrypoint = "app.main:app"` was already in `pyproject.toml`, and `CLAUDE.md`, `docs/SPEC.md` and `docs/PLAN.md` already told people to run `uv run fastapi dev`. They were right. The missing piece was the package.

## Why plain `fastapi-cli` and not `fastapi[standard]`

The `fastapi` package ships the `fastapi` command, but the command is only a thin shim. It tries to import `fastapi_cli`, and if that fails it prints the "please install fastapi[standard]" message. The real code lives in the separate `fastapi-cli` package.

`fastapi[standard]` would fix that, but it also installs `fastapi-cloud-cli`, `email-validator` and more that this app does not use. I read the installed `fastapi_cli/cli.py`: it needs `typer`, `rich` and `uvicorn`, and it loads `fastapi_cloud_cli` and `fastapi_new` only inside `try/except ImportError`. `uvicorn[standard]==0.54.0` is already pinned, so plain `fastapi-cli` is enough. Its own `[standard]` extra would add only `fastapi-cloud-cli`, so I did not use it.

Checked by hand: `uv run fastapi dev` served `/` and `/healthz` on port 8000, and `uv run fastapi run --port 8765` served both on port 8765. Both servers were stopped afterwards. `uv run uvicorn app.main:app --reload` also serves `/healthz`.

## Read first

`pyproject.toml` (one added line), then `tests/test_cli.py`. The first test explains the failure: `fastapi.cli.cli_main` is `None` when `fastapi-cli` is missing.

## Lesson learned

Pin the CLI you tell people to run. The docs said `uv run fastapi dev`, but the lock file never contained the package that makes that command work, and no test noticed. Whenever a doc tells someone to run a command, check that the command's package is a direct dependency, and add a small test so it cannot quietly disappear.

Closes #109

🤖 Generated with [Claude Code](https://claude.com/claude-code)
