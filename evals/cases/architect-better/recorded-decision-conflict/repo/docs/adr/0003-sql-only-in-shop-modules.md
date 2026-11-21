# 0003. SQL only in the shop's data modules

Date: 2026-02-20
Status: Accepted

## Context

In February we added `status` values to `orders`. `jobs/send_emails.py` ran its own SQL on `shop.db`, its query broke
on the new values, and no confirmation email went out for a day. Nobody knew the job read that table.

## Decision

Only `shop/store.py` and `shop/outbox.py` run SQL on `shop.db`. The API, the jobs and any script call their functions;
none of them opens the database with its own queries.

## Consequences

- A schema change touches one module, and its tests show every query that changes.
- A new job that needs new data first adds a function to `shop/store.py`.
- Slightly more code for a one-off query.
