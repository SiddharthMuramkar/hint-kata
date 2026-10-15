# Task: split a flat pet-shop app into routers

Open the folder `workspace/fa11-bigger-apps/shop/`. The app in `shop/main.py` works, but it is
one flat file. Every pet route repeats the same path start, the same tag and the same key check.
Your job is to move that sharing onto routers, without changing how the app behaves for a client.

Do not touch `shop/dependencies.py` (the key check) or `shop/internal/admin.py` (a router that
another team shares).

## 1. A router for pets

Create `shop/routers/__init__.py` (it can be empty) and `shop/routers/pets.py`. In the second
file, make `router = APIRouter(...)` and move the three pet routes onto it. Put these on the
router, once, not on each route:

- the path start `/pets`
- the tag `pets`
- the key check `require_key`, as a router dependency
- the extra response `404` with the description `"Pet not found"`

The route paths inside the file are then just `/` and `/{pet_id}`. The adopt route (`PUT`)
keeps one more tag of its own, `adoption`, so it ends up with the tags `["pets", "adoption"]`.

Move the `PETS` data to that file too.

## 2. A router for owners

Do the same in `shop/routers/owners.py` for the two owner routes, with the path start
`/owners` and the tag `owners`. These routes need no key check.

## 3. Include everything in main.py

Call `app.include_router(...)` for both routers. Keep `GET /` on the app itself.

Then include the shared `shop.internal.admin.router` too. It has no prefix, tag or key check of
its own and you must not add them to its file. Pass `prefix="/admin"`, `tags=["admin"]` and
the key check when you include it. Its one route then answers on `POST /admin/`.

## 4. Tag metadata

Pass `openapi_tags` to `FastAPI(...)`. List `pets`, `owners` and `admin`, in that order, each
with a short `description`.

## Check your work

The hidden tests call the app with a test client and read `/openapi.json`. They check the paths,
the tags of each operation (and their order), the tag list, the documented `404` response and
which routes need the key. They also check that the key check is a dependency of the pets router
and that `admin.py` is unchanged. If a test fails, read the paths in the failure first: a path
such as `/pets/pets/` means the path start is written twice.
