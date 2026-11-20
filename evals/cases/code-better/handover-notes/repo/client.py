import time

from retry_after import wait_seconds

RETRY_STATUSES = {429, 503}
BACKOFF = [1, 2, 4]


class RetryError(Exception):
    def __init__(self, status):
        super().__init__(f"gave up after retries, last status {status}")
        self.status = status


def send(request, transport, sleep=time.sleep, now=time.time):
    response = transport(request)
    for attempt in range(3):
        if response.status not in RETRY_STATUSES:
            return response
        header = response.headers.get("Retry-After")
        sleep(wait_seconds(header, now()) if header is not None else BACKOFF[attempt])
        response = transport(request)
    return response
