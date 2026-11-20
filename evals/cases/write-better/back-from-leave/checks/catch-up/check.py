"""catch-up.md opens with the last move and the next step, and keeps the restore test and shutdown dates."""
import re

text = open("catch-up.md").read()
body = " ".join(line for line in text.splitlines() if not re.match(r"\s*#", line))
opening = " ".join(body.split()[:80])
last = (r"billing|all (11|eleven)|(11|eleven) services|last (service|move)|every service|no traffic"
        r"|all (of )?(the |our )?services|complete|finished")
next_step = r"shut(ting)?[\s-]*(it\s+|k8s-old\s+|the old cluster\s+)?(down|off)|decommission|turn(ing)? off|switch(ing)? off|retir|delet|offline"
assert re.search(last, opening, re.I), "last thing done not in the opening"
assert re.search(next_step, opening, re.I), "next step not in the opening"
for pattern in (r"restore", r"2026-11-23|\b23(rd)?\s*(of\s+)?Nov|Nov[a-z]*\.?\s*23\b|Monday",
                r"2026-11-24|\b24(th)?\s*(of\s+)?Nov|Nov[a-z]*\.?\s*24\b|Tuesday"):
    assert re.search(pattern, text, re.I), pattern
