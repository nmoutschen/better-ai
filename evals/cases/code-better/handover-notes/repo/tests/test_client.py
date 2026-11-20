import unittest
from types import SimpleNamespace

from client import send


def responses(*statuses, headers=None):
    queue = [SimpleNamespace(status=status, headers=headers or {}) for status in statuses]
    return lambda request: queue.pop(0)


class SendTest(unittest.TestCase):
    def test_retries_503_with_retry_after(self):
        waits = []
        response = send(
            SimpleNamespace(method="GET"), responses(503, 200, headers={"Retry-After": "5"}), sleep=waits.append
        )
        self.assertEqual(response.status, 200)
        self.assertEqual(waits, [5])

    def test_backoff_without_header(self):
        waits = []
        response = send(SimpleNamespace(method="GET"), responses(429, 429, 200), sleep=waits.append)
        self.assertEqual(response.status, 200)
        self.assertEqual(waits, [1, 2])


if __name__ == "__main__":
    unittest.main()
