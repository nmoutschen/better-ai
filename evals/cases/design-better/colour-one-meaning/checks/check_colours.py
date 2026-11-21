"""Hidden check: the tables in architecture.html do not reuse the diagram legend's exact colours.

The legend gives green (#2e7d32, tint #e8f5e9, class `library`, variable --library) to parts provided by a library and
orange (#e65100, tint #fff3e0, class `ours`, variable --ours) to code we write. The check fails when a table's markup
uses one of these values, classes or variables, or when a CSS rule that styles a table, its cells or a class used in a
table does. It only finds exact reuse; another shade of green or orange is for the judge. With no table it passes.
"""

import html.parser
import pathlib
import re
import sys

LEGEND_VALUES = re.compile(r"2e7d32|e8f5e9|e65100|fff3e0|--library|--ours", re.IGNORECASE)
LEGEND_CLASSES = {"library", "ours", "swatch"}
TABLE_SELECTOR = re.compile(r"\b(table|thead|tbody|tfoot|tr|th|td|caption)\b", re.IGNORECASE)


class TableMarkup(html.parser.HTMLParser):
    """Collect the start tags inside tables, the classes they use, and the page's style blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.tags: list[str] = []
        self.classes: set[str] = set()
        self.in_style = False
        self.styles: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "style":
            self.in_style = True
            self.styles.append("")
        if tag == "table":
            self.depth += 1
        if self.depth:
            self.tags.append(self.get_starttag_text() or "")
            for name, value in attrs:
                if name == "class" and value:
                    self.classes.update(value.split())

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False
        if tag == "table" and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if self.in_style:
            self.styles[-1] += data


page = TableMarkup()
page.feed(pathlib.Path("architecture.html").read_text(encoding="utf-8"))
problems = [f"table markup: {tag}" for tag in page.tags if LEGEND_VALUES.search(tag)]
problems += [f"table uses the legend class {name}" for name in sorted(page.classes & LEGEND_CLASSES)]

css = "\n".join(page.styles)
for path in pathlib.Path(".").rglob("*.css"):
    if not {".git", ".design", ".code"} & set(path.parts):
        css += "\n" + path.read_text(encoding="utf-8", errors="replace")
css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
    classes = set(re.findall(r"\.([\w-]+)", selector))
    styles_table = TABLE_SELECTOR.search(selector) or classes & page.classes
    if styles_table and LEGEND_VALUES.search(body):
        problems.append(f"CSS rule {selector.strip()} uses a legend colour")

if problems:
    print("The table reuses the legend's colours:\n" + "\n".join(problems))
    sys.exit(1)
print("No table reuses the legend's exact colours.")
