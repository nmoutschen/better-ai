# 0004. Serve exports through the API

Date: 2026-11-21
Status: Accepted

## Context

An export holds a customer's name, addresses and order history. It must reach only that customer (RQ2, API standard rule 3).

## Decision

The CSV stays on the VPS. `GET /v1/account/export/<token>` serves it to its owner only, with the session cookie, for 7 days; the job deletes older files. Rejected: a public link on the static website (anyone with the link gets the data, forever); attaching the CSV to the email (5 MB limit, and emails get forwarded).

## Consequences

- A download endpoint and file clean-up to maintain on the VPS.
