# Incident report: 5xx on `GET /api/orders/{order_id}`

## Summary
`GET /api/orders/express-1002` returns HTTP 500. The handler computes the estimated delivery date by adding 2 to the day-of-month. The order was placed on 2026-09-30, so the result is day 32, which is invalid. I fixed the date arithmetic in `app/main.py`.

## Impact
- **Affected:** express-priority orders placed on day 29, 30 or 31 of a month. Currently that is only `express-1002`, whose detail lookup always fails. The same bug will hit any express order placed within 2 days of a month end.
- **Not affected:** standard orders and `GET /api/orders` (the list endpoint). `/healthz` stays "ok", so health checks don't show the problem.
- The alert reported 1 error in 5 minutes. I didn't check how many requests failed in total.

## Timeline
- **2026-09-30T10:45Z:** `express-1002` was seeded with `created_at` set to the last day of the previous month. Seeding is in `init_db`, `app/main.py:60-63`.
- **2026-10-04T09:36:01Z:** The lookup for `express-1002` threw `ValueError`, giving a 500 (trace `0353c5e6f77169c812db62f8c24bee14`).
- **2026-10-04T09:36:20Z:** The Grafana alert started firing.
- **2026-10-04T09:36:30Z:** The incident context was collected.
- **2026-10-04T09:36:48Z:** I reproduced the 500 with a read-only `curl`.

## Evidence
- **Loki**, 09:36:01.429Z: `Order lookup failed {"exception_type": "ValueError", "exception_message": "day is out of range for month", "order_id": "express-1002", "trace_id": "0353c5e6f77169c812db62f8c24bee14", "span_id": "e8f49a25244df93b"}`.
- **Trace `0353c5e6f77169c812db62f8c24bee14`:**
  - The root span `GET /api/orders/{order_id}` has status ERROR, HTTP 500, and a duration of 152 ms.
  - The child span `order.lookup` has `order.id=express-1002`, `order.priority=express` and the same `ValueError`.
  - The traceback ends at `main.py:80`, `placed_at.replace(day=placed_at.day + 2)`.
- **Reproduction:** `curl -i http://app:8000/api/orders/express-1002` returned `HTTP/1.1 500 Internal Server Error`.
- **Data:** `GET /api/orders` shows `express-1002` with `created_at: 2026-09-30T10:45:05+00:00`. September has 30 days, so 30 + 2 = 32 is out of range.

## Root cause
`app/main.py:80`, in `order_detail`, did `placed_at.replace(day=placed_at.day + 2)`. `datetime.replace` doesn't carry overflow into the next month, so it raises `ValueError` whenever `day + 2` exceeds the month's length. The exception isn't caught, so the endpoint returns a 500.

## Fix applied
`app/main.py:80` now adds a `timedelta`, which handles month and year rollover. `timedelta` was already imported.

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

## How to verify the fix
1. Rebuild and redeploy the app. The running container won't pick up the change until then.
2. Run `curl -i http://app:8000/api/orders/express-1002`. It should return 200 with `estimated_delivery` of `2026-10-02`.
3. Run `curl http://app:8000/api/orders/standard-1001`. It should still return 200.
4. Add a regression test for an express order dated the 30th or 31st, including a December-to-January case. I didn't write one because `tests/` is read-only for me.
5. Check Grafana: `order_tracker_http_requests_total{http_route="/api/orders/{order_id}", http_response_status_code=~"5.."}` should stop increasing, and the alert should resolve.
