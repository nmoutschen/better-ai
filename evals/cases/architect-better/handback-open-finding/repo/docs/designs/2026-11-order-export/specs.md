# Spec: order history export

Goal: a logged-in customer downloads a CSV of their own orders from their account page.
Design: [design.md](design.md)

| ID | Requirement | Source | Checked by |
|---|---|---|---|
| S1 | When a logged-in customer requests GET /v1/account/export/<token> for their own export less than 7 days old, the shop API shall return the CSV with status 200. | D2 | test: own export downloads |
| S2 | If the export belongs to another customer, or the request has no valid session cookie, then the shop API shall return 404 with the standard error body. | RQ2; docs/standards/api.md rule 3 | test: other customer's token gets 404 |
| S3 | When an export is older than 7 days, the build_exports job shall delete its file, and the API shall return 404 for it. | D2 | test: expired export |
| S4 | When a customer with up to 500 orders requests an export, the CSV shall be downloadable within 5 minutes. | RQ3 | scenario run with 500 seeded orders |
| S5 | When a customer sends more than 10 export requests in one minute, the shop API shall answer 429 and create no export for the extra requests. | RQ5; docs/standards/api.md rule 4 | test: 11th request in a minute |
| S6 | The CSV shall hold one row per order line with order id, date, title, ISBN, quantity, price, order total, status and shipping address, for the requesting customer's orders only. | RQ1 | test: CSV columns and rows |

## Gaps

- None.

## Design items with no requirement

- None.
