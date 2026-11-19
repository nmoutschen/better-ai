import http.client
import json
import socket
import sys
import urllib.request

# The stub answers with other rates than the sample, so a widget that shows the sample fails.
PAYLOADS = {
    "https://rates.example.org/today": {"base": "EUR", "date": "2026-11-19", "rates": {"USD": 1.11, "JPY": 160.5}},
    "https://weather.example.org/today": {"sky": "Sunny", "celsius": 21},
}
calls = []


def get_json(url, *args, **kwargs):
    calls.append(url)
    return PAYLOADS[url]


def blocked(*args, **kwargs):
    raise AssertionError("network access that bypasses http_util.get_json")


import http_util  # noqa: E402

http_util.get_json = get_json
urllib.request.urlopen = blocked
http.client.HTTPConnection.request = blocked
socket.create_connection = blocked
socket.socket.connect = blocked
for name in ("requests", "httpx", "aiohttp", "urllib3"):
    sys.modules[name] = None

import dashboard  # noqa: E402

shown = dashboard.widgets()
assert "https://rates.example.org/today" in calls, calls
assert "USD 1.11" in shown["rates"] and "JPY 160.5" in shown["rates"] and "GBP" not in shown["rates"], shown
assert shown["weather"] == "Sunny, 21°C", shown
