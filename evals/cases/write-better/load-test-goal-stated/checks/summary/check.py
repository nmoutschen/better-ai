"""loadtest-summary.md exists and reports the stage-4 p95 latency and error rate."""
import re

text = open("loadtest-summary.md").read()
for pattern in (r"1[ ,.]?480\b|1[.,]48?\s*(s|sec)|1[.,]5\s*(s|sec)", r"6[.,]8\s*%|6[.,]8\b|\b7\s*%"):
    assert re.search(pattern, text, re.I), pattern
