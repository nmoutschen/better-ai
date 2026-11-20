"""Every form control in signup.html has a label: a <label for=id> or a <label> that wraps it."""

import sys
from html.parser import HTMLParser

SKIPPED_TYPES = {"hidden", "submit", "button", "reset", "image"}


class Controls(HTMLParser):
    """Collect form controls, whether each sits inside a label, and the ids that labels point to."""

    def __init__(self):
        super().__init__()
        self.controls = []
        self.label_for = set()
        self.label_depth = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "label":
            self.label_depth += 1
            if attributes.get("for"):
                self.label_for.add(attributes["for"])
        elif tag in ("input", "select", "textarea"):
            if tag == "input" and (attributes.get("type") or "text").lower() in SKIPPED_TYPES:
                return
            self.controls.append((attributes.get("id") or attributes.get("name") or tag, attributes.get("id"), self.label_depth > 0))

    def handle_endtag(self, tag):
        if tag == "label" and self.label_depth:
            self.label_depth -= 1


parser = Controls()
with open("signup.html", encoding="utf-8") as handle:
    parser.feed(handle.read())

if len(parser.controls) < 5:
    sys.exit(f"expected the signup form's controls, found {len(parser.controls)}")
missing = [name for name, element_id, wrapped in parser.controls if not wrapped and element_id not in parser.label_for]
if missing:
    sys.exit(f"controls without a label: {', '.join(missing)}")
print(f"all {len(parser.controls)} controls have a label")
