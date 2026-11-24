# 0001. SQLite for orders

Date: 2025-09-02
Status: Accepted

## Context

Two people run the shop. We take about 40 orders a day. Nobody wants to run a database server.

## Decision

Keep all shop data in one SQLite file on the VPS, backed up nightly.

## Consequences

- One writer at a time; fine at our volume.
- No separate database to patch or pay for.
- Moving to a server database later means a migration.
