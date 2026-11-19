# Design: retry

- The retry loop lives in `send()` in `client.py`. Callers keep calling `send(request, transport)`.
- `retry_after.wait_seconds(header, now)` turns a `Retry-After` value into seconds to wait, so the loop does not parse headers.
- `send()` takes the transport and a `sleep` function as arguments, so tests use a fake transport and never wait.
- `RetryError` is defined in `client.py` next to `send()`.
