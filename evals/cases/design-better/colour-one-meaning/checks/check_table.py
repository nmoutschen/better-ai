"""Hidden check: architecture.html has a table that lists every check in checks.json, however it is styled."""

import html.parser
import json
import pathlib
import sys


class Tables(html.parser.HTMLParser):
    """Collect the text of each table in the page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.texts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            if self.depth == 0:
                self.texts.append("")
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == "table" and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if self.depth:
            self.texts[-1] += " " + data


def normal(text: str) -> str:
    """Lower-case the text and collapse its white space."""
    return " ".join(text.lower().split())


names = [check["name"] for check in json.loads(pathlib.Path("checks.json").read_text(encoding="utf-8"))]
parser = Tables()
parser.feed(pathlib.Path("architecture.html").read_text(encoding="utf-8"))
for text in parser.texts:
    missing = [name for name in names if normal(name) not in normal(text)]
    if not missing:
        print("A table in architecture.html lists every check.")
        sys.exit(0)
print(f"No table in architecture.html lists every check ({len(parser.texts)} tables found).")
sys.exit(1)
