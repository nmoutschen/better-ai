# Load test notes: checkout-api, 2026-11-17

Ran against staging with k6: four stages of 10 minutes each, scenario = browse, add to cart, pay with a test card.
Per-stage numbers are in results/summary.csv.

- SLO for checkout-api: p95 under 400 ms, errors under 1%.
- Stages 1 to 3 are within the SLO. Stage 4 (750 users) breaks both: p95 1,480 ms, errors 6.8%, almost all HTTP 503.
- The 503s start when the database connection pool reaches its maximum of 50 connections (pool metrics on the Grafana
  dashboard "checkout-db"). CPU on the app nodes stayed under 60% throughout.
- Throughput flattens: 1,950 to 2,210 requests/s going from 500 to 750 users, so requests are queueing, not getting done.
- Caveat: the staging database is a smaller instance than production (4 vCPU against 16) and holds about a third of the
  production data. Production may answer queries faster, but the pool limit is the same setting (50) in both.
- Last year's Black Friday peak was about 620 concurrent checkout users (analytics, 2025-11-28).
- Ideas: raise the pool to 100 and rerun stage 4; look at slow queries on the payment step.
