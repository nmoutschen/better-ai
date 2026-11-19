# Outage log, 12 March

- 09:12 Alerts: checkout error rate above 20%.
- 09:15 On-call (Rui) confirms payments failing with timeouts.
- 09:21 Cause found: the payment provider rotated its TLS certificate; our pinned certificate no longer matched.
- 09:34 Pin updated and deployed; error rate back under 1% by 09:40.
- 09:55 412 orders failed during the outage; 380 retried automatically, 32 customers emailed.
- Follow-up: replace certificate pinning with provider key validation (owner: Rui, due 26 March).
