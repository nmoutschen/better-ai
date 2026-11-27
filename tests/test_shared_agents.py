"""The list of agents at work is in the shared page, and no board keeps its own copy of it, its markup or its CSS.

Run with `python3 tests/run.py test_shared_agents`.
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from better_ai import page  # noqa: E402
from better_ai.architect import pagespec as architect_page  # noqa: E402
from better_ai.research import board  # noqa: E402

SRC = ROOT / "src" / "better_ai"
PAGE_CSS = (SRC / "page" / "page.css").read_text(encoding="utf-8")
DESIGN = (ROOT / "DESIGN.md").read_text(encoding="utf-8")


def rule(css: str, selector: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for match in re.finditer(r"(?m)^([^{}@\n][^{}]*?)\s*\{([^}]*)\}", css):
        if selector in [s.strip() for s in match.group(1).split(",")]:
            return match.group(2)
    return ""


class SharedAgents(unittest.TestCase):
    def test_page_js_holds_the_renderer_and_it_reads_no_log(self):
        script = (SRC / "page" / "page.js").read_text(encoding="utf-8")
        body = script.split("function pageAgents", 1)[1].split("\nfunction ", 1)[0]
        for name in ("fetch", "XMLHttpRequest", "searches", "logs"):
            self.assertNotIn(name, body)

    def test_page_css_styles_the_section_and_the_list(self):
        for selector in (".agentsec", ".agents", ".agents button", ".agents .dry"):
            self.assertTrue(rule(PAGE_CSS, selector), f"page.css has no {selector} rule")

    def test_the_working_chip_marks_work_in_progress_and_the_list_adds_no_colour_of_its_own(self):
        self.assertIn("chip working", (SRC / "page" / "page.js").read_text(encoding="utf-8"))
        self.assertNotIn("#", re.sub(r"/\*.*?\*/", "", rule(PAGE_CSS, ".agents")))

    def test_the_research_package_keeps_no_copy(self):
        self.assertFalse((SRC / "research" / "agents.html").exists())
        css = (SRC / "research" / "board.css").read_text(encoding="utf-8")
        self.assertNotRegex(css, r"\.agentsec|\.agents\b")
        self.assertNotIn("research/agents.html", (SRC / "research" / "board.py").read_text(encoding="utf-8"))

    def test_the_research_board_still_has_the_section_in_its_side_column(self):
        text = page.shell(board.SPEC)
        aside = text[text.index('<aside class="notes"') : text.index("</aside>")]
        self.assertIn('id="agents"', aside)
        self.assertLess(aside.index('id="agents"'), aside.index('id="notes-h"'))

    def test_the_architect_page_has_the_section_in_its_side_column(self):
        text = page.shell(architect_page.SPEC)
        aside = text[text.index('<aside class="notes"') : text.index("</aside>")]
        self.assertIn('id="agents"', aside)
        script = (SRC / "architect" / "page.js").read_text(encoding="utf-8")
        self.assertIn("pageAgents(", script)
        self.assertNotRegex((SRC / "architect" / "page.css").read_text(encoding="utf-8"), r"\.agentsec|\.agents\b")

    def test_design_md_documents_the_list_as_a_component(self):
        text = DESIGN.split("### Agents at work\n", 1)[1].split("\n#", 1)[0]
        for part in ("Use for:", "Markup:", "Name and role:", "No word from", "second try"):
            self.assertIn(part, text)


if __name__ == "__main__":
    unittest.main()
