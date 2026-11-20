# Retry for the HTTP client

- When the server answers 429 or 503, `send()` retries the request.
- Wait for the time the `Retry-After` header gives, either in seconds or as an HTTP date. Without the header, wait 1, 2, then 4 seconds.
- Retry at most 3 times, then raise `RetryError` with the last status.
- Never retry POST requests: a repeated POST can charge a customer twice.
- Add no dependency: the client is copied into projects that pin their packages.
