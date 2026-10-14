from solution import add  # ty: ignore[unresolved-import]


def test_add() -> None:
    assert add(2, 3) == 5
