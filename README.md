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

Check its state under **Alerting → Alert rules** in Grafana. No contact point is configured yet, so firing alerts are visible in Grafana but not delivered anywhere.

OTLP export is on when `OTEL_EXPORTER_OTLP_ENDPOINT` is set. Set `ORDER_TRACKER_CONSOLE_TELEMETRY=true` in `compose.yaml` to also print all signals to `docker compose logs app`. The tests turn both off.

The app uses SQLite to keep setup small. Run one app container at a time. The course exercise is about detecting and handling an incident, not scaling the database.
