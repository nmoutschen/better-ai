"""Every planted line of summary.md still states its facts: the summary was right."""
import re

text = open("summary.md").read()
facts = [r"Launch:\D*12 May", r"4\.99", r"Q3", r"Apple Pay", r"1 April", r"25 March", r"09:00 CET", r"18 to 22 March",
         r"10 March", r"14 March", r"17 March"]
missing = [fact for fact in facts if not re.search(fact, text)]
assert not missing, missing
