# Design: order history export

Request: [architect.json](architect.json)
Requirements: RQ1–RQ6 in [requirements.jsonl](requirements.jsonl), all confirmed by the user on 2026-11-21.
Diagrams: [design.json](design.json)

## Goals and non-goals

- Goal: a logged-in customer gets a CSV of all their orders from their account page (RQ1), which also answers GDPR access requests without an hour of manual work.
- Non-goal: exporting other personal data (payment references, emails sent); deleting an account.

## Context

One VPS runs the shop API, the SQLite file and the cron jobs; the website is static on Netlify. Emails go through the outbox (ADR 0002). About 40 orders a day.

## Containers and components

- `api` gains `POST /v1/account/export`: checks the session cookie, checks the rate limit (RQ5), inserts an `exports` row with status `pending`, answers 202.
- New job `exportjob` (`jobs/build_exports.py`, cron every minute): for each pending export, reads the customer's orders and order lines, writes the CSV, writes it as `data/exports/<token>.csv` with a 32-character random token, deletes files older than 7 days, and adds an outbox row with the link. Marks the export `done`, or `failed` with the error.
- New `exportfiles`: CSV files in `data/exports/` on the VPS. `api` gains `GET /v1/account/export/<token>`, which serves a file only to the customer who asked for it, with their session cookie, for 7 days.

## Main flows

### Export order history

Flow `export` in design.json: steps x1–x9. On failure the job marks the export `failed` and adds an outbox email telling the customer to try again (RQ6).

## Data

- New table `exports` (id, customer_id, requested_at, status, token, error). Existing data unchanged.

## Perspectives

| Perspective | Applies | Why |
|---|---|---|
| Security | yes | New download path for personal data. |
| Observability | yes | New cron job; failures must reach customer and owners (RQ6). |
| API standards | no | docs/standards/api.md covers the new endpoint. |
| Data and privacy | yes | CSV holds names, addresses, order history; stored and emailed. |
| docs/standards/api.md | yes | Rules 1–4 apply to the new endpoint. |

## Decisions summary

- D1 Build exports in a cron job, not in the request: drivers RQ3, RQ4. The API stays responsive and the job follows the outbox pattern. Rejected: build the CSV in the request (a 500-order export with lines may take longer than the website's 10 s request timeout); a task queue such as Celery with Redis (a new service to run, against RQ4).
  - Assumes: one job run per minute keeps up with exports (a few a day).
- D2 Serve exports through the API behind the session cookie, revised after review finding V1: drivers RQ2, RQ4. The CSV stays in `data/exports/` on the VPS; `GET /v1/account/export/<token>` serves it to its owner only, for 7 days; the job deletes older files. Rejected: a public link on the static website (anyone with the link gets the data, forever: V1); attaching the CSV to the email (MailRelay limits attachments to 5 MB, and emails get forwarded).
  - Assumes: exports stay small enough for the VPS disk (a few a day, deleted after 7 days).

## Departures from existing patterns

- None.

## Unresolved questions

- None.
