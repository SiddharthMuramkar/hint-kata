import pytest
from pydantic_ai import models

from app.config import settings

models.ALLOW_MODEL_REQUESTS = False  # never hit a real LLM in tests

collect_ignore_glob = ["fixtures/*"]  # fixture lessons hold sample tests, not ours


@pytest.fixture(autouse=True)
def _sqlite_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """A DATABASE_URL in the developer's local env file must not send tests to Postgres."""
    monkeypatch.setattr(settings, "database_url", "")
