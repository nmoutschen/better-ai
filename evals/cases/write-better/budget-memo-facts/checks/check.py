"""budget-memo.md was rewritten and still holds every number, date, name, condition, limit and the recommendation."""
import re

text = open("budget-memo.md").read()
FACTS = (
    r"4[.,]82",
    r"3[.,]5\s*(%|per\s*cent)",
    r"4[.,]66",
    r"(?<![\d.,])6\s*(%|per\s*cent)",
    r"(?<![\d.,])10\s*(%|per\s*cent)",
    r"90\s*(%|per\s*cent)",
    r"1[,. ]?200",
    r"85[,. ]?000|85\s*k\b",
    r"310[,. ]?000|310\s*k\b",
    r"(?<![\d.,])60[,. ]?000|(?<![\d.,])60\s*k\b",
    r"contractor",
    r"freeze",
    r"March",
    r"Kumasi",
    r"30\s*April|April\s*30|30/04",
    r"15\s*January|January\s*15|15\s*Jan\b|Jan\s*15|2027-01-15|15/01",
    r"12\s*June|June\s*12|12\s*Jun\b|12/06",
    r"week",
    r"managing director|\bMD\b",
    r"default",
    r"reserve",
    r"\bQ3\b|third quarter",
    r"equipment",
    r"Adwoa",
)
missing = [p for p in FACTS if not re.search(p, text, re.I)]
assert not missing, f"missing facts: {missing}"
assert text.strip() != open(__file__.replace("check.py", "planted.md")).read().strip(), "unchanged"
