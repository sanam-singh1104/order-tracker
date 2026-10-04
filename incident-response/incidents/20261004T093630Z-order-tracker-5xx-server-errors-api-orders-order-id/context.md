# Incident context: Order Tracker 5xx server errors

- **Endpoint:** `/api/orders/{order_id}`
- **Status:** firing
- **Started:** 2026-10-04T09:36:20Z
- **Summary:** HTTP 5xx errors on /api/orders/{order_id}
- **Description:** 1 server error(s) (HTTP 5xx) on /api/orders/{order_id} in the last 5 minutes.
- **Value:** [ var='A' labels={http_route=/api/orders/{order_id}} type='query' value=1.0341796370029475 ], [ var='B' labels={http_route=/api/orders/{order_id}} type='reduce' value=1.0341796370029475 ], [ var='C' labels={http_route=/api/orders/{order_id}} type='threshold' value=1 ]
- **Labels:** `{"alertname": "Order Tracker 5xx server errors", "grafana_folder": "Order Tracker", "http_route": "/api/orders/{order_id}", "service": "order-tracker", "severity": "critical"}`
- **Dashboard:** http://127.0.0.1:3000/d/order-tracker/order-tracker?from=now-1h&to=now
- **Context window:** 2026-10-04T09:21:20+00:00 to 2026-10-04T09:37:30.367010+00:00
- **Collected:** 2026-10-04T09:36:30.367010+00:00

## App health

`GET http://app:8000/healthz` -> `{"status": "ok"}`

## Failing traces (1 found, 1 saved)

TraceQL: `{ resource.service.name = "order-tracker" && status = error && span.http.route = "/api/orders/{order_id}" }`

#### Trace `353c5e6f77169c812db62f8c24bee14`

- **GET /api/orders/{order_id}** status=ERROR duration=152.4ms
  - attributes: `{"http.request.method": "GET", "http.response.status_code": "500", "http.route": "/api/orders/{order_id}", "url.path": "/api/orders/express-1002"}`
  - event **exception**
    - exception.type: `ValueError`
    - exception.message: `day is out of range for month`

```
Traceback (most recent call last):
  File "/app/app/main.py", line 113, in telemetry_middleware
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/app/.venv/lib/python3.12/site-packages/starlette/middleware/base.py", line 168, in call_next
    raise app_exc from app_exc.__cause__ or app_exc.__context__
  File "/app/.venv/lib/python3.12/site-packages/starlette/middleware/base.py", line 144, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "/app/.venv/lib/python3.12/site-packages/starlette/middleware/exceptions.py", line 63, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "/app/.venv/lib/python3.12/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/app/.venv/lib/python3.12/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "/app/.venv/lib/python3.12/site-packages/fastapi/middleware/asyncexitstack.py", line 18, in __call__
    await self.app(scope, receive, send)
  File "/app/.venv/lib/python3.12/site-packages/starlette/routing.py", line 670, in __call__
    await self.middleware_stack(scope, receive, send)
  File "/app/.venv/lib/python3.12/site-packages/fastapi/routing.py", line 2734, in app
    await route.handle(scope, receive, send)
  File "/app/.venv/lib/python3.12/site-packages/fastapi/routing.py", line 1281, in handle
    await super().handle(scope, receive, send)
  File "/app/.venv/lib/python3.12/site-packages/starlette/routing.py", line 280, in handle
    await self.app(scope, receive, send)
  File "/app/.venv/lib/python3.12/site-packages/fastapi/routing.py", line 158, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "/app/.venv/lib/python3.12/site-packages/starlette/_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "/app/.venv/lib/python3.12/site-packages/starlette/_exception_handler.py", line 42, in wrapped_app
    await app(
```

- **order.lookup** status=ERROR duration=73.3ms
  - attributes: `{"order.found": true, "order.id": "express-1002", "order.priority": "express"}`
  - event **exception**
    - exception.type: `ValueError`
    - exception.message: `day is out of range for month`

```
Traceback (most recent call last):
  File "/app/.venv/lib/python3.12/site-packages/opentelemetry/trace/__init__.py", line 602, in use_span
    yield span
  File "/app/.venv/lib/python3.12/site-packages/opentelemetry/sdk/trace/__init__.py", line 1136, in start_as_current_span
    yield span
  File "/app/app/main.py", line 165, in get_order
    order = order_detail(row)
            ^^^^^^^^^^^^^^^^^
  File "/app/app/main.py", line 80, in order_detail
    estimated_at = placed_at.replace(day=placed_at.day + 2)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ValueError: day is out of range for month
```


## Logs for those traces

- (no log lines)

## Error logs for order-tracker

- `2026-10-04T09:36:01.429+00:00` Order lookup failed `{"exception_message": "day is out of range for month", "exception_type": "ValueError", "order_id": "express-1002", "severity_text": "ERROR", "span_id": "e8f49a25244df93b", "trace_id": "0353c5e6f77169c812db62f8c24bee14"}`

```
Traceback (most recent call last):
  File "/app/app/main.py", line 165, in get_order
    order = order_detail(row)
            ^^^^^^^^^^^^^^^^^
  File "/app/app/main.py", line 80, in order_detail
    estimated_at = placed_at.replace(day=placed_at.day + 2)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ValueError: day is out of range for month
```


## Raw data in this folder

- `alert.json`: the Grafana notification for this alert
- `app-health.json`, `tempo-search.json`, `traces/*.json`
- `loki-error-logs.json`, `loki-trace-logs.json`
