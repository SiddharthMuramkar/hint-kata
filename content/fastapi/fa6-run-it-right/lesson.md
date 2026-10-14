---
id: fa6-run-it-right
track: fastapi
title: "Run it right: uv, fastapi dev / fastapi run, entrypoints"
minutes: 20
pins:
  fastapi: "0.143.0"
  fastapi-cli: "0.0.32"
  uv: "0.13"
sources:
  - fastapi-tutorial
  - fastapi-fastapi-cli
  - fastapi-tutorial-first-steps
  - fastapi-deployment-versions
---
You wrote an app. Now you have to start it. The `fastapi` command does that, and it needs two things from you: where your app lives, and which mode to run it in. This lesson makes both explicit. It also fixes the FastAPI version, so the app keeps working next month.

One sentence is the whole mental model: **the `fastapi` command takes an import string like `main:app`, imports your app from it, and runs it in dev mode (for you, while you code) or in run mode (for a server).** The import string is the one thing it must have.

The rest of the lesson is detail on that: how a project gets set up, what each mode changes, how the command finds the import string, and how to stop the version from drifting. The last section reads this site's own files and checks them against all of that.

## Start a project with uv

uv is the tool that manages Python projects here. It makes the `pyproject.toml` file, the virtual environment and a lock file. [Install uv](https://docs.astral.sh/uv/getting-started/installation/) first. Then open a terminal (in VS Code: Terminal, then New Terminal) and run three commands.

```console
$ uv init awesome-project --bare
$ cd awesome-project
$ uv add "fastapi[standard]"
```

- `uv init awesome-project --bare` makes a new folder with one file in it, `pyproject.toml`. Without `--bare`, uv also writes starter files you do not need here.
- `uv add` makes a virtual environment in `.venv`, writes the dependency into `pyproject.toml`, and writes `uv.lock`. The lock file holds the exact version of every package uv chose. Someone who installs from it later gets the same versions.
- `uv run` runs a command inside that environment. You never activate the environment by hand. Every command in this lesson starts with `uv run`.

The part in square brackets matters. `fastapi[standard]` is FastAPI plus a set of extras. Two of them are the `fastapi` command itself (the package `fastapi-cli`) and Uvicorn, the server that does the real work. A third is a command for FastAPI Cloud, the hosting service from the FastAPI team. You can ignore it, or leave it out with `fastapi[standard-no-fastapi-cloud-cli]`.

Plain `fastapi` has none of these. If a project lists only plain `fastapi`, then `uv run fastapi dev` stops with a message that asks you to install `fastapi[standard]`. A Python traceback follows it, ending in a `RuntimeError` that repeats the same message. The traceback looks scary, but the message is the whole story. We ran it and saw both. The last section shows where.

If you want only the command, you can list the package `fastapi-cli` by itself, next to `fastapi`. We checked that this starts `fastapi dev` too.

One more fact about `uv add`. It writes only a lower bound. If the newest FastAPI is `0.143.1`, your file gets `fastapi[standard]>=0.143.1`, with no upper limit. The pin section fixes that.

More: [Tutorial - User Guide](https://fastapi.tiangolo.com/tutorial/), the part called "Install FastAPI".

## Your first app and its docs

Put this in a file called `main.py` in the project folder.

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Hello World"}
```

- `app` is one `FastAPI` object. Everything else attaches to it.
- `@app.get("/")` is a decorator. It says: a request that uses the GET method and goes to the path `/` calls the function below it.
- The function returns a `dict`, and FastAPI sends it as JSON.
- The official page writes `async def`. Plain `def` works too. Pick one and stay with it.

Start it.

```console
$ uv run fastapi dev
```

Open `http://127.0.0.1:8000`. You see `{"message":"Hello World"}`. FastAPI also builds three more pages for you, with no extra code.

- `/docs` is a page where you can read every route and try it in the browser.
- `/redoc` is a second page for the same job, in another style.
- `/openapi.json` is the raw description of your API, in a standard format called OpenAPI. It lists every path, with the methods and parameters of each. Both pages above are drawn from it. Other tools can read it too, for example to generate client code.

In our run, the `/openapi.json` of this one-route app had a `paths` entry for `/` with a `get` inside. Keep that file in mind. A route that is missing from it is a route FastAPI does not know about. The hands-on task checks it.

More: [First Steps](https://fastapi.tiangolo.com/tutorial/first-steps/).

## Dev mode and run mode

The `fastapi` command has two modes. They start the same app the same way. They differ in their defaults. The built-in help says it plainly: `fastapi dev` is `fastapi run` with reload on and the address set to `127.0.0.1`.

| | `fastapi dev` | `fastapi run` |
| --- | --- | --- |
| Meant for | you, while you write code | servers and containers |
| Auto-reload | on | off |
| Listens on | `127.0.0.1` | `0.0.0.0` |
| `FASTAPI_ENV` | set to `development`, if not set already | left alone |
| Extra option | none | `--workers`, for more than one process |

Here is what each row means.

**Auto-reload.** The command watches your project files. When you save one, it restarts the app. We tested it. We started `fastapi dev`, changed the text in `main.py`, waited a few seconds, and the next request got the new text. We did the same edit under `fastapi run`, and it kept serving the old text. Reload uses more resources and can be less stable than a plain start. That is why it is only for development.

**The address.** `127.0.0.1` means "this computer only". Nobody else on your network can connect. `0.0.0.0` means "every network address this machine has". Anyone who can reach the machine can reach the app. In a container that is what you want. On a laptop, usually not. So use `fastapi dev` while you code. In real deployments a proxy in front of the app normally handles HTTPS.

**Flags change the defaults.** The modes are only bundles of defaults. `--host` and `--port` set the address and the port. The port is 8000 unless you pass `--port` or set the `PORT` environment variable. `--reload` and `--no-reload` turn reload on or off. We checked two of these. `fastapi dev --host 0.0.0.0` listened on all addresses. `fastapi run --host 127.0.0.1` listened on this machine only. `--workers` is only on `run`. The built-in help calls it mutually exclusive with reload. When we passed both anyway, the app started, and Uvicorn logged a warning that `workers` is ignored while reloading.

**`FASTAPI_ENV`.** This is an environment variable. Before it imports your app, dev mode sets it to `development`, but only if it has no value yet. So `FASTAPI_ENV=staging uv run fastapi dev` gives your app the value `staging`. `fastapi run` does not touch it. We ran an app that printed the variable, and under `fastapi run` it was not set at all.

```python
import os

env = os.environ.get("FASTAPI_ENV")  # "development" under dev; None under run if nothing set it
```

The usual values are `development` and `production`. Your own startup code can read the variable, for example to turn on more logging. If it needs to know it is in production, set `FASTAPI_ENV=production` yourself. `fastapi run` will not do it for you.

Both modes use Uvicorn underneath. We ran all of this with `fastapi-cli` 0.0.32.

More: [FastAPI CLI](https://fastapi.tiangolo.com/fastapi-cli/), the parts called "fastapi dev" and "fastapi run".

## Entrypoints: how the command finds your app

The command has to import your app object. For that it needs an **import string**: a module path, a colon, then a variable name.

```text
main:app            means   from main import app
backend.main:app    means   from backend.main import app
```

Dots go between folders and the file name. A colon goes between the module and the variable. There are no slashes and no `.py`. In the second line, `backend` is a folder with an `__init__.py` file in it, and `main.py` sits inside it.

**If you give the command nothing, it guesses.** From its built-in help:

- It takes the first of these files that exists: `main.py`, `app.py`, `api.py`, `app/main.py`, `app/app.py`, `app/api.py`.
- In that module it looks for a variable named `app`, then one named `api`. If neither exists, it takes the first FastAPI object it finds. We tried a file with `application = FastAPI()` and it found it.
- If it finds nothing, it stops and says so. It either could not find a default file, or could not find a FastAPI app in the module.

The start-up message says when it had to guess. In our run it printed `main:app` marked as auto-discovered, plus a hint to add the table you are about to see.

Guessing is fine for a tiny project. It gets shaky when the file has another name, when there are two apps, or when the project is a package. Then you say it out loud. There are three ways.

| Way | Example | Where it lives |
| --- | --- | --- |
| `pyproject.toml` | `entrypoint = "main:app"` under `[tool.fastapi]` | in the repo |
| A path argument | `uv run fastapi dev main.py` | only in what you type |
| `--entrypoint` (or `-e`) | `uv run fastapi dev --entrypoint main:app` | only in what you type |

The pyproject version is two lines.

```toml
[tool.fastapi]
entrypoint = "main:app"
```

We tested which one wins. We pointed pyproject at one app and then ran the command with a path, and then with `--entrypoint`, pointing at another. Both times the command used what we typed. So the flag is good for a one-off. The pyproject entry is the default for everything else.

**Why pyproject is the better home.**

- You write it once, in the repo. Plain `uv run fastapi dev` works the same for everybody, and nobody has to remember a path or a flag.
- Other tools read it. The docs warn that tools like the VS Code extension and FastAPI Cloud may not find an app that is only named on the command line.
- It is explicit. If the name in the file does not match your code, you get an error. A guess can silently pick the first FastAPI object in a module, and that may not be the one you meant.

Here is what a wrong name looks like. Say pyproject says `main:application` but `main.py` has `app`.

- `fastapi run` stops. It prints that the attribute was not found in the module, and exits with an error code. A container would stop with it.
- `fastapi dev` prints the same error but keeps running, with its reloader still up. The command still being there does not mean the app loaded. Read the error line.

More: [FastAPI CLI](https://fastapi.tiangolo.com/fastapi-cli/), the parts called "Configure the app entrypoint in pyproject.toml" and "fastapi dev with path or with --entrypoint CLI option".

## Pin the version

FastAPI's version numbers still start with `0`. The versions page explains what that means. In a project that has not reached `1.0`, any release may bring a breaking change. Still, there is a rule of thumb. A **patch** is the last number, like the `1` in `0.143.1`. It is for bug fixes and should not break you. A **minor** is the middle number, like the `143`. It may add features, and it may break things.

So you pin FastAPI to one minor.

```toml
[project]
dependencies = [
    "fastapi[standard]>=0.143.0,<0.144.0",
]
```

- `>=0.143.0` means `0.143.0` or newer.
- `<0.144.0` means older than `0.144.0`. The next minor is out.
- Patches stay in. We checked: under this range uv installed `0.143.1`, a patch that came after the version this lesson was written against.

The pin can also be one version only, like `fastapi==0.143.0`. The docs show both forms. A range lets bug fixes in. An exact pin keeps everything still.

Set the range in one command.

```console
$ uv add "fastapi[standard]>=0.143.0,<0.144.0"
```

Why not plain `uv add "fastapi[standard]"`? As you saw, it writes a lower bound and nothing else. The lock file holds the version you have today. But a later `uv lock --upgrade` is allowed to pick the newest FastAPI, including a new minor, and your app can break on a day you did not plan for.

**How to upgrade on purpose.** Have tests first (lesson FA2 is about that). Then raise the pin to the new minor, run the tests, and fix what breaks. Commit the pin and the new lock file together.

**What not to pin.** Do not pin Starlette. Each FastAPI release already asks for a Starlette that works with it. Pydantic is different. You can pin it to a version that works for you, and the docs use `pydantic>=2.7.0,<3.0.0` as the example.

More: [About FastAPI versions](https://fastapi.tiangolo.com/deployment/versions/).

## How this site runs

This site is a FastAPI app, so everything above applies to it. Here is what its own files say, as of when this lesson was written.

- **`app/main.py`** makes the app with `app = FastAPI(lifespan=lifespan)`. It sits at the top level of the file `app/main.py`, and `app/` is a package. So the import string is `app.main:app`. The package and the variable are both called `app`. The part before the colon is the module, the part after is the variable.
- **`pyproject.toml`** has `[tool.fastapi]` with `entrypoint = "app.main:app"`. That is the rule from the entrypoint section. A second table, `[tool.vercel]`, holds the same string. It is for hosting on Vercel later, and `docs/runbooks/vercel.md` covers it.
- **The pins** are exact. When this lesson was written, `fastapi==0.143.0` and `uvicorn[standard]==0.54.0` were listed. The fix described below adds `fastapi-cli==0.0.32` next to them.
- **`CLAUDE.md`** says to start the site with `uv run fastapi dev`. With `fastapi-cli` installed, that command finds `app.main:app` from the pyproject entry, with no path. We checked by adding `fastapi[standard]` for a single run with `uv run --with "fastapi[standard]==0.143.0" fastapi dev`. It printed `app.main:app` as the import string and `/healthz` answered `{"ok": true}`.
- **`docs/RESUME.md`** is the prompt you paste to carry on building in a Claude Code session. When this lesson was written, it had no command for starting the site. The fix described below adds a short "run the site" section to it.

There was one catch, and it is the trap from the first section. When this lesson was written, the site's dependency line was plain `fastapi`, with no `[standard]`, and the lock file had no `fastapi-cli`. When we ran plain `uv run fastapi dev` in the repo, it stopped with the message that asks for `fastapi[standard]`, followed by the traceback. The same project started fine with Uvicorn directly: `uv run uvicorn app.main:app`. Uvicorn is a direct dependency, and the site answered `/healthz` that way.

The repo has since listed `fastapi-cli` itself, pinned to the version this lesson was tested with. The `[standard]` extra would also have worked. It brings extra packages this site does not use, so the repo took the smaller route. The general fix is the same either way: get `fastapi-cli` installed, with `fastapi[standard]` or with `fastapi-cli` on its own.

Check it yourself. Run `uv run fastapi dev` in the repo. You should see the dev banner with `app.main:app` as the import string. If you see the install message instead, your environment is missing the package. Run `uv sync --locked --all-groups` and try again.

Sources (FastAPI 0.143.0, MIT licence, © 2018 Sebastián Ramírez; adapted and rewritten): [Tutorial - User Guide](https://fastapi.tiangolo.com/tutorial/), [FastAPI CLI](https://fastapi.tiangolo.com/fastapi-cli/), [First Steps](https://fastapi.tiangolo.com/tutorial/first-steps/), [About FastAPI versions](https://fastapi.tiangolo.com/deployment/versions/). This site is not affiliated with FastAPI.
