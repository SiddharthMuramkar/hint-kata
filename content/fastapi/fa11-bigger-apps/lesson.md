---
id: fa11-bigger-apps
track: fastapi
title: "Bigger apps with APIRouter"
minutes: 25
pins:
  fastapi: "0.143.0"
sources:
  - fastapi-tutorial-bigger-applications
  - fastapi-tutorial-path-operation-configuration
  - fastapi-tutorial-metadata
---

A small app fits in one file. Then you add users, then recipes, then an admin area, and the file turns into a scroll. Worse, every recipe route repeats the same path start, the same tag and the same login check. Copy and paste is how one of them ends up without the check.

One sentence is the whole mental model: **an `APIRouter` is a small app that holds routes and shared settings, and `include_router` plugs it into the real app, so the settings are written once and the real app stays a short list of "plug this in here".** If you have used Flask, a router plays the part of a blueprint.

Where the lesson says "we ran" or "we saw", it is an observation from 2026-10-15 (FastAPI 0.143.0, Python 3.13, macOS). The examples use recipes and cooks. The hands-on task uses a pet shop.

## What a router is

A router is made like the app and used like the app. You write `router.get(...)` where you would write `app.get(...)`. The docs call it a "mini FastAPI", and it takes the same options: `dependencies`, `tags`, `responses` and so on.

A layout for a bigger app, with one folder per kind of thing:

```text
shop/
  __init__.py
  main.py            # creates the app and plugs the routers in
  dependencies.py    # checks that several routers share
  routers/
    __init__.py
    recipes.py       # one APIRouter
    cooks.py         # another APIRouter
```

The docs put an `__init__.py` in every folder so the files can import each other, and we do the same here. Here is the smallest working pair. This is our own example, not the page's.

```python
# shop/routers/recipes.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/recipes/")
def list_recipes() -> list[str]:
    return ["soup", "bread"]
```

```python
# shop/main.py
from fastapi import FastAPI

from .routers import recipes

app = FastAPI()
app.include_router(recipes.router)
```

A request to `/recipes/` reaches `list_recipes`, exactly as if it had been declared on `app`. The router is not a separate mini server. Its routes become part of the app, and they show up in the same `/docs` page and in the same OpenAPI file.

Two small points. The variable name `router` is a habit, not a rule. And you can still declare a route straight on `app` next to the included ones. The tutorial does that for the `/` route, and so does the task.

More: [Bigger Applications - Multiple Files](https://fastapi.tiangolo.com/tutorial/bigger-applications/).

## Settings on a router

Look at `list_recipes` again. The path starts with `/recipes/`. Add a second and third route and you will write `/recipes/` again and again. Move the shared parts to the router.

```python
# shop/dependencies.py
from typing import Annotated

from fastapi import Header, HTTPException


def need_key(x_key: Annotated[str, Header()]) -> None:
    if x_key != "letmein":
        raise HTTPException(status_code=401, detail="bad key")
```

```python
# shop/routers/recipes.py
from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import need_key

router = APIRouter(
    prefix="/recipes",
    tags=["recipes"],
    dependencies=[Depends(need_key)],
    responses={404: {"description": "Recipe not found"}},
)

RECIPES = {1: "soup", 2: "bread"}


@router.get("/")
def list_recipes() -> dict[int, str]:
    return RECIPES


@router.get("/{recipe_id}")
def read_recipe(recipe_id: int) -> str:
    if recipe_id not in RECIPES:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return RECIPES[recipe_id]


@router.put("/{recipe_id}", tags=["favourites"])
def favourite_recipe(recipe_id: int) -> dict[str, object]:
    return {"recipe_id": recipe_id, "favourite": True}
```

The four settings do four jobs.

- **`prefix`** goes in front of every route path. The routes here are `/recipes/`, `/recipes/{recipe_id}` and `/recipes/{recipe_id}` for `PUT`.
- **`tags`** label each route for the docs. The `PUT` route adds one more tag of its own. We looked at its entry in `/openapi.json`: the tags were `recipes` and then `favourites`. The router's tags come first, then the route's.
- **`dependencies`** run for every route in the router. They get no parameter in the route function. Like the `dependencies` list you can put on a single decorator, they exist for their side effect, here the key check. The header still appears in the docs: the `/recipes/` entry listed a required header `x-key`.
- **`responses`** add extra documented responses to every route. In our run, `404` was listed on all three routes, even on `/recipes/`, which never raises it. A route with its own `responses`, such as a `403`, lists both. So put on the router only what is true for every route in it.

### Prefix rules and path slips

The prefix has two rules, and FastAPI enforces both when you create the router. We tried it:

| `prefix=` | Result |
| --- | --- |
| `"items"` | `AssertionError: A path prefix must start with '/'` |
| `"/items/"` | `AssertionError: A path prefix must not end with '/', as the routes will start with '/'` |
| `"/items"` | fine |

The second rule exists because each route path starts with `/` itself. A trailing `/` on the prefix would give `//`.

The route paths are less strict, and that is where slips hide. All four came from our runs, with a router whose prefix was `/b`, `/a` or `/pets`.

- A route path of `"x"` with no leading `/` was **accepted**. The path became `/bx`. No error, just a wrong URL.
- A route path of `""` and one of `"/"` are two different URLs: with the prefix `/a` we got both `/a` and `/a/`.
- A route path of `""` on a router with **no prefix** raised `FastAPIError: Prefix and path cannot be both empty`.
- Writing the prefix twice, once in the router and once in each route, gave `/pets/pets/`.

One more habit: with the route `"/"` and the prefix `/items`, the URL is `/items/`. A client that asks for `/items` without the slash got a `307` redirect to `/items/` in our test client. It works, but it costs a round trip, so give clients the exact path.

More: [Bigger Applications - Multiple Files](https://fastapi.tiangolo.com/tutorial/bigger-applications/), the part about adding the prefix, tags, responses and dependencies to the router.

## Settings added at include time

A router is sometimes not yours to edit. Say another team shares an admin router between several projects. It has no prefix, no tag and no key check, and you must not change the file.

You can add all of that when you plug it in. `include_router` takes the same settings.

```python
# shop/main.py
from fastapi import Depends, FastAPI

from .dependencies import need_key
from .internal import admin
from .routers import recipes

app = FastAPI()
app.include_router(recipes.router)
app.include_router(
    admin.router,
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(need_key)],
)
```

Does the include change the router object? We checked. After including a router with `prefix="/admin"` and `tags=["admin"]`, the router's own `prefix` was still `""` and its `tags` were still `[]`. The settings belong to this one inclusion, so another project, or another `include_router` call, can add different ones.

When both sides give a prefix they join, the include's prefix first. A router with `prefix="/items"` included with `prefix="/v1"` gave `/v1/items/`.

### What runs first, and in what order tags appear

Settings can now come from five places. We built one app with a dependency or a tag at every level, called a route once, and noted the order.

| Where the dependency is set | Position in our run |
| --- | --- |
| `FastAPI(dependencies=[...])` | 1 |
| `include_router(..., dependencies=[...])` | 2 |
| `APIRouter(dependencies=[...])` | 3 |
| the decorator, `@router.get(..., dependencies=[...])` | 4 |
| a parameter, `Annotated[..., Depends(...)]` | 5 |

The tutorial lists the last three in that order and says router dependencies come first. The first two rows are our own observation. We also saw how the tags stack up: tags given at include time came first, then the router's, then the route's, so the route we tested read `inc`, `items`, `extra`. And `responses` simply add up: the `200` from the route, plus `404` from the router, `418` from the include and `403` from the route, were all listed.

Why does the order matter? A key check set higher up runs before a check set lower down, so an unauthenticated client is turned away before any route-level work. Put the "who are you" check at the top.

More: [Bigger Applications - Multiple Files](https://fastapi.tiangolo.com/tutorial/bigger-applications/), the part about including a router with a custom prefix.

## Imports and running the app

Inside a package you import by position. One dot means "this package". Two dots mean "the parent package".

```python
# in shop/routers/recipes.py
from ..dependencies import need_key  # up to shop/, then shop/dependencies.py
```

```python
# in shop/main.py
from .routers import recipes  # shop/routers/recipes.py
```

The absolute form works too, `from shop.routers import recipes`, as long as `shop` can be found. The page uses the relative form and the task starter uses the absolute one. Pick one and keep it.

### Import the module, not `router`

It is tempting to write the second line below. Do not.

```python
from shop.routers.recipes import router
from shop.routers.cooks import router
```

The second line replaces the first name, so `router` now means only the cooks router. We ran this pattern with two router files and included `router` twice, as the pattern leads you to. Only the second file's routes were left, and the first file's routes were gone with no import error. The one clue was a `UserWarning: Duplicate Operation ID`, because the same router had been included twice. That warning is easy to miss. Import the modules, `from .routers import cooks, recipes`, and write `cooks.router` and `recipes.router`.

### Run the package, not the file

A file with a relative import cannot be run as a script. We ran `python shop/main.py` and got `ImportError: attempted relative import with no known parent package`. The fix is to tell the `fastapi` command where the app lives, once, in `pyproject.toml`:

```toml
[tool.fastapi]
entrypoint = "shop.main:app"
```

With that file in the folder, we started `fastapi dev` with no arguments. It printed `Using import string: shop.main:app`, and requests to a route in each router were answered. The page also recommends this over passing a path every time, because other tools can read the entrypoint too.

More: [Bigger Applications - Multiple Files](https://fastapi.tiangolo.com/tutorial/bigger-applications/), the parts on imports and on the entrypoint.

## Route order across routers

The rule from the path-parameters lesson still holds: the first declared route that matches wins. A variable path such as `/users/{user_id}` matches the text `me`, so a fixed `/users/me` has to come first.

Splitting into files gives that rule a new place to go wrong. The order is now the order of the `include_router` calls. We made one router with `/users/{user_id}` and another with `/users/me`, both with the prefix `/users`, and asked for `/users/me`.

| Included first | Status for `/users/me` |
| --- | --- |
| the variable router | `422` (`"me"` is not an `int`) |
| the fixed router | `200` |

So when two routers share a path start, include the one with fixed paths first. Better still, keep the two kinds of routes in one router, fixed ones first, so the order is visible in one file.

More: [Bigger Applications - Multiple Files](https://fastapi.tiangolo.com/tutorial/bigger-applications/), the example router with `/users/me` above `/users/{username}`.

## Tags and docs metadata

Tags are the headings in the interactive docs. Everything in this section shows up in `/openapi.json`, which is what the docs page reads, and which is also easy to check in a test.

### Tags

A tag is a `str`. You can also use a member of an `Enum` when the app has many tags and you want one spelling for each. We ran a route with `tags=[Tags.items]` and the OpenAPI tag was the plain text `items`.

### The tag list at the top

`FastAPI(openapi_tags=[...])` takes a list of dicts, each with a `name`, and optionally a `description` (Markdown is allowed) and `externalDocs`. The list order is the order the docs show the tags in. We tried three entries, `users`, `items` and `unused`, with the routes using `items`, `users` and a third tag `orders`:

- The top-level tag list in `/openapi.json` was `users, items, unused`: our order, not the alphabetical one.
- `unused`, with no routes, was still in the list.
- `orders` was on its route, but it was **not** in the top-level list, because we had given it no metadata. The docs say you need not describe every tag, and this is what that looks like.

So keep one list of tag metadata in `main.py`, and make sure a typo in a router's tag does not silently create a new, undescribed heading.

```python
from fastapi import FastAPI

tags_metadata = [
    {"name": "recipes", "description": "Read and favourite recipes."},
    {"name": "cooks", "description": "The people who write them."},
]

app = FastAPI(title="Recipe shop", version="0.1.0", openapi_tags=tags_metadata)
```

`title`, `version`, `description` and a few contact and licence fields describe the whole API in the same file. `openapi_url` and `docs_url` move or switch off the schema and the docs page. See the metadata page for the full table.

### Per-route options

Each route decorator takes a few more options that end up in the docs. We ran one route with all of them:

```python
from fastapi import FastAPI, status

app = FastAPI()


@app.get(
    "/old/",
    summary="List the old way",
    response_description="A short list",
    deprecated=True,
    status_code=status.HTTP_202_ACCEPTED,
)
def old_list() -> list[str]:
    """Return the old list.

    Kept for old clients."""
    return ["soup"]
```

In `/openapi.json` this route had `summary` set, `deprecated` as `true`, a single response `202` with our description, and a `description` taken from the docstring (both paragraphs, as the page promises). A route with none of these options got a summary made from its function name (`Plain Name` for `plain_name`), and no description at all.

Be careful that these options go on the **decorator**, not on the function. The page puts a warning box on exactly that.

### Check the shape in a test

Because tags and paths are data, a test can read them. This is a self-contained example of how.

```python
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("/")
def list_recipes() -> list[str]:
    return []


app = FastAPI()
app.include_router(router)

spec = TestClient(app).get("/openapi.json").json()
assert list(spec["paths"]) == ["/recipes/"]
assert spec["paths"]["/recipes/"]["get"]["tags"] == ["recipes"]
```

If you see a path such as `/recipes/recipes/`, you wrote the prefix twice. If a tag is missing, the router or the include call lost it. The hands-on task is checked this way.

More: [Path Operation Configuration](https://fastapi.tiangolo.com/tutorial/path-operation-configuration/) and [Metadata and Docs URLs](https://fastapi.tiangolo.com/tutorial/metadata/).

## Routers stay live

The 0.143.0 version of the tutorial says that an included router is not copied into the app. It stays connected to it. We checked three things.

- **Routes added after the include still work.** We included an empty router, then added `@router.get("/now")`. The route answered `200` and `/late/now` was in the OpenAPI paths.
- **One router can be included twice with different prefixes.** The page suggests `/api/v1` and `/api/latest`. We did it: both paths answered, and the two operation ids were different (`ping_api_v1_ping_get` and `ping_api_latest_ping_get`), so there was no duplicate warning. Including it twice with the *same* prefix is what triggers the warning from earlier.
- **A router can include another router.** With `outer = APIRouter(prefix="/v1")` and `inner = APIRouter(prefix="/inner")`, after `outer.include_router(inner)` the route was at `/v1/inner/x`.

One warning from the page: do not edit `router.routes` by hand. It is a lower-level list that can hold nested inclusions, and not a flat list of final routes. Add routes with the decorators and `include_router`, not with the list.

More: [Bigger Applications - Multiple Files](https://fastapi.tiangolo.com/tutorial/bigger-applications/), the last two sections, on including the same router twice and a router in another router.

Sources (FastAPI 0.143.0, MIT licence, © 2018 Sebastián Ramírez; adapted and rewritten): [Bigger Applications - Multiple Files](https://fastapi.tiangolo.com/tutorial/bigger-applications/), [Path Operation Configuration](https://fastapi.tiangolo.com/tutorial/path-operation-configuration/), [Metadata and Docs URLs](https://fastapi.tiangolo.com/tutorial/metadata/). The observations marked "we ran" or "we saw" are our own runs on 2026-10-15. This site is not affiliated with FastAPI.
