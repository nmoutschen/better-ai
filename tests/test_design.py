"""DESIGN.md and the pages agree: every colour a page uses is in DESIGN.md's colour table, and the table's values are
the ones page.css defines.

Run with `python3 -m unittest discover tests`.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE_CSS = ROOT / "skills" / "research-better" / "scripts" / "page.css"
PAGES = [
    p
    for pattern in ("skills/*/scripts/*.css", "skills/*/scripts/*.html", "skills/*/scripts/*.js")
    for p in sorted(ROOT.glob(pattern))
]


def hex6(value: str) -> str:
    """#abc, #aabbcc or rgb(a)(r,g,b,…) as upper-case #RRGGBB, without alpha."""
    if value.startswith("rgb"):
        r, g, b = (int(x) for x in re.findall(r"\d+", value)[:3])
        return f"#{r:02X}{g:02X}{b:02X}"
    v = value.lstrip("#").upper()
    if len(v) in (3, 4):
        v = "".join(c * 2 for c in v[:3])
    return "#" + v[:6]


def design_table() -> dict:
    """The colour table in DESIGN.md: {name: value}."""
    text = (ROOT / "DESIGN.md").read_text(encoding="utf-8")
    section = text.split("## Colour", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\| `(--[a-z-]+)` \| `([^`]+)` \|", section, re.M)
    return dict(rows)


def page_css_tokens() -> dict:
    root = PAGE_CSS.read_text(encoding="utf-8").split(":root {", 1)[1].split("\n}", 1)[0]
    root = re.sub(r"/\*.*?\*/", "", root, flags=re.S)
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"(--[a-z-]+):([^;]+);", root)}


COLOUR = re.compile(r"#[0-9A-Fa-f]{3,8}\b|rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+[^)]*\)")
# Colours a page could write without a hex value: by name, or with a function the table does not use.
OTHER = re.compile(
    r"\b(?:hsla?|hwb|lab|lch|oklab|oklch|color-mix)\(|"
    r"(?:color|background(?:-color)?|border(?:-[a-z]+)*|outline(?:-color)?|fill|stroke)\s*[:=]\s*[\"']?"
    r"(?:white|black|red|green|blue|gr[ae]y|silver|orange|yellow|purple|pink|brown|navy|beige|ivory)\b"
)


class Design(unittest.TestCase):
    def test_the_colour_table_matches_page_css(self):
        table, css = design_table(), page_css_tokens()
        self.assertTrue(table, "no colour table found in DESIGN.md")
        for name, value in table.items():
            self.assertIn(name, css, f"{name} is in DESIGN.md but not in page.css")
            self.assertEqual(value.replace(" ", ""), css[name].replace(" ", ""), name)

    def test_pages_use_only_named_colours(self):
        allowed = {hex6(c) for v in design_table().values() for c in COLOUR.findall(v)}
        stray = []
        for path in PAGES:
            text = re.sub(r"--saya:url\([^)]*\)", "", path.read_text(encoding="utf-8"))  # the pattern's own fill
            for n, line in enumerate(text.splitlines(), 1):
                for c in COLOUR.findall(line):
                    if hex6(c) not in allowed:
                        stray.append(f"{path.relative_to(ROOT)}:{n}: {c}")
                for m in OTHER.finditer(line):
                    stray.append(f"{path.relative_to(ROOT)}:{n}: {m.group(0)}")
        self.assertEqual(stray, [], "colours not named in DESIGN.md")

    def test_design_html_carries_the_current_page_css_and_page_js(self):
        """DESIGN.html works as a single file, so it holds copies of page.css and page.js: they must be the current ones."""
        html = (ROOT / "DESIGN.html").read_text(encoding="utf-8")
        for name, tag in (("page.css", "style"), ("page.js", "script")):
            match = re.search(rf'<{tag} id="{name.replace(".", "-")}">\n(.*?)</{tag}>', html, re.S)
            self.assertIsNotNone(match, f"DESIGN.html has no <{tag} id=...> with {name}")
            current = (ROOT / "skills" / "research-better" / "scripts" / name).read_text(encoding="utf-8")
            self.assertEqual(match.group(1), current, f"DESIGN.html's copy of {name} is out of date: paste it again")

    def test_design_html_lists_the_same_colours(self):
        html = (ROOT / "DESIGN.html").read_text(encoding="utf-8")
        listed = re.findall(r'^  \["([a-z-]+)", "', html.split("const COLOURS = [", 1)[1].split("];", 1)[0], re.M)
        colours = [name[2:] for name, value in design_table().items() if COLOUR.fullmatch(value)]
        self.assertEqual(listed, colours)


if __name__ == "__main__":
    unittest.main()
