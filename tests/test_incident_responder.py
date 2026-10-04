import importlib.util
import json
from pathlib import Path

import pytest


SAMPLE = Path(__file__).parent.parent / "incident-response" / "sample-alert.json"


@pytest.fixture
def responder_module():
    # incident-response/ is not a package (hyphenated name), so load by path.
    path = SAMPLE.parent / "responder.py"
    spec = importlib.util.spec_from_file_location("incident_responder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def payload():
    return json.loads(SAMPLE.read_text())


def test_saves_firing_alert_and_skips_duplicates(responder_module, payload, tmp_path):
    responder = responder_module.Responder(incidents_dir=tmp_path)

    accepted, skipped = responder.accept(payload)
    again, skipped_again = responder.accept(payload)

    assert len(accepted) == 1 and skipped == []
    assert again == [] and skipped_again[0]["reason"] == "already handled"
    incident = tmp_path / accepted[0]
    alert = json.loads((incident / "alert.json").read_text())
    assert alert["labels"]["http_route"] == "/api/orders/{order_id}"
    status = json.loads((incident / "status.json").read_text())
    assert status["state"] == "received"
    assert status["endpoint"] == "/api/orders/{order_id}"
    assert responder.jobs.qsize() == 1


def test_ignores_resolved_alerts(responder_module, payload, tmp_path):
    payload["alerts"][0]["status"] = "resolved"
    responder = responder_module.Responder(incidents_dir=tmp_path)

    accepted, skipped = responder.accept(payload)

    assert accepted == [] and skipped[0]["reason"] == "not firing"
    assert list(tmp_path.iterdir()) == []


def test_handle_collects_context_then_investigates(responder_module, payload, tmp_path, monkeypatch):
    trace = {"batches": [{"scopeSpans": [{"spans": [{
        "name": "order.lookup",
        "startTimeUnixNano": "1000000",
        "endTimeUnixNano": "3000000",
        "status": {"code": "STATUS_CODE_ERROR"},
        "attributes": [{"key": "order.id", "value": {"stringValue": "express-1002"}}],
        "events": [{"name": "exception", "attributes": [
            {"key": "exception.type", "value": {"stringValue": "ValueError"}},
            {"key": "exception.message", "value": {"stringValue": "day is out of range for month"}},
        ]}],
    }]}]}]}
    logs = {"data": {"result": [{
        "stream": {"service_name": "order-tracker", "severity_text": "ERROR", "trace_id": "abc123"},
        "values": [["1759579200000000000", "Order lookup failed"]],
    }]}}
    queries = []

    def fake_get(base, path, params=None):
        queries.append((base, path, params))
        if path == "/healthz":
            return {"status": "ok"}
        if path == "/api/search":
            return {"traces": [{"traceID": "abc123"}]}
        if path.startswith("/api/traces/"):
            return trace
        return logs

    monkeypatch.setattr(responder_module, "http_get", fake_get)
    investigated = []
    responder = responder_module.Responder(
        incidents_dir=tmp_path,
        investigate=lambda d, endpoint: investigated.append(endpoint) or "done in 1s",
    )
    accepted, _ = responder.accept(payload)

    responder.handle(*responder.jobs.get())

    incident = tmp_path / accepted[0]
    context = (incident / "context.md").read_text()
    assert "ValueError" in context and "day is out of range for month" in context
    assert "Order lookup failed" in context
    assert (incident / "traces" / "abc123.json").exists()
    search = next(p for _, path, p in queries if path == "/api/search")
    assert 'span.http.route = "/api/orders/{order_id}"' in search["q"]
    assert any(p and 'trace_id=~"abc123"' in p.get("query", "") for _, _, p in queries)
    assert investigated == ["/api/orders/{order_id}"]
    status = json.loads((incident / "status.json").read_text())
    assert status["state"] == "done in 1s" and status["trace_ids"] == ["abc123"]


def test_agent_runs_headless_with_read_only_tools(responder_module):
    command = responder_module.agent_command()

    assert command[:2] == ["claude", "-p"]
    assert command[command.index("--permission-mode") + 1] == "dontAsk"
    tools = command[command.index("--allowedTools") + 1:]
    assert not any(t.startswith(("Edit", "Write")) for t in tools) and "Bash" not in tools


def test_fix_mode_allows_editing_app_code_only(responder_module, tmp_path):
    command = responder_module.agent_command(can_fix=True)
    prompt = responder_module.agent_prompt(tmp_path, "/api/orders/{order_id}", can_fix=True)

    tools = command[command.index("--allowedTools") + 1:]
    assert [t for t in tools if t.startswith(("Edit", "Write"))] == ["Edit(./app/**)"]
    assert "Bash" not in tools
    assert "apply the smallest correct fix" in prompt and "Fix applied" in prompt
