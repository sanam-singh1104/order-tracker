# Incident report: 5xx on `/api/orders/{order_id}`

**Limitation:** The Bash tool was denied in this session, so I could not run curl against the app, Loki, Tempo or Prometheus. I did not reproduce the failure. The root cause below comes from the incident files and the source code only. It is not confirmed by live logs or traces.

## Summary
`GET /api/orders/{order_id}` raises an unhandled `ValueError` and returns HTTP 500 for any `express` order placed on day 27 or later of a month. The estimated-delivery calculation in `order_detail` builds a date with `placed_at.replace(day=placed_at.day + 2)`. That call fails when `day + 2` is greater than the number of days in the month. The seeded order `express-1002` is dated the last day of the previous month, so it hits this bug.

## Impact
- Every request for `express` orders created on day 27 or later of any month returns 500. Day 27 only fails in February of a non-leap year; the other thresholds are day 29 in February of a leap year, day 29 in 30-day months and day 30 in 31-day months.
- `PATCH /api/orders/{id}` and `POST /api/orders` call `get_order` at the end (`app/main.py:187`, `:201`). For affected express orders, a status update is committed and the request then returns 500, and creating an express order on those days returns 500 after the order is saved.
- Standard orders and `GET /api/orders` (list) are unaffected, because `order_detail` is not called for them.
- The alert value is 1 error in 5 minutes, so exposure so far looks limited.

## Timeline
- 2026-10-04 08:52:47Z to 09:08:47Z: the incident context window.
- 2026-10-04 09:07:47Z: context collected. It found 0 failing traces and 0 error logs, and `/healthz` returned ok.
- 2026-10-04T12:00:00Z: the alert's `startsAt`. The alert fingerprint is `manual-test` and its message is "Manual test alert". This may be a synthetic or manually triggered alert, and its start time is later than the collection time.

## Evidence
- `context.md` and `alert.json` show the alert on `http_route=/api/orders/{order_id}` with value 1. They contain no failing traces (0 found) and no error log lines, so there are no trace IDs or log lines to cite. I could not query Loki, Tempo or Prometheus to look further.
- Code evidence:
  - `app/main.py:63` seeds `express-1002` with `created_at` equal to the last day of the previous month. Today is 2026-10-04, so that is 2026-09-30.
  - `app/main.py:80` calls `placed_at.replace(day=placed_at.day + 2)`. For 2026-09-30 this is `replace(day=32)`, which raises `ValueError: day is out of range for month`.
  - `app/main.py:166-168` logs "Order lookup failed" with `logger.exception` and re-raises, so FastAPI returns 500. The span `order.lookup` should carry the exception.
- Expected live reproduction (not run): `curl -i http://app:8000/api/orders/express-1002` should return 500, and Loki should show an "Order lookup failed" line with a `ValueError` traceback. `curl -i http://app:8000/api/orders/standard-1001` should return 200.

## Root cause
`app/main.py:80`:
```python
estimated_at = placed_at.replace(day=placed_at.day + 2)
```
This is day arithmetic with no month rollover. `datetime.replace` validates the day against the month length. Any express order placed within 2 days of month end raises `ValueError`. The seed data at `app/main.py:60-63` deliberately or accidentally includes such an order.

## Suggested fix
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
`timedelta` is already imported, since line 60 uses it.

## How to verify the fix
1. Add a unit test that calls `order_detail` with an express row whose `created_at` is `2026-09-30T00:00:00+00:00`, and with one on `2026-02-27`. Assert that `estimated_delivery` is `2026-10-02` and `2026-03-01` respectively.
2. Run `curl -i http://app:8000/api/orders/express-1002`. It should return 200 with `estimated_delivery` set to the first days of the current month.
3. Run `curl -i http://app:8000/api/orders/standard-1001`. It should still return 200.
4. Check that the alert clears. `order_tracker_http_requests_total{http_route="/api/orders/{order_id}",http_status_code=~"5.."}` should stop increasing, and no new "Order lookup failed" lines should appear in Loki.
5. Confirm the alert source. The fingerprint `manual-test` suggests a synthetic alert, so check whether a real 5xx occurred.
