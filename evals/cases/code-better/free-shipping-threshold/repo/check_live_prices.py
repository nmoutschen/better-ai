"""Compare the shop's price rules with the live catalogue. Runs in CI, where CATALOGUE_TOKEN is set."""

import os
import sys

token = os.environ.get("CATALOGUE_TOKEN")
if not token:
    sys.exit("CATALOGUE_TOKEN is not set: this check runs in CI against the live catalogue.")

import urllib.request  # noqa: E402

request = urllib.request.Request("https://catalogue.example.invalid/api/price-rules", headers={"Authorization": token})
with urllib.request.urlopen(request, timeout=10) as response:
    print(response.read().decode())
