# Incident context: Order Tracker 5xx server errors

- **Endpoint:** `/api/orders/{order_id}`
- **Status:** firing
- **Started:** 2026-10-04T12:00:00Z
- **Summary:** HTTP 5xx errors on /api/orders/{order_id}
- **Description:** 1 server error(s) (HTTP 5xx) on /api/orders/{order_id} in the last 5 minutes.
- **Value:** [ var='B' labels={http_route=/api/orders/{order_id}} value=1 ]
- **Labels:** `{"alertname": "Order Tracker 5xx server errors", "grafana_folder": "Order Tracker", "http_route": "/api/orders/{order_id}", "service": "order-tracker", "severity": "critical"}`
- **Dashboard:** http://127.0.0.1:3000/d/order-tracker/order-tracker?from=now-1h&to=now
- **Context window:** 2026-10-04T08:52:47.905860+00:00 to 2026-10-04T09:08:47.905860+00:00
- **Collected:** 2026-10-04T09:07:47.905860+00:00

## App health

`GET http://app:8000/healthz` -> `{"status": "ok"}`

## Failing traces (0 found, 0 saved)

TraceQL: `{ resource.service.name = "order-tracker" && status = error && span.http.route = "/api/orders/{order_id}" }`

- (no failing traces found)

## Logs for those traces

- (none)

## Error logs for order-tracker

- (no log lines)

## Raw data in this folder

- `alert.json`: the Grafana notification for this alert
- `app-health.json`, `tempo-search.json`, `traces/*.json`
- `loki-error-logs.json`, `loki-trace-logs.json`
