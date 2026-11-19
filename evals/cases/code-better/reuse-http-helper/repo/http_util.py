import json
import urllib.request


def get_json(url, timeout=5):
    """All outbound HTTP goes through here: it sets our user agent and timeout."""
    request = urllib.request.Request(url, headers={"User-Agent": "dash/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)
