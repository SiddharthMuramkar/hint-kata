from fastapi import FastAPI

app = FastAPI()


# TODO 1 (route order): add `GET /books/featured` here. It returns {"featured": "Dune"}.
#   It must be declared BEFORE the route below. Why? Read the lesson section on route order.


# TODO 2 (path rule): `book_id` must be an int that is >= 1.
#   Use Annotated with Path(...): book_id: Annotated[int, Path(ge=1)]
@app.get("/books/{book_id}")
def read_book(book_id):
    return {"book_id": book_id}


# TODO 3 (Enum): write `class Shelf(str, Enum)` with the members fiction, science and history
#   (values are the same words in lower case). Use it as the type of `shelf`, and return
#   {"shelf": shelf.value}.
@app.get("/shelves/{shelf}")
def read_shelf(shelf):
    return {"shelf": shelf}


# TODO 4 (query parameters): declare these parameters on `search`, with the rules on the
#   parameters, not in an `if`:
#     q: required str, 3 to 20 characters          (Query(min_length=..., max_length=...))
#     tags: optional list[str], None when not sent  (a list needs Query() to be read from the URL)
#     limit: int, default 10, from 1 to 50          (ge and le)
#     sort: str, default "title", exactly "title" or "year"   (pattern; anchor it with ^ and $)
#     in_stock: bool, default False
#   Then return them in the dict below, instead of the fixed values.
@app.get("/search")
def search():
    return {"q": None, "tags": None, "limit": 10, "sort": "title", "in_stock": False}
