scratch, retry work

2026-11-12
- first loop called time.sleep directly. test_client.py took 41 s for the 503 cases. moved to a `sleep` argument on send(), tests pass a fake that records the waits. works.
- tried urllib3 Retry instead of writing the loop. dropped it: new dependency (requirements say none), and it retries POST unless allowed_methods is set.

2026-11-13
- int(headers["Retry-After"]) raised ValueError on "Wed, 21 Oct 2026 07:28:00 GMT" — the staging server sends dates. email.utils.parsedate_to_datetime parses it. NOT wired in yet, wait_seconds() still only does integers.
- staging also sends Retry-After: 0 on some 503s. with 0 the loop retries 3 times instantly and gives up. no decision on this yet, haven't asked anyone.
- state: 429/503 retry with integer Retry-After works + tested. not done: HTTP-date form, POST must not retry (right now POST retries too), RetryError after 3 retries (loop currently just returns the last response).
