# Incident context: Order Tracker 5xx server errors

- **Endpoint:** `/api/orders/{order_id}`
- **Status:** firing
- **Started:** 2026-10-04T08:29:20Z
- **Summary:** HTTP 5xx errors on /api/orders/{order_id}
- **Description:** 1 server error(s) (HTTP 5xx) on /api/orders/{order_id} in the last 5 minutes.
- **Value:** [ var='A' labels={http_route=/api/orders/{order_id}} type='query' value=1.0341618118514944 ], [ var='B' labels={http_route=/api/orders/{order_id}} type='reduce' value=1.0341618118514944 ], [ var='C' labels={http_route=/api/orders/{order_id}} type='threshold' value=1 ]
- **Labels:** `{"alertname": "Order Tracker 5xx server errors", "grafana_folder": "Order Tracker", "http_route": "/api/orders/{order_id}", "service": "order-tracker", "severity": "critical"}`
- **Dashboard:** http://127.0.0.1:3000/d/order-tracker/order-tracker?from=now-1h&to=now
- **Context window:** 2026-10-04T08:14:20+00:00 to 2026-10-04T08:30:37.390708+00:00
- **Collected:** 2026-10-04T08:29:37.390708+00:00

## App health

`GET http://app:8000/healthz` -> `{"status": "ok"}`

## Failing traces (4 found, 4 saved)

TraceQL: `{ resource.service.name = "order-tracker" && status = error && span.http.route = "/api/orders/{order_id}" }`

#### Trace `d1db5c95a620f3498dae12c977b2a6fe`

- **GET /api/orders/{order_id}** status=ERROR duration=61.6ms
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

- **order.lookup** status=ERROR duration=29.3ms
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


#### Trace `aa57080be42fe36b8ed1c5d8d535cef1`

- **GET /api/orders/{order_id}** status=ERROR duration=9.3ms
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

- **order.lookup** status=ERROR duration=2.2ms
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


#### Trace `87b8cc6d2ef5805772b9bc00611012c1`

- **GET /api/orders/{order_id}** status=ERROR duration=8.1ms
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

- **order.lookup** status=ERROR duration=3.3ms
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


#### Trace `74eb81ef80174d10cf686042a2dc5daf`

- **GET /api/orders/{order_id}** status=ERROR duration=281.8ms
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

- **order.lookup** status=ERROR duration=104.0ms
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

- `2026-10-04T08:23:43.779+00:00` Order lookup failed `{"exception_message": "day is out of range for month", "exception_type": "ValueError", "order_id": "express-1002", "severity_text": "ERROR", "span_id": "b87e99f727ba5af9", "trace_id": "74eb81ef80174d10cf686042a2dc5daf"}`

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

- `2026-10-04T08:23:44.054+00:00` Order lookup failed `{"exception_message": "day is out of range for month", "exception_type": "ValueError", "order_id": "express-1002", "severity_text": "ERROR", "span_id": "dd4c6a005e9249d0", "trace_id": "87b8cc6d2ef5805772b9bc00611012c1"}`

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

- `2026-10-04T08:23:44.158+00:00` Order lookup failed `{"exception_message": "day is out of range for month", "exception_type": "ValueError", "order_id": "express-1002", "severity_text": "ERROR", "span_id": "5ec4d2c829477513", "trace_id": "aa57080be42fe36b8ed1c5d8d535cef1"}`

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

- `2026-10-04T08:28:46.845+00:00` Order lookup failed `{"exception_message": "day is out of range for month", "exception_type": "ValueError", "order_id": "express-1002", "severity_text": "ERROR", "span_id": "1cd40df8e738dea6", "trace_id": "d1db5c95a620f3498dae12c977b2a6fe"}`

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


## Error logs for order-tracker

- `2026-10-04T08:23:43.779+00:00` Order lookup failed `{"exception_message": "day is out of range for month", "exception_type": "ValueError", "order_id": "express-1002", "severity_text": "ERROR", "span_id": "b87e99f727ba5af9", "trace_id": "74eb81ef80174d10cf686042a2dc5daf"}`

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

- `2026-10-04T08:23:44.054+00:00` Order lookup failed `{"exception_message": "day is out of range for month", "exception_type": "ValueError", "order_id": "express-1002", "severity_text": "ERROR", "span_id": "dd4c6a005e9249d0", "trace_id": "87b8cc6d2ef5805772b9bc00611012c1"}`

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

- `2026-10-04T08:23:44.158+00:00` Order lookup failed `{"exception_message": "day is out of range for month", "exception_type": "ValueError", "order_id": "express-1002", "severity_text": "ERROR", "span_id": "5ec4d2c829477513", "trace_id": "aa57080be42fe36b8ed1c5d8d535cef1"}`

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

- `2026-10-04T08:28:46.845+00:00` Order lookup failed `{"exception_message": "day is out of range for month", "exception_type": "ValueError", "order_id": "express-1002", "severity_text": "ERROR", "span_id": "1cd40df8e738dea6", "trace_id": "d1db5c95a620f3498dae12c977b2a6fe"}`

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
