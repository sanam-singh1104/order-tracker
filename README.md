# Order Tracker

A small order tracking app for the AI Dev Tools Zoomcamp observability homework. It includes a web page, API, tests, and a Docker Compose setup. You add telemetry, alerts, and an incident responder in Homework 4.

The main user flow is creating an order and checking its status. Three sample orders are created on first startup.

## Run it

You need Docker with Compose. To run the tests, you also need Python 3.11+ and `uv`.

```bash
docker compose up --build -d --wait
```

Open <http://127.0.0.1:8000>. The API is at `/api/orders`, and the health check is at `/healthz`. Data is stored in a Docker volume and survives container recreation.

If port 8000 is occupied, set `ORDER_TRACKER_PORT`, for example:

```bash
ORDER_TRACKER_PORT=18080 docker compose up --build -d --wait
```

Run tests with `uv run --frozen pytest -q`. Stop the app with `docker compose down`. Add `-v` only if you also want to delete the order data.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Web page |
| GET | `/healthz` | Database health check |
| GET | `/api/orders` | List orders |
| POST | `/api/orders` | Create an order |
| GET | `/api/orders/{id}` | Check an order |
| PATCH | `/api/orders/{id}` | Change an order status |

## Telemetry

The app uses the OpenTelemetry SDK (`app/telemetry.py`) and sends OTLP to an OpenTelemetry Collector. The Collector forwards each signal to its own backend, and Grafana shows all three:

```
app --OTLP--> otel-collector --> Prometheus (metrics)
                             --> Loki       (logs)
                             --> Tempo      (traces)   --> Grafana
```

`docker compose up --build -d --wait` starts the whole stack. All config is under `observability/`:

| File | Purpose |
| --- | --- |
| `otel-collector.yaml` | OTLP receiver, pipelines to Prometheus, Loki, and Tempo |
| `prometheus.yml` | Prometheus settings; metrics arrive via its OTLP receiver |
| `loki.yaml` | Single-process Loki with filesystem storage |
| `tempo.yaml` | Single-binary Tempo with local storage |
| `grafana/provisioning/` | Datasources (with trace/log links) and dashboard provider |
| `grafana/dashboards/order-tracker.json` | The Order Tracker dashboard |

Open Grafana at <http://127.0.0.1:3000> (set `GRAFANA_PORT` to change it). Anyone can view dashboards and use Explore without logging in. Sign in as `admin` / `admin` (or `GRAFANA_ADMIN_PASSWORD`) to edit. Prometheus is at <http://127.0.0.1:9090> (`PROMETHEUS_PORT`).

What the app emits:

- **Metrics** (every 10s, `OTEL_METRIC_EXPORT_INTERVAL`): `order_tracker.http.requests` (counter) and `http.server.request.duration` (histogram, seconds), both with `http.route`, `http.response.status_code`, and `http.request.method`. In Prometheus they are `order_tracker_http_requests_total` and `http_server_request_duration_seconds_*`, with labels `http_route`, `http_response_status_code`, and `http_request_method`.
- **Traces**: each request gets a server span (for example `GET /api/orders/{order_id}`). Each order lookup gets a child `order.lookup` span with `order.id`, `order.found`, and `order.priority`.
- **Logs**: `Order lookup succeeded` (INFO), `Order not found` (WARN), and `Order lookup failed` (ERROR, with the exception). Each log carries `trace_id`/`span_id`. In Grafana, a log's TraceID link opens its trace, and a span's "Logs for this span" button opens its logs.

### Alerts

`observability/grafana/provisioning/alerting/order-tracker-alerts.yaml` provisions **Order Tracker 5xx server errors** (folder *Order Tracker*). Every 30s it computes 5xx responses per endpoint over the last 5 minutes and fires as soon as one endpoint has any. Each alert includes the endpoint, the 5-minute window, and a dashboard link. Endpoints that served traffic without errors report 0 (Normal), and no traffic at all is treated as OK, so quiet periods never show "No Data".

Check its state under **Alerting → Alert rules** in Grafana. `observability/grafana/provisioning/alerting/incident-responder.yaml` sends every firing alert to the incident responder through a webhook contact point (grouped per endpoint, 10s group wait, repeated every 4h while firing).

### Incident responder

`incident-response/` is a small service (stdlib Python plus the Claude Code CLI) that runs in Compose as `incident-responder` and listens on <http://127.0.0.1:8001> (`INCIDENT_RESPONDER_PORT`). When Grafana POSTs an alert to `/alerts`, it:

1. Saves the alert in `incident-response/incidents/<time>-<alert>-<endpoint>/alert.json` and replies `202` right away.
2. Collects context from inside the Compose network: app health (`http://app:8000/healthz`), failing traces on the alerted endpoint from Tempo (TraceQL `status = error && span.http.route = "<endpoint>"`, up to 5 full traces), and Loki logs for those traces plus all recent error logs. It writes a readable summary to `context.md`, next to the raw JSON.
3. Starts Claude Code headless (`claude -p`) with the repo mounted at `/workspace`. The agent gets `Read`, `Grep`, `Glob`, `curl`, `jq`, and `Edit` limited to `app/**` (permission mode `dontAsk` denies all other tools). It queries the app, Loki, Tempo, and Prometheus, then applies a fix to `app/`, the only writable part of the mount. Its report (summary, evidence, root cause, applied fix) is saved to `investigation.md`, its change to `fix.diff`, and stderr to `agent.log`. The fix lands in your working tree as an uncommitted change, so review it with `git diff`. The running app picks it up only after a rebuild (`docker compose up -d --build app`). Set `INCIDENT_AGENT_CAN_FIX=false` to have the agent only investigate and suggest a diff.

`status.json` in each folder shows progress (`received` → `collecting context` → `investigating` → `done`/`failed`). Resolved notifications and repeats of an alert that is already handled are skipped. One investigation runs at a time, with a 15 minute limit.

Claude Code needs credentials. Put one of these in `.env` (gitignored) or your shell before starting:

```bash
ANTHROPIC_API_KEY=sk-ant-...
# or a Claude subscription token, created with `claude setup-token`:
CLAUDE_CODE_OAUTH_TOKEN=...
```

Without credentials the responder still saves the alert and context, and the investigation fails with "Not logged in". Set `INCIDENT_AGENT_ENABLED=false` to skip the agent on purpose, and `INCIDENT_AGENT_MODEL` to pick a model.

**Send a test alert** (a Grafana-style payload, no real errors needed):

```bash
curl -X POST http://127.0.0.1:8001/alerts -H "Content-Type: application/json" --data-binary @incident-response/sample-alert.json
```

On Windows PowerShell, use `curl.exe` instead of `curl`. A repeat of the same alert is skipped until the responder restarts; change `fingerprint` or `startsAt` in the file to send it again.

**Full automatic flow** (alert → webhook → agent fix → verify):

1. Rebuild and start everything. The second command makes Grafana reload the alerting provisioning, which it reads only at startup:

   ```bash
   docker compose up --build -d --wait
   docker compose up -d --force-recreate --wait grafana
   ```

2. Make sure the alert is Normal under **Alerting → Alert rules**. It stays firing for 5 minutes after the last 5xx, and Grafana does not resend an alert that is still firing.
3. Trigger the failure. The express order placed at the end of last month returns a 500:

   ```bash
   curl http://127.0.0.1:8000/api/orders/express-1002
   ```

4. Watch Grafana send the webhook. Within about 40 seconds (30s rule interval + 10s group wait), the rule turns Firing and the responder logs `POST /alerts ... 202`:

   ```bash
   docker compose logs -f incident-responder
   ```

5. Watch the agent. The log moves through `collecting context` → `investigating` → `done in Ns, fix applied (see fix.diff)`, usually within a minute. Then check `incident-response/incidents/<newest>/investigation.md`, `fix.diff`, and `git diff app`.
6. Verify. Rebuild the app with the fix and repeat the request, which now returns 200 with an `estimated_delivery`:

   ```bash
   docker compose up -d --build --wait app
   curl http://127.0.0.1:8000/api/orders/express-1002
   ```

The alert returns to Normal about 5 minutes later. Commit the fix if you keep it.

OTLP export is on when `OTEL_EXPORTER_OTLP_ENDPOINT` is set. Set `ORDER_TRACKER_CONSOLE_TELEMETRY=true` in `compose.yaml` to also print all signals to `docker compose logs app`. The tests turn both off.

The app uses SQLite to keep setup small. Run one app container at a time. The course exercise is about detecting and handling an incident, not scaling the database.
