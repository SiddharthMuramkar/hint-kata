from typing import Annotated

from fastapi import Header, HTTPException


def require_key(x_key: Annotated[str, Header()]) -> None:
    """Shared check: every protected route needs the header `X-Key: letmein`."""
    if x_key != "letmein":
        raise HTTPException(status_code=401, detail="bad key")
