"""The PA4 trace script re-runs to the same steps as the committed trace.json.

Only `["steps"]` is compared: `captured_at` changes every day, the steps must not.
"""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from app.traces import Trace

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "traces" / "scripts"
COMMITTED = ROOT / "content" / "pydantic-ai" / "pa4-streaming" / "trace.json"


def script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_agent_stream_script_matches_the_committed_trace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = script("agent_stream")
    runs: list[dict[str, object]] = []
    for name in ("a.json", "b.json"):
        out = tmp_path / name
        monkeypatch.setattr(sys, "argv", ["agent_stream.py", "--out", str(out)])
        module.main()
        runs.append(json.loads(out.read_text()))
    committed = json.loads(COMMITTED.read_text())
    assert runs[0]["steps"] == runs[1]["steps"], "the script is not deterministic"
    assert runs[0]["steps"] == committed["steps"], (
        "trace.json is stale; regenerate it with: "
        "uv run python traces/scripts/agent_stream.py "
        "--out content/pydantic-ai/pa4-streaming/trace.json"
    )


def test_agent_stream_trace_shape() -> None:
    trace = Trace.model_validate_json(COMMITTED.read_text())
    assert [s.kind for s in trace.steps] == [
        "user_prompt",
        "model_request",
        "tool_call",
        "tool_call",
        "tool_result",
        "model_request",
        "model_text",
        "model_text",
        "model_text",
        "final_output",
    ]
    assert [s.idx for s in trace.steps if s.checkpoint] == [1, 8]
    assert trace.source["generator"] == "FunctionModel"
    assert trace.source["events"] == [
        "PartStartEvent",
        "PartDeltaEvent",
        "PartEndEvent",
        "FunctionToolCallEvent",
        "FunctionToolResultEvent",
        "PartStartEvent",
        "FinalResultEvent",
        "PartDeltaEvent",
        "PartDeltaEvent",
        "PartDeltaEvent",
        "PartEndEvent",
        "AgentRunResultEvent",
    ]
    assert trace.steps[-1].metrics["requests"] == 2
