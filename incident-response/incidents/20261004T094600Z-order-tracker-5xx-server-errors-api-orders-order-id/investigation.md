# Incident report: 5xx on `GET /api/orders/{order_id}`

## Summary
`GET /api/orders/express-1002` returns HTTP 500 every time. The code that computes the estimated delivery date for express orders adds 2 to the day-of-month. That raises `ValueError: day is out of range for month` whenever the order was placed on day 29 or later of a month. The failure comes from the seeded data: `express-1002` is created on the last day of the previous month (2026-09-30). I did not look at how production orders are created. The same bug would hit any express order placed on the 29th, 30th or 31st.

## Impact
- Every lookup of an affected express order fails with a 500. In this data that is `express-1002`; its `created_at` is `2026-09-30T10:45:05Z`.
- Standard orders are unaffected. `standard-1001` returned 200 on a live request.
- Express orders placed on days 1–28 are unaffected. The failure is date-dependent.
- Express orders created through `POST /api/orders` or changed through `PATCH /api/orders/{id}` also call `get_order`, so those requests would return 500 for the same reason (`create_order` at line 187 and `update_status` at line 201). I did not test them.
- The alert reported 8 server errors in 5 minutes. `/healthz` stayed `ok`, so health checks did not catch it.

## Timeline
All times are UTC on 2026-10-04.
- 09:36:01: first logged failure (trace `0353c5e6f77169c812db62f8c24bee14`).
- 09:36:49 and 09:38:31: further failures (traces `ef2bda11491d0a656ba322145dee3364` and `eb7a4b23635fd0b317bb7dc96d525664`).
- 09:45:30–09:45:47: burst of failures (traces `8b961756…`, `685cbf02…`, `6129ca4b…`, `8e649a68…`, `a39299c3…`, `e7176915…`, `723c6651…`).
- 09:45:50: Grafana alert started.
- 09:46:17: I reproduced the 500 with a read-only GET. The live app was still running the unfixed code.
- After the 09:46:17 reproduction: I applied the fix in `app/main.py`. The running app has not been rebuilt, so the endpoint will not recover until it is.

## Evidence
- Loki, `2026-10-04T09:45:30.848Z`, "Order lookup failed": `{"exception_type":"ValueError","exception_message":"day is out of range for month","order_id":"express-1002","trace_id":"8b961756daed067e36a314e4f384e675"}`. The traceback ends at `app/main.py:80`, in `order_detail`, at `placed_at.replace(day=placed_at.day + 2)`.
- The same log line, with the same traceback, appears at 09:36:01, 09:36:49, 09:38:31 and at 09:45:32, 09:45:33, 09:45:36, 09:45:42, 09:45:45 and 09:45:47.
- Failing traces (all `GET /api/orders/{order_id}`, status 500, `url.path=/api/orders/express-1002`):
  - `8e649a682ed11bdb1431500ccf575eed`
  - `6129ca4bf2294cfe6aaa98e2575cd50f`
  - `685cbf023b0615efff4eb3d12bb48c27`
  - `8b961756daed067e36a314e4f384e675`
  - `eb7a4b23635fd0b317bb7dc96d525664`
- In each trace the child span `order.lookup` has `order.found=true` and `order.priority=express`, and records the same exception.
- Live reproduction: `curl http://app:8000/api/orders/express-1002` returned `HTTP/1.1 500 Internal Server Error`. `GET /api/orders/standard-1001` returned 200.
- `GET /api/orders` shows `express-1002` with `created_at: 2026-09-30T10:45:05+00:00`. Adding 2 to day 30 of a 30-day month gives day 32, which is invalid.
- Prometheus `order_tracker_http_requests_total{http_route="/api/orders/{order_id}",http_response_status_code="500"}` is non-zero.

## Root cause
`app/main.py:80` in `order_detail`:
```python
estimated_at = placed_at.replace(day=placed_at.day + 2)
```
`datetime.replace(day=...)` does not roll over into the next month. Any `created_at` on day 29 or later of a month overflows, for example 30 + 2 = 32, and raises `ValueError`. The exception is not handled in `get_order` (`app/main.py:165-168`), which logs it and re-raises, so the client gets a 500.

## Fix applied
`app/main.py:80`. Date arithmetic now uses `timedelta`, which handles month and year boundaries. `timedelta` was already imported.
```diff
--- a/app/main.py
+++ b/app/main.py
@@ -77,7 +77,7 @@ def order_detail(row):
     order = as_dict(row)
     if order["priority"] == "express":
         placed_at = datetime.fromisoformat(order["created_at"])
-        estimated_at = placed_at.replace(day=placed_at.day + 2)
+        estimated_at = placed_at + timedelta(days=2)
         order["estimated_delivery"] = estimated_at.date().isoformat()
     return order
```
I did not run the test suite or exercise the changed code.

## How to verify the fix
1. Rebuild and redeploy the app, because the running container still has the old code.
2. Run `curl -i http://app:8000/api/orders/express-1002`. It should return 200 with `estimated_delivery` set to `2026-10-02` for the seeded order, which was placed on 2026-09-30.
3. Check that `order_tracker_http_requests_total{http_route="/api/orders/{order_id}",http_response_status_code="500"}` stops increasing and the Grafana alert resolves.
4. In Loki, run `{service_name="order-tracker"} |= "Order lookup failed"`. There should be no new entries after the deploy.
5. Add a regression test for an express order with `created_at` on the last day of a month, and one on 31 December to cover the year boundary. Expect the estimate to roll into the next month or year.
