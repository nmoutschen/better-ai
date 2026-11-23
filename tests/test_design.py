"""DESIGN.md and the pages agree: every colour a page uses is in DESIGN.md's colour table, the boards write spaces and
type sizes with the tokens only, and DESIGN.md's tables of colours, type and spacing hold the values page.css defines.

Run with `python3 -m unittest discover tests`.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE_CSS = ROOT / "src" / "better_ai" / "page" / "page.css"
PAGES = [
    p
    for pattern in (
        "skills/*/scripts/*.css",
        "skills/*/scripts/*.html",
        "skills/*/scripts/*.js",
        "src/better_ai/*/*.css",
        "src/better_ai/*/*.html",
        "src/better_ai/*/*.js",
    )
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


def design_tokens(heading: str) -> dict:
    """A token table under a DESIGN.md heading: {name: value} from rows that start with a `--token` and its value."""
    text = (ROOT / "DESIGN.md").read_text(encoding="utf-8")
    section = text.split(f"## {heading}", 1)[1].split("\n## ", 1)[0]
    return dict(re.findall(r"^\| `(--[a-z0-9-]+)` \| `?([^`|]+?)`? \|", section, re.M))


# Every src/better_ai/*/*.css is held to the tokens, except these parts, which keep their own sizes.
def _numbered(css, start=1):
    return enumerate(css.splitlines(), start)


def _without_map(css):
    """A drawing, the research map, keeps its own sizes."""
    return ((n, line) for n, line in _numbered(css) if ".map" not in line)


def _after_tokens(css):
    """page.css after its :root block, where the tokens themselves are defined with raw values."""
    return _numbered(css, css[: css.index("\n}\n")].count("\n") + 2)


def _before_slides(css):
    """show.css up to its slides, which keep their own sizes."""
    for n, line in _numbered(css):
        if line.startswith("/* ---------- A slide"):
            return
        yield n, line


EXCEPTIONS = {
    "page/page.css": _after_tokens,
    "research/board.css": _without_map,
    "code/dashboard.css": _without_map,
    "show/show.css": _before_slides,
}


def board_css():
    """The lines of every skill CSS file that must write spaces and type sizes with tokens, as (file, line number, line)."""
    for path in sorted((ROOT / "src" / "better_ai").glob("*/*.css")):
        css = path.read_text(encoding="utf-8")
        name = path.relative_to(ROOT / "src" / "better_ai").as_posix()
        for n, line in EXCEPTIONS.get(name, _numbered)(css):
            yield path, n, line


# A px value in a padding, margin or gap, or as the size in a font or font-size; 0 and 1px (a hairline) are allowed.
RAW_SPACE = re.compile(
    r"(?<![\w-])(?:padding|margin|(?:row-|column-)?gap)(?:-[a-z]+)*\s*:[^;}]*?(?<![\d.])(?!1px)\d+(?:\.\d+)?px"
)
RAW_TEXT = re.compile(r"(?<![\w-])(?:font\s*:\s*(?:[a-z0-9]+\s+)*?|font-size\s*:\s*)\d+(?:\.\d+)?px")
# A font shorthand must be a type style token, or inherit.
RAW_FONT = re.compile(r"(?<![\w-])font\s*:\s*(?!var\(--font-|inherit)")


def page_css_tokens() -> dict:
    root = PAGE_CSS.read_text(encoding="utf-8").split(":root {", 1)[1].split("\n}", 1)[0]
    root = re.sub(r"/\*.*?\*/", "", root, flags=re.S)
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"(--[a-z0-9-]+):([^;]+);", root)}


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

    def test_the_type_and_spacing_tables_match_page_css(self):
        css = page_css_tokens()
        for heading, prefix in (("Type", "--text-"), ("Type", "--font-"), ("Spacing and layout", "--space-")):
            table = {name: value for name, value in design_tokens(heading).items() if name.startswith(prefix)}
            in_css = {name: value for name, value in css.items() if name.startswith(prefix)}
            self.assertTrue(table, f"no token table under {heading} in DESIGN.md")
            self.assertEqual(table, in_css, f"DESIGN.md's {heading} table and page.css disagree")

    def test_boards_write_spaces_and_type_sizes_with_tokens(self):
        raw = [
            f"{path.relative_to(ROOT)}:{n}: {line.strip()[:90]}"
            for path, n, line in board_css()
            if RAW_SPACE.search(line) or RAW_TEXT.search(line) or RAW_FONT.search(line)
        ]
        self.assertEqual(raw, [], "values where DESIGN.md asks for --space-*, --text-* or --font-* tokens")
        # register.css has no page.css: its own :root holds copies of the tokens it uses, and they must match
        register = (ROOT / "src" / "better_ai" / "architect" / "register.css").read_text(encoding="utf-8")
        copies = dict(re.findall(r"(--[a-z-]+):\s*([^;]+);", register.split("}", 1)[0]))
        self.assertEqual(copies, {name: page_css_tokens()[name] for name in copies})

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
            current = (ROOT / "src" / "better_ai" / "page" / name).read_text(encoding="utf-8")
            self.assertEqual(match.group(1), current, f"DESIGN.html's copy of {name} is out of date: paste it again")

    def test_design_html_lists_the_same_colours(self):
        html = (ROOT / "DESIGN.html").read_text(encoding="utf-8")
        listed = re.findall(r'^  \["([a-z-]+)", "', html.split("const COLOURS = [", 1)[1].split("];", 1)[0], re.M)
        colours = [name[2:] for name, value in design_table().items() if COLOUR.fullmatch(value)]
        self.assertEqual(listed, colours)


if __name__ == "__main__":
    unittest.main()
