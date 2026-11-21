# 0003. Build exports in a cron job

Date: 2026-11-21
Status: Accepted

## Context

Customers can download their order history (design: docs/designs/2026-11-order-export). An export must be ready within 5 minutes for up to 500 orders (RQ3), on the existing VPS with no new paid service (RQ4).

## Decision

A cron job, `jobs/build_exports.py`, builds pending exports every minute, like the outbox job. Rejected: building the CSV in the request (may pass the website's 10 s timeout); a task queue such as Celery with Redis (a new service to run).

## Consequences

- Exports wait up to a minute before the job picks them up.
