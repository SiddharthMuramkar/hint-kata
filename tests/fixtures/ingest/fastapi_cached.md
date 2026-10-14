# Dependencies <!-- anchor: dependencies -->

**FastAPI** has a very powerful **<dfn title="also known as components, providers">Dependency Injection</dfn>** system.

## What is "Dependency Injection" <!-- anchor: what-is-dependency-injection -->

It means your code can declare what it needs, and FastAPI provides it.

## First Steps <!-- anchor: first-steps -->

Let's see a very simple example.

### Create a dependency, or "dependable" <!-- anchor: create-a-dependency-or-dependable -->

It is just a function:

```python
async def common_parameters(q: str | None = None, skip: int = 0, limit: int = 100):
    # a comment that is not a heading
    return {"q": q, "skip": skip, "limit": limit}
```

> [!NOTE]
> FastAPI added support for `Annotated` in version 0.95.0.
>
> Upgrade before using it.

**Python 3.10+**

```python
commons: Annotated[dict, Depends(common_parameters)]
```

<img src="/img/tutorial/dependencies/image01.png">

### Import `Depends` <!-- anchor: import-depends -->

```python
from fastapi import Depends
```

> [!TIP]
> **Handy**
> You can reuse a dependency as a type alias.
