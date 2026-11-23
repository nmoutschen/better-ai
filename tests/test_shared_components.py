"""The shared page.css holds the chip, table, decision panel, section intro, inline record form and wrapping tabs,
each documented in DESIGN.md, and the boards use them instead of their own copies.

Run with `python3 tests/run.py test_shared_components`.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "better_ai"
PAGE_CSS = (SRC / "page" / "page.css").read_text(encoding="utf-8")
DESIGN = (ROOT / "DESIGN.md").read_text(encoding="utf-8")


def hex6(value: str) -> str:
    """#abc or #aabbcc as upper-case #RRGGBB."""
    v = value.lstrip("#").upper()
    return "#" + ("".join(c * 2 for c in v) if len(v) == 3 else v[:6])


def design_table() -> dict:
    """DESIGN.md's colour table: {name: value}."""
    section = DESIGN.split("## Colour", 1)[1].split("\n## ", 1)[0]
    return dict(re.findall(r"^\| `(--[a-z-]+)` \| `([^`]+)` \|", section, re.M))


def rule(css: str, selector: str) -> str:
    """The declarations of the rule whose selector list is exactly `selector`, or '' when there is none."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for match in re.finditer(r"(?m)^([^{}@\n][^{}]*?)\s*\{([^}]*)\}", css):
        if selector in [s.strip() for s in match.group(1).split(",")]:
            return match.group(2)
    return ""


def section(heading: str) -> str:
    """The text of a DESIGN.md `###` section."""
    return DESIGN.split(f"### {heading}\n", 1)[1].split("\n#", 1)[0]


class SharedComponents(unittest.TestCase):
    def test_page_css_defines_each_shared_component(self):
        for selector in (
            ".chip",
            "table.tbl",
            "table.tbl th",
            "table.tbl td",
            ".decide",
            ".intro",
            ".rec",
            ".tabs--wrap",
        ):
            self.assertTrue(rule(PAGE_CSS, selector), f"page.css has no {selector} rule")

    def test_chip_colours_follow_the_colour_meanings(self):
        for kind, border, colour in (
            ("ok", "--moss-dark", "--moss-dark"),
            ("error", "--error", "--error"),
            ("working", "--terracotta", "--terracotta-dark"),
            ("wait", "--umber", "--umber"),
        ):
            body = rule(PAGE_CSS, f".chip.{kind}")
            self.assertIn(f"border-color:var({border})", body.replace(" ", ""), f".chip.{kind} border")
            self.assertIn(f"color:var({colour})", body.replace(" ", ""), f".chip.{kind} text")
        self.assertIn("var(--sand)", rule(PAGE_CSS, ".chip"), "a plain chip has a sand border")

    def test_the_chip_uses_the_label_style_and_the_working_chip_pulses(self):
        body = rule(PAGE_CSS, ".chip").replace(" ", "")
        self.assertIn("font:var(--font-label)", body)
        self.assertIn("text-transform:uppercase", body)
        self.assertIn("pulse-bar", rule(PAGE_CSS, ".chip.working::before"))

    def test_no_chip_at_weight_600(self):
        self.assertNotIn(".chip.req", PAGE_CSS)
        self.assertNotIn("font-weight:600", rule(PAGE_CSS, ".chip"))

    def test_the_boards_do_not_keep_their_own_copies(self):
        for name in ("architect/page.css", "research/board.css"):
            css = (SRC / name).read_text(encoding="utf-8")
            for line in css.splitlines():
                self.assertNotRegex(line, r"^\.(chip|decide)\b", f"{name} still styles {line[:30]}")
                self.assertNotRegex(line, r"^\.tbl( th| td)?\s*\{", f"{name} still styles {line[:30]}")

    def test_the_old_chip_classes_are_gone(self):
        for path in sorted(SRC.glob("*/*")):
            if path.suffix not in (".css", ".js", ".html"):
                continue
            text = path.read_text(encoding="utf-8")
            old = re.findall(r"chip[ .](?:open|guess|bad|now|todo|req)\b|chip\([^)]*'(?:open|guess)'\)", text)
            self.assertEqual(old, [], f"{path.relative_to(ROOT)} uses an old chip class")

    def test_research_state_names_map_to_the_shared_chip(self):
        script = (SRC / "research" / "board.js").read_text(encoding="utf-8")
        states = dict(
            re.findall(r'"([a-z ]+)": \["[a-z ]+", "([a-z]+)"\]', script.split("const STATE", 1)[1].split("};", 1)[0])
        )
        self.assertEqual(
            states,
            {
                "answered": "ok",
                "in progress": "working",
                "open": "plain",
                "proposed": "plain",
                "contested": "error",
                "not found": "error",
                "unclear": "error",
            },
        )
        self.assertNotRegex(script, r'class="chip (now|todo|bad)')
        self.assertNotIn("chip wait", script)  # work in progress is working; wait is for what waits for the user
        fill = script.split("const FILL", 1)[1].split("};", 1)[0]
        for kind in ("ok", "working", "plain", "error"):
            self.assertIn(kind + ":", fill)

    def test_architect_chips_follow_what_the_state_means(self):
        script = (SRC / "architect" / "page.js").read_text(encoding="utf-8")
        self.assertIn("chip('guessed', 'plain')", script)
        self.assertIn("chip('Unconfirmed', 'plain')", script)
        self.assertIn("chip('Not valid', 'error')", script)
        self.assertIn("chip('no valid source', 'error')", script)
        self.assertIn("chip('New')", script)
        self.assertIn("' comments'))", script)
        self.assertNotRegex(script, r"chip\([^)]*'(open|guess)'\)")

    def test_the_table_rule_is_only_for_a_table_element(self):
        """code-better's dashboard has a <section class="tbl">: the shared rule must not reach it."""
        css = re.sub(r"/\*.*?\*/", "", PAGE_CSS, flags=re.S)
        selectors = [s.strip() for m in re.finditer(r"(?m)^([^{}@\n][^{}]*?)\s*\{", css) for s in m.group(1).split(",")]
        bare = [s for s in selectors if re.search(r"(?<!table)\.tbl\b", s)]
        self.assertEqual(bare, [], "page.css styles .tbl on any element")

    def test_a_blocked_chip_gets_its_circle_slash_from_one_rule(self):
        body = rule(PAGE_CSS, ".chip.error::before")
        self.assertIn("2298", body)
        for path in sorted(SRC.glob("*/*")):
            if path.suffix in (".js", ".html"):
                self.assertNotIn(
                    "\u2298", path.read_text(encoding="utf-8"), f"{path.relative_to(ROOT)} types the mark itself"
                )
        self.assertIn("page.css puts", section("Chip"))

    def test_every_state_colour_follows_the_colour_meanings(self):
        """By value: moss-dark done, terracotta working, umber waiting for the user, error blocked."""
        table = {name: hex6(value) for name, value in design_table().items() if value.startswith("#")}
        done, working, wait, blocked = (table[n] for n in ("--moss-dark", "--terracotta", "--umber", "--error"))
        # the chip: its border carries the meaning
        for kind, expected in (("ok", done), ("working", working), ("wait", wait), ("error", blocked)):
            border = re.search(r"border-color:var\((--[a-z-]+)\)", rule(PAGE_CSS, f".chip.{kind}")).group(1)
            self.assertEqual(table[border], expected, f".chip.{kind}")
        # the research board's dots, rings and legend
        script = (SRC / "research" / "board.js").read_text(encoding="utf-8")
        fill = {
            k: hex6(v)
            for k, v in re.findall(r'(\w+): "(#[0-9A-Fa-f]{6})"', script.split("const FILL", 1)[1].split("};", 1)[0])
        }
        self.assertEqual(fill["working"], working)
        self.assertEqual(fill["error"], blocked)
        ring = re.search(r'const ring = q\.view === "in progress" \?.*?stroke="(#[0-9A-Fa-f]{6})"', script).group(1)
        self.assertEqual(hex6(ring), working, "the in-progress ring")
        for view in ("not found", "unclear"):
            line = re.search(rf'q\.view === "{view}" \? hollow\("(#[0-9A-Fa-f]{{6}})"', script).group(1)
            self.assertEqual(hex6(line), blocked, view)
        legend = (SRC / "research" / "board.html").read_text(encoding="utf-8")
        for label, expected in (
            ("contested", blocked),
            ("not found", blocked),
            ("unclear", blocked),
            ("agent on it", working),
        ):
            item = re.search(r"<li>((?:(?!</li>).)*?)" + label + r"</li>", legend, re.S).group(1)
            colours = {hex6(c) for c in re.findall(r'(?:fill|stroke)="(#[0-9A-Fa-f]{6})"', item)} - {hex6("#33302B")}
            self.assertEqual(colours, {expected}, f"legend: {label}")

    def test_design_md_documents_each_component(self):
        for heading in ("Chip", "Table", "Decision panel", "Section intro", "Inline record form"):
            text = section(heading)
            self.assertIn("Use for:", text, heading)
            self.assertIn("Name and role:", text, heading)
        for word in ("`.chip`", "`.ok`", "`.error`", "`.working`", "`.wait`", "`.plain`"):
            self.assertIn(word, section("Chip"))
        self.assertIn("`table.tbl`", section("Table"))
        self.assertIn("`.decide`", section("Decision panel"))
        self.assertIn("`.intro`", section("Section intro"))
        self.assertIn("`.rec`", section("Inline record form"))
        self.assertIn("`.tabs--wrap`", section("Tabs and segmented controls"))

    def test_where_it_lives_points_at_the_page_folder(self):
        text = DESIGN.split("## Where it lives", 1)[1].split("\n## ", 1)[0]
        self.assertIn("src/better_ai/page/page.css", text)
        self.assertNotIn("skills/*/scripts/page.css", text)


if __name__ == "__main__":
    unittest.main()
