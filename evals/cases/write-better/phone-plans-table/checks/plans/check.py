"""plans.md has a Markdown table and keeps every price, data allowance, contract length and roaming figure."""
import re

text = open("plans.md").read()
lines = text.splitlines()
separator = r"\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*"
starts = [number for number, line in enumerate(lines) if re.fullmatch(separator, line)]
assert any(sum(1 for line in lines[start + 1:start + 4] if "|" in line) >= 3 for start in starts), "no table with 3 rows"
for pattern in ('(?<![\\d.])14(?![\\d.])', '(?<![\\d.])15(?![\\d.])', 'rolling|one[- ]month|1[- ]month|monthly contract|month[- ]to[- ]month|no (fixed|minimum) (term|contract)', '£\\s?2(\\.00)?(?![\\d.])|(?<![\\d.])2\\s*(GBP|pounds?)\\b|(?<![\\d.])2\\s*(/|per|a)\\s*day', 'megabyte|\\bMB\\b', '(?<![\\d.])19(?![\\d.])', '(?<![\\d.])40(?![\\d.])', '(?<![\\d.])12(?![\\d.])', '(?<![\\d.])20(?![\\d.])', 'five or more|5 or more|5\\+|at least (5|five)|(five|5) lines or more', '10\\s*%', '17[.,]10', '(?<![\\d.])27(?![\\d.])', 'unlimited', '(?<![\\d.])650(?![\\d.])', '(?<![\\d.])24(?![\\d.])', '(?<![\\d.])70(?![\\d.])', '(?<![\\d.])25(?![\\d.])', '(?<![\\d.])6(?![\\d.])', '(?<![\\d.])22(?![\\d.])', '(?<![\\d.])11(?![\\d.])', 'nine|(?<![\\d.])9(?![\\d.])'):
    assert re.search(pattern, text, re.I), pattern
