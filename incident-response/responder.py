"""Automatic incident responder for the Order Tracker.

Grafana sends alert notifications to POST /alerts. For each new firing alert the
responder:

1. saves the alert to incidents/<id>/alert.json,
2. collects context from the app (health), Tempo (failing traces on the alerted
   endpoint), and Loki (error logs and the logs of those traces), and writes it
   to incidents/<id>/context.md plus the raw JSON responses,
3. starts Claude Code in headless mode (`claude -p`) to investigate, and saves
   its report to incidents/<id>/investigation.md. With AGENT_CAN_FIX=true the
   agent may also edit files under app/, and the change is saved to fix.diff.

Only the standard library is used. Configuration comes from environment
variables (see the constants below).
"""

import json
import logging
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


PORT = int(os.getenv("PORT", "8001"))
INCIDENTS_DIR = Path(os.getenv("INCIDENTS_DIR", "incidents"))
WORKSPACE_DIR = Path(os.getenv("WORKSPACE_DIR", "."))
APP_URL = os.getenv("APP_URL", "http://app:8000")
LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100")
TEMPO_URL = os.getenv("TEMPO_URL", "http://tempo:3200")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
SERVICE_NAME = os.getenv("SERVICE_NAME", "order-tracker")
LOOKBACK_MINUTES = int(os.getenv("LOOKBACK_MINUTES", "15"))
MAX_TRACES = int(os.getenv("MAX_TRACES", "5"))
AGENT_ENABLED = os.getenv("AGENT_ENABLED", "true").lower() != "false"
AGENT_TIMEOUT_SECONDS = int(os.getenv("AGENT_TIMEOUT_SECONDS", "900"))
AGENT_MODEL = os.getenv("AGENT_MODEL", "")
AGENT_CAN_FIX = os.getenv("AGENT_CAN_FIX", "false").lower() == "true"
HTTP_TIMEOUT = 10

# The agent may read code and query the telemetry backends. dontAsk mode
# denies every tool that is not listed here.
AGENT_TOOLS = ["Read", "Grep", "Glob", "Bash(curl *)", "Bash(jq *)"]
# In fix mode it may also edit the application code, and only that.
FIX_TOOLS = ["Edit(./app/**)"]

log = logging.getLogger("incident-responder")


# ---------------------------------------------------------------------------
# HTTP helpers


def http_get(base, path, params=None):
    """GET a URL and return parsed JSON (or text). Raises on errors."""
    url = base.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
        body = response.read().decode("utf-8", errors="replace")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return body


def fetch(name, errors, base, path, params=None):
    """Like http_get, but records failures in `errors` and returns None."""
    try:
        return http_get(base, path, params)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        errors.append(f"{name}: {exc}")
        log.warning("Could not fetch %s: %s", name, exc)
        return None


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# Alert parsing


def parse_time(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    # Grafana uses 0001-01-01 for "not set".
    return parsed if parsed.year > 1 else None


def alert_endpoint(alert):
    labels = alert.get("labels") or {}
    annotations = alert.get("annotations") or {}
    return labels.get("http_route") or annotations.get("endpoint") or "unknown"


def alert_key(alert):
    """Identifies one firing period of one alert instance."""
    labels = alert.get("labels") or {}
    fingerprint = alert.get("fingerprint") or json.dumps(labels, sort_keys=True)
    return f"{fingerprint}@{alert.get('startsAt', '')}"


def incident_id(alert, now):
    name = (alert.get("labels") or {}).get("alertname", "alert")
    slug = re.sub(r"[^a-z0-9]+", "-", f"{name} {alert_endpoint(alert)}".lower()).strip("-")
    return f"{now:%Y%m%dT%H%M%SZ}-{slug[:60]}"


# ---------------------------------------------------------------------------
# Context collection


def otlp_value(value):
    for kind in ("stringValue", "intValue", "boolValue", "doubleValue"):
        if kind in value:
            return value[kind]
    if "arrayValue" in value:
        return [otlp_value(v) for v in value["arrayValue"].get("values", [])]
    return value


def otlp_attributes(attributes):
    return {a["key"]: otlp_value(a.get("value", {})) for a in attributes or []}


def summarize_trace(trace_id, trace):
    """Turn a Tempo OTLP-JSON trace into readable Markdown lines."""
    lines = [f"#### Trace `{trace_id}`", ""]
    batches = trace.get("batches") or trace.get("resourceSpans") or []
    spans = []
    for batch in batches:
        for scope in batch.get("scopeSpans") or batch.get("instrumentationLibrarySpans") or []:
            spans.extend(scope.get("spans", []))
    spans.sort(key=lambda s: int(s.get("startTimeUnixNano", 0)))
    for span in spans:
        status = (span.get("status") or {}).get("code", "STATUS_CODE_UNSET")
        status = str(status).replace("STATUS_CODE_", "")
        start = int(span.get("startTimeUnixNano", 0))
        duration_ms = (int(span.get("endTimeUnixNano", start)) - start) / 1e6
        attrs = otlp_attributes(span.get("attributes"))
        lines.append(f"- **{span.get('name')}** status={status} duration={duration_ms:.1f}ms")
        if attrs:
            lines.append(f"  - attributes: `{json.dumps(attrs, sort_keys=True)}`")
        for event in span.get("events", []):
            event_attrs = otlp_attributes(event.get("attributes"))
            lines.append(f"  - event **{event.get('name')}**")
            for key in ("exception.type", "exception.message"):
                if key in event_attrs:
                    lines.append(f"    - {key}: `{event_attrs[key]}`")
            if "exception.stacktrace" in event_attrs:
                lines += ["", "```", str(event_attrs["exception.stacktrace"]).rstrip(), "```", ""]
    lines.append("")
    return lines


LOG_FIELDS = (
    "severity_text", "trace_id", "span_id", "order_id",
    "exception_type", "exception_message",
)


def summarize_logs(result):
    """Turn a Loki query_range response into readable Markdown lines."""
    entries = []
    for stream in ((result or {}).get("data") or {}).get("result", []):
        labels = stream.get("stream", {})
        for ts, line, *metadata in stream.get("values", []):
            fields = dict(labels)
            if metadata and isinstance(metadata[0], dict):
                fields.update(metadata[0].get("structuredMetadata", {}))
            entries.append((int(ts), line, fields))
    entries.sort(key=lambda e: e[0])
    lines = []
    for ts, line, fields in entries:
        when = datetime.fromtimestamp(ts / 1e9, timezone.utc).isoformat(timespec="milliseconds")
        extra = {k: fields[k] for k in LOG_FIELDS if k in fields}
        lines.append(f"- `{when}` {line} `{json.dumps(extra, sort_keys=True)}`")
        if "exception_stacktrace" in fields:
            lines += ["", "```", fields["exception_stacktrace"].rstrip(), "```", ""]
    return lines or ["- (no log lines)"]


def loki_query(name, errors, query, start, end, limit=100):
    return fetch(name, errors, LOKI_URL, "/loki/api/v1/query_range", {
        "query": query,
        "start": str(int(start.timestamp() * 1e9)),
        "end": str(int(end.timestamp() * 1e9)),
        "limit": str(limit),
        "direction": "backward",
    })


def gather_context(alert, incident_dir, now=None):
    """Collect app, trace, and log context for one alert into incident_dir."""
    now = now or datetime.now(timezone.utc)
    endpoint = alert_endpoint(alert)
    started = parse_time(alert.get("startsAt")) or now
    start = min(started, now) - timedelta(minutes=LOOKBACK_MINUTES)
    end = now + timedelta(minutes=1)
    errors = []

    health = fetch("app health", errors, APP_URL, "/healthz")
    write_json(incident_dir / "app-health.json", health)

    # Failing server spans on the alerted endpoint.
    selector = f'resource.service.name = "{SERVICE_NAME}" && status = error'
    if endpoint != "unknown":
        selector += f' && span.http.route = "{endpoint}"'
    traceql = "{ " + selector + " }"
    search = fetch("tempo search", errors, TEMPO_URL, "/api/search", {
        "q": traceql,
        "start": str(int(start.timestamp())),
        "end": str(int(end.timestamp())),
        "limit": "20",
    })
    write_json(incident_dir / "tempo-search.json", search)
    trace_ids = [t["traceID"] for t in (search or {}).get("traces", []) if "traceID" in t]

    traces_dir = incident_dir / "traces"
    traces_dir.mkdir(exist_ok=True)
    trace_lines = []
    for trace_id in trace_ids[:MAX_TRACES]:
        trace = fetch(f"trace {trace_id}", errors, TEMPO_URL, f"/api/traces/{trace_id}")
        if isinstance(trace, dict):
            write_json(traces_dir / f"{trace_id}.json", trace)
            trace_lines += summarize_trace(trace_id, trace)

    service = f'{{service_name="{SERVICE_NAME}"}}'
    error_logs = loki_query("loki error logs", errors, f'{service} | severity_text="ERROR"', start, end)
    write_json(incident_dir / "loki-error-logs.json", error_logs)
    trace_logs = None
    if trace_ids:
        pattern = "|".join(trace_ids[:MAX_TRACES])
        trace_logs = loki_query(
            "loki trace logs", errors, f'{service} | trace_id=~"{pattern}"', start, end
        )
        write_json(incident_dir / "loki-trace-logs.json", trace_logs)

    labels = alert.get("labels") or {}
    annotations = alert.get("annotations") or {}
    md = [
        f"# Incident context: {labels.get('alertname', 'alert')}",
        "",
        f"- **Endpoint:** `{endpoint}`",
        f"- **Status:** {alert.get('status')}",
        f"- **Started:** {alert.get('startsAt')}",
        f"- **Summary:** {annotations.get('summary', '')}",
        f"- **Description:** {annotations.get('description', '')}",
        f"- **Value:** {alert.get('valueString', '')}",
        f"- **Labels:** `{json.dumps(labels, sort_keys=True)}`",
        f"- **Dashboard:** {annotations.get('dashboard_url') or alert.get('dashboardURL', '')}",
        f"- **Context window:** {start.isoformat()} to {end.isoformat()}",
        f"- **Collected:** {now.isoformat()}",
        "",
        "## App health",
        "",
        f"`GET {APP_URL}/healthz` -> `{json.dumps(health)}`",
        "",
        f"## Failing traces ({len(trace_ids)} found, {min(len(trace_ids), MAX_TRACES)} saved)",
        "",
        f"TraceQL: `{traceql}`",
        "",
        *(trace_lines or ["- (no failing traces found)", ""]),
        "## Logs for those traces",
        "",
        *(summarize_logs(trace_logs) if trace_logs else ["- (none)"]),
        "",
        f"## Error logs for {SERVICE_NAME}",
        "",
        *summarize_logs(error_logs),
        "",
        "## Raw data in this folder",
        "",
        "- `alert.json`: the Grafana notification for this alert",
        "- `app-health.json`, `tempo-search.json`, `traces/*.json`",
        "- `loki-error-logs.json`, `loki-trace-logs.json`",
        "",
    ]
    if errors:
        md += ["## Collection errors", "", *[f"- {e}" for e in errors], ""]
    (incident_dir / "context.md").write_text("\n".join(md), encoding="utf-8")
    return {"endpoint": endpoint, "trace_ids": trace_ids, "errors": errors}


# ---------------------------------------------------------------------------
# Headless coding assistant


def agent_prompt(incident_dir, endpoint, can_fix=None):
    can_fix = AGENT_CAN_FIX if can_fix is None else can_fix
    if can_fix:
        code_access = (
            "The application code in app/ is writable: once you have found the root\n"
            "cause, apply the smallest correct fix there with the Edit tool. Everything\n"
            "else (tests, config, this incident folder) is read-only; do not try to\n"
            "change it. The running app will not pick up your change until it is\n"
            "rebuilt, so do not expect the live endpoint to recover."
        )
        fix_section = "Fix applied (file:line and what changed, as a unified diff)"
    else:
        code_access = "It is mounted read-only. Do not try to modify any files."
        fix_section = "Suggested fix (as a unified diff)"
    return f"""\
You are the on-call engineer for the Order Tracker service. Grafana fired an
alert for HTTP 5xx errors on the endpoint `{endpoint}`.

The alert and the context collected when it fired are in {incident_dir}.
Start with {incident_dir}/context.md; raw JSON is next to it.

The service source code is in the current directory ({WORKSPACE_DIR}).
{code_access}

You may query live systems with curl:
- App:        {APP_URL} (API under /api/orders, health at /healthz)
- Loki:       {LOKI_URL} (LogQL, e.g. /loki/api/v1/query_range, stream {{service_name="{SERVICE_NAME}"}})
- Tempo:      {TEMPO_URL} (TraceQL search at /api/search, traces at /api/traces/<id>)
- Prometheus: {PROMETHEUS_URL} (metric order_tracker_http_requests_total)

Find the root cause. Reproduce it against the app with a read-only request if
you can. Then reply with only a Markdown incident report with these sections:
Summary, Impact, Timeline, Evidence (cite log lines and trace IDs), Root cause
(with file:line), {fix_section}, How to verify the fix.
"""


def agent_command(can_fix=None):
    can_fix = AGENT_CAN_FIX if can_fix is None else can_fix
    tools = AGENT_TOOLS + (FIX_TOOLS if can_fix else [])
    command = [
        "claude", "-p",
        "--output-format", "text",
        "--permission-mode", "dontAsk",
        "--no-session-persistence",
        "--allowedTools", *tools,
    ]
    if AGENT_MODEL:
        command += ["--model", AGENT_MODEL]
    return command


def agent_env():
    env = dict(os.environ)
    # An empty credential variable would shadow the one that is set.
    for name in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"):
        if not env.get(name):
            env.pop(name, None)
    return env


def run_agent(incident_dir, endpoint):
    """Run Claude Code headless. Returns the final status string."""
    if not AGENT_ENABLED:
        return "skipped: AGENT_ENABLED=false"
    if shutil.which("claude") is None:
        return "skipped: claude CLI not found"
    # Grant access to the incident folder in addition to the workspace.
    command = agent_command() + ["--add-dir", str(incident_dir.resolve())]
    log.info("Starting headless investigation for %s", incident_dir.name)
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            input=agent_prompt(incident_dir.resolve(), endpoint),
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=WORKSPACE_DIR,
            env=agent_env(),
            timeout=AGENT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        (incident_dir / "agent.log").write_text(str(exc.stderr or ""), encoding="utf-8")
        return f"failed: timed out after {AGENT_TIMEOUT_SECONDS}s"
    (incident_dir / "investigation.md").write_text(result.stdout, encoding="utf-8")
    (incident_dir / "agent.log").write_text(result.stderr, encoding="utf-8")
    elapsed = time.monotonic() - started
    if result.returncode != 0:
        return f"failed: claude exited with {result.returncode} after {elapsed:.0f}s (see agent.log)"
    if AGENT_CAN_FIX:
        changed = save_fix_diff(incident_dir)
        return f"done in {elapsed:.0f}s, " + ("fix applied (see fix.diff)" if changed else "no code changed")
    return f"done in {elapsed:.0f}s"


def save_fix_diff(incident_dir):
    """Save uncommitted changes under app/ to fix.diff. Returns True if any."""
    try:
        result = subprocess.run(
            # autocrlf matches Git for Windows, so CRLF checkouts diff cleanly.
            ["git", "--no-optional-locks", "-c", "core.autocrlf=true", "diff", "--", "app"],
            capture_output=True, text=True, encoding="utf-8", cwd=WORKSPACE_DIR, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("Could not compute fix diff: %s", exc)
        return False
    (incident_dir / "fix.diff").write_text(result.stdout, encoding="utf-8")
    return bool(result.stdout.strip())


# ---------------------------------------------------------------------------
# Incident pipeline


class Responder:
    def __init__(self, incidents_dir=INCIDENTS_DIR, investigate=None):
        self.incidents_dir = Path(incidents_dir)
        self.investigate = investigate or run_agent
        self.seen = set()
        self.lock = threading.Lock()
        self.jobs = queue.Queue()

    def set_status(self, incident_dir, state, **extra):
        status_file = incident_dir / "status.json"
        status = json.loads(status_file.read_text()) if status_file.exists() else {}
        status.update(extra, state=state, updated_at=datetime.now(timezone.utc).isoformat())
        write_json(status_file, status)
        log.info("%s: %s", incident_dir.name, state)

    def accept(self, payload):
        """Save each new firing alert and queue it. Returns incident ids."""
        accepted, skipped = [], []
        for alert in payload.get("alerts") or []:
            if alert.get("status") != "firing":
                skipped.append({"reason": "not firing", "status": alert.get("status")})
                continue
            key = alert_key(alert)
            with self.lock:
                if key in self.seen:
                    skipped.append({"reason": "already handled", "key": key})
                    continue
                self.seen.add(key)
            now = datetime.now(timezone.utc)
            incident_dir = self.incidents_dir / incident_id(alert, now)
            suffix = 1
            while incident_dir.exists():
                suffix += 1
                incident_dir = self.incidents_dir / f"{incident_id(alert, now)}-{suffix}"
            incident_dir.mkdir(parents=True)
            write_json(incident_dir / "alert.json", {**alert, "notification": {
                k: v for k, v in payload.items() if k != "alerts"
            }})
            self.set_status(incident_dir, "received", endpoint=alert_endpoint(alert), key=key)
            self.jobs.put((alert, incident_dir))
            accepted.append(incident_dir.name)
        return accepted, skipped

    def handle(self, alert, incident_dir):
        try:
            self.set_status(incident_dir, "collecting context")
            context = gather_context(alert, incident_dir)
            self.set_status(
                incident_dir, "investigating",
                trace_ids=context["trace_ids"], collection_errors=context["errors"],
            )
            result = self.investigate(incident_dir, context["endpoint"])
            self.set_status(incident_dir, result)
        except Exception as exc:  # Keep the worker alive for the next alert.
            log.exception("Incident %s failed", incident_dir.name)
            self.set_status(incident_dir, f"failed: {exc}")

    def work_forever(self):
        # One investigation at a time keeps load and cost predictable.
        while True:
            alert, incident_dir = self.jobs.get()
            self.handle(alert, incident_dir)
            self.jobs.task_done()


def make_handler(responder):
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, code, body):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/healthz":
                self.send_json(200, {"status": "ok", "queued": responder.jobs.qsize()})
            else:
                self.send_json(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/alerts":
                self.send_json(404, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(payload, dict):
                    raise ValueError("expected a JSON object")
            except ValueError as exc:
                self.send_json(400, {"error": f"invalid JSON: {exc}"})
                return
            accepted, skipped = responder.accept(payload)
            self.send_json(202, {"accepted": accepted, "skipped": skipped})

        def log_message(self, fmt, *args):
            log.info("%s %s", self.address_string(), fmt % args)

    return Handler


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    INCIDENTS_DIR.mkdir(parents=True, exist_ok=True)
    if AGENT_ENABLED and not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_CODE_OAUTH_TOKEN")):
        log.warning("No ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN set; investigations will fail")
    responder = Responder()
    threading.Thread(target=responder.work_forever, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), make_handler(responder))
    log.info("Listening on :%d, saving incidents to %s", PORT, INCIDENTS_DIR.resolve())
    server.serve_forever()


if __name__ == "__main__":
    main()
