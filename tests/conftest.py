import logging
from collections.abc import Iterator

import pytest
from pydantic_ai import models

from app.config import settings

models.ALLOW_MODEL_REQUESTS = False  # never hit a real LLM in tests

collect_ignore_glob = ["fixtures/*"]  # fixture lessons hold sample tests, not ours


@pytest.fixture(autouse=True)
def _sqlite_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """A DATABASE_URL in the developer's local env file must not send tests to Postgres."""
    monkeypatch.setattr(settings, "database_url", "")


@pytest.fixture
def app_logs(caplog: pytest.LogCaptureFixture) -> Iterator[pytest.LogCaptureFixture]:
    """caplog for the app's own loggers. configure_logging stops "app" passing records on to the
    root logger, so hook caplog's handler onto "app" itself (and make that true in every test)."""
    app_log = logging.getLogger("app")
    propagate, app_log.propagate = app_log.propagate, False
    app_log.addHandler(caplog.handler)
    caplog.set_level(logging.DEBUG, logger="app")
    yield caplog
    app_log.removeHandler(caplog.handler)
    app_log.propagate = propagate
