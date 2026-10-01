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

The app uses the OpenTelemetry SDK (`app/telemetry.py`) and writes all signals to stdout as JSON. View them with `docker compose logs -f app`.

- **Metrics** are printed every 10s (`OTEL_METRIC_EXPORT_INTERVAL`). `order_tracker.http.requests` (counter) and `http.server.request.duration` (histogram, seconds) both carry the attributes `http.route`, `http.response.status_code`, and `http.request.method`.
- **Traces**: each request gets a `GET /api/orders/{order_id}` server span. Each order lookup gets a child `order.lookup` span with `order.id`, `order.found`, and `order.priority`.
- **Logs**: `Order lookup succeeded` (INFO), `Order not found` (WARN), and `Order lookup failed` (ERROR, with the exception). Each log includes `trace_id`/`span_id` so you can match it to its span.

Set `ORDER_TRACKER_CONSOLE_TELEMETRY=false` to turn the exporters off; the tests do this.

The app uses SQLite to keep setup small. Run one app container at a time. The course exercise is about detecting and handling an incident, not scaling the database.
