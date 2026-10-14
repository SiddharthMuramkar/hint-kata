from enum import Enum
from typing import Annotated

from fastapi import FastAPI, Path, Query

app = FastAPI()


class Shelf(str, Enum):  # noqa: UP042 (the lesson teaches `str` + `Enum`; StrEnum also works)
    fiction = "fiction"
    science = "science"
    history = "history"


# Fixed path first, so "featured" is not captured by {book_id}.
@app.get("/books/featured")
def read_featured():
    return {"featured": "Dune"}


@app.get("/books/{book_id}")
def read_book(book_id: Annotated[int, Path(ge=1)]):
    return {"book_id": book_id}


@app.get("/shelves/{shelf}")
def read_shelf(shelf: Shelf):
    return {"shelf": shelf.value}


@app.get("/search")
def search(
    q: Annotated[str, Query(min_length=3, max_length=20)],
    tags: Annotated[list[str] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    sort: Annotated[str, Query(pattern="^(title|year)$")] = "title",
    in_stock: bool = False,
):
    return {"q": q, "tags": tags, "limit": limit, "sort": sort, "in_stock": in_stock}
