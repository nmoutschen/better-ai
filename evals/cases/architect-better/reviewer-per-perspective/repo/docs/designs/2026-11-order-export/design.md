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
- New job `exportjob` (`jobs/build_exports.py`, cron every minute): for each pending export, reads the customer's orders and order lines, writes the CSV, uploads it to the website as `/exports/<token>.csv` with a 32-character random token, and adds an outbox row with the link. Marks the export `done`, or `failed` with the error.
- New `exportfiles`: CSV files on the Netlify site, uploaded through Netlify's deploy API with a deploy token kept in the job's environment.

## Main flows

### Export order history

Flow `export` in design.json: steps x1–x8. On failure the job marks the export `failed` and adds an outbox email telling the customer to try again (RQ6).

## Data

- New table `exports` (id, customer_id, requested_at, status, token, error). Existing data unchanged.

## Perspectives

| Perspective | Applies | Why |
|---|---|---|
| Security | yes | New download path for personal data; new Netlify deploy token. |
| Observability | yes | New cron job; failures must reach customer and owners (RQ6). |
| API standards | no | docs/standards/api.md covers the new endpoint. |
| Data and privacy | yes | CSV holds names, addresses, order history; stored and emailed. |
| docs/standards/api.md | yes | Rules 1–4 apply to the new endpoint. |

## Decisions summary

- D1 Build exports in a cron job, not in the request: drivers RQ3, RQ4. The API stays responsive and the job follows the outbox pattern. Rejected: build the CSV in the request (a 500-order export with lines may take longer than the website's 10 s request timeout); a task queue such as Celery with Redis (a new service to run, against RQ4).
  - Assumes: one job run per minute keeps up with exports (a few a day).
- D2 Serve the file from the static website with an unguessable link, not through the API: drivers RQ3, RQ4. Netlify serves files fast and the API needs no download endpoint. Rejected: a download endpoint in the API (more code on the VPS); attaching the CSV to the email (MailRelay limits attachments to 5 MB).
  - Assumes: the link is only in the customer's email.

## Departures from existing patterns

- The job writes to the Netlify site; until now only the website's own build did.

## Unresolved questions

- None.
