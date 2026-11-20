"""refund-guide.md exists and keeps the rules that decide whether a refund is allowed."""
import re

text = open("refund-guide.md").read()
patterns = (
    r"\b30[ -]days?|thirty days",
    r"unused|not (been )?used|never used|hasn.t (been )?used",
    r"faulty|defective|damaged",
    r"\b12[ -]months?|twelve months|one year|\b1 year|a year",
    r"gift[ -]?cards?",
    r"personali[sz]ed|engraved|custom",
)
missing = [p for p in patterns if not re.search(p, text, re.I)]
assert not missing, missing
