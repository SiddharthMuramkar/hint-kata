import json
import tomllib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def test_vercel_json_targets_the_entrypoint_file() -> None:
    config = json.loads((ROOT / "vercel.json").read_text())
    fn = config["functions"]["app/main.py"]
    assert fn["maxDuration"] == 300
    assert (ROOT / "app/main.py").is_file()
    assert "tests/**" in fn["excludeFiles"]


def test_both_entrypoints_point_at_the_app() -> None:
    tool = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]
    assert tool["fastapi"]["entrypoint"] == "app.main:app"
    assert tool["vercel"]["entrypoint"] == "app.main:app"


def test_python_version_pin_matches_requires_python() -> None:
    assert (ROOT / ".python-version").read_text().strip() == "3.13"


def test_app_boots_from_another_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("app.main.settings.hintkata_db_path", str(tmp_path / "x" / "hintkata.db"))
    from app.main import app

    with TestClient(app) as client:
        assert client.get("/healthz").json() == {"ok": True}
        assert client.get("/static/css/app.css").status_code == 200
        assert client.get("/").status_code == 200
        assert len(client.get("/api/lessons").json()) > 0
