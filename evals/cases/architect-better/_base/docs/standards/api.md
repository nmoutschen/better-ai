# API standard

Every endpoint of the shop API follows these rules.

1. Paths start with a version: `/v1/...`. A breaking change gets a new version; the old one keeps working for 6 months.
2. Errors are JSON: `{"error": {"code": "<snake_case>", "message": "<text a customer can read>"}}`, with a fitting
   HTTP status.
3. An endpoint that returns a customer's data requires their session cookie and returns only their own data
   (404, not 403, for someone else's).
4. Endpoints that send email or cost money are limited to 10 requests per customer per minute (429 beyond).
