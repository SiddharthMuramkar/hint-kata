import config_app  # the learner's config_app.py, on PYTHONPATH
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

KEY = "sk-test-SECRET-4242"  # a made-up value, only for these tests
NAMES = ("APP_NAME", "MAX_ITEMS", "API_KEY")


def clear_cache() -> None:
    # A starter without @lru_cache has no cache_clear. Skip it, so the real failure shows.
    getattr(config_app.get_settings, "cache_clear", lambda: None)()


@pytest.fixture(autouse=True)
def clean_settings(monkeypatch, tmp_path):
    """No real env file is read: tests run in an empty folder, with the variables removed."""
    monkeypatch.chdir(tmp_path)
    for name in NAMES:
        monkeypatch.delenv(name, raising=False)
    clear_cache()
    config_app.app.dependency_overrides.clear()
    yield
    clear_cache()
    config_app.app.dependency_overrides.clear()


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Demo")
    monkeypatch.setenv("MAX_ITEMS", "25")
    monkeypatch.setenv("API_KEY", KEY)


client = TestClient(config_app.app)


def locs(error: ValidationError) -> list[tuple]:
    return [e["loc"] for e in error.errors()]


def test_settings_reads_and_converts_environment_variables(env):
    settings = config_app.Settings()
    assert settings.app_name == "Demo"
    assert settings.max_items == 25  # an int, not the text "25"
    assert settings.api_key == KEY


def test_max_items_defaults_to_10(env, monkeypatch):
    monkeypatch.delenv("MAX_ITEMS")
    assert config_app.Settings().max_items == 10


def test_app_name_and_api_key_are_required():
    with pytest.raises(ValidationError) as exc:
        config_app.Settings()
    assert sorted(locs(exc.value)) == [("api_key",), ("app_name",)]
    assert {e["type"] for e in exc.value.errors()} == {"missing"}


def test_a_max_items_that_is_not_an_int_raises_validation_error(env, monkeypatch):
    monkeypatch.setenv("MAX_ITEMS", "lots")
    with pytest.raises(ValidationError) as exc:
        config_app.Settings()
    assert locs(exc.value) == [("max_items",)]
    assert exc.value.errors()[0]["type"] == "int_parsing"


def test_get_settings_raises_validation_error_on_a_bad_value(env, monkeypatch):
    monkeypatch.setenv("MAX_ITEMS", "lots")
    with pytest.raises(ValidationError):
        config_app.get_settings()


def test_settings_points_at_an_env_file():
    assert config_app.Settings.model_config.get("env_file") == ".env"


def test_settings_can_come_from_an_env_file(tmp_path):
    file = tmp_path / "settings.env"
    file.write_text(f"APP_NAME=FromFile\nMAX_ITEMS=7\nAPI_KEY={KEY}\n")
    settings = config_app.Settings(_env_file=file)
    assert (settings.app_name, settings.max_items, settings.api_key) == ("FromFile", 7, KEY)


def test_get_settings_returns_the_same_object_every_time(env):
    first = config_app.get_settings()
    assert config_app.get_settings() is first


def test_get_settings_is_cached_so_later_env_changes_are_not_seen(env, monkeypatch):
    first = config_app.get_settings()
    monkeypatch.setenv("MAX_ITEMS", "99")
    assert config_app.get_settings().max_items == 25
    clear_cache()
    assert config_app.get_settings() is not first
    assert config_app.get_settings().max_items == 99


def test_info_returns_the_app_name_and_max_items(env):
    response = client.get("/info")
    assert response.status_code == 200
    assert response.json() == {"app_name": "Demo", "max_items": 25}


def test_key_length_returns_only_the_length(env):
    response = client.get("/key-length")
    assert response.status_code == 200
    assert response.json() == {"key_length": len(KEY)}


def test_routes_use_get_settings_so_a_test_can_override_it():
    # The environment is empty here. The real get_settings would fail, so a 200 proves the
    # routes asked for it with Depends and the override replaced it.
    def fake_settings():
        return config_app.Settings(app_name="Fake", max_items=3, api_key="fake-key", _env_file=None)

    config_app.app.dependency_overrides[config_app.get_settings] = fake_settings
    assert client.get("/info").json() == {"app_name": "Fake", "max_items": 3}
    assert client.get("/key-length").json() == {"key_length": len("fake-key")}


def test_the_key_value_is_never_in_any_response(env):
    config_app.get_settings()  # warm the cache with the real settings
    for path in ("/info", "/key-length", "/info?extra=1", "/missing"):
        response = client.get(path)
        assert KEY not in response.text, path
        assert KEY not in str(response.headers), path

    def fake_settings():
        return config_app.Settings(app_name="Fake", max_items=3, api_key=KEY, _env_file=None)

    config_app.app.dependency_overrides[config_app.get_settings] = fake_settings
    for path in ("/info", "/key-length"):
        assert KEY not in client.get(path).text, path
