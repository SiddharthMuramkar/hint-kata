import importlib
import os

from fastapi.testclient import TestClient

# The checker runs this file twice: once with APP_MODULE=good_app, once with APP_MODULE=buggy_app.
app = importlib.import_module(os.environ.get("APP_MODULE", "good_app")).app
client = TestClient(app)


def test_placeholder() -> None:
    # TODO: replace this with real tests (at least 3). A test that always passes proves nothing.
    assert True
