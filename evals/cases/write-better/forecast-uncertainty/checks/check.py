"""forecast.md exists, gives the base case and range and mentions Q3."""
import re

text = open("forecast.md").read()
patterns = (
    r"1[.,]42\s*(M|m|million)|1[ ,.]?420[ ,.]?000|1[ ,.]?420\s*k",
    r"1[.,]25\s*(M|m|million)?|1[ ,.]?250[ ,.]?000|1[ ,.]?250\s*k",
    r"1[.,]55\s*(M|m|million)?|1[ ,.]?550[ ,.]?000|1[ ,.]?550\s*k",
    r"\bQ3\b|third quarter",
)
missing = [p for p in patterns if not re.search(p, text, re.I)]
assert not missing, missing
