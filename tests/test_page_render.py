"""The shared `render` verb: every skill that registers a page has it, and the file it writes shows without a server."""

import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from better_ai import architect, cli, code, design, discover, page, research, show  # noqa: E402

SKILLS = (architect, code, design, discover, research, show)  # imported so each registers its page

OWN_RENDER = {"show-better"}  # its `render` checks a slide spec and also prints text
LIVE_ONLY = {"discover-better"}  # a static copy would keep words a redact removes, and its page reads only /data


class RenderEveryPage(unittest.TestCase):
    def test_every_registered_page_has_the_shared_render_verb_except_where_a_skill_has_its_own(self):
        self.assertTrue(page.PAGES)
        for name in page.PAGES:
            skill = next(s for s in SKILLS if s.SKILL.name == name).SKILL
            renders = [v for v in cli._verbs_of(skill) if v.name == "render"]
            if name in LIVE_ONLY:
                self.assertEqual(renders, [], name)
                continue
            self.assertEqual(len(renders), 1, name)
            self.assertEqual(renders[0].run is page.render, name not in OWN_RENDER, name)

    def test_the_file_of_every_page_stands_alone(self):
        for name, spec in page.PAGES.items():
            if name in OWN_RENDER | LIVE_ONLY:
                continue
            with self.subTest(skill=name):
                text = page.static_page(spec, {})
                self.assertIn('id="page-data"', text)
                self.assertIsNone(re.search(r'(src|href)="/', text))
                self.assertTrue(spec.rendered.endswith(".html"))


if __name__ == "__main__":
    unittest.main()
