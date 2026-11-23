"""Every record type a skill's command writes has an example line in the skill's own text.

A record type is a type of a unit kind's `add` or `create` (`records.layout`), so the types of `conversation.jsonl` are not
included: the page writes those. The example is a line or block holding `"type": "<type>"` in a file under the skill's
`formats/`. design-better has no `formats/`: its only record is the `canvas` head, which its SKILL.md must show with each of
its fields.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))

from better_ai import architect, code, design, paths, records, research, schema, show  # noqa: E402

SKILLS = {
    "architect-better": architect.SKILL,
    "code-better": code.SKILL,
    "design-better": design.SKILL,
    "research-better": research.SKILL,
    "show-better": show.SKILL,
}


# The shared decisions schema is bundled into every skill with a page, so `add` accepts a `decision` in a show-better and a
# design-better unit too; neither skill asks the user anything through one, so neither shows an example. Reported to the
# coordinator as a finding: either the two skills stop bundling it or they gain a format file.
UNUSED = {("show-better", "decision"), ("design-better", "decision")}


def written_types(skill) -> dict[str, set[str]]:
    """The record types the commands of the skill write, by the unit kind that holds them."""
    docs = schema.docs_for(skill.package)
    out = {}
    for kind in skill.kinds:
        unit = paths.Unit(Path("/x") / kind.folder / "u", Path("/x"), kind, skill)
        out[kind.kind] = set(records.layout(unit, docs).forms)
    return out


class FormatExamples(unittest.TestCase):
    def text_of(self, name: str) -> str:
        files = sorted((ROOT / "skills" / name / "formats").glob("*.md"))
        return "\n".join(f.read_text(encoding="utf-8") for f in files)

    def test_every_written_type_of_each_skill_with_formats_has_an_example(self):
        for name, skill in SKILLS.items():
            if name == "design-better":
                continue
            text = self.text_of(name)
            self.assertTrue(text, f"{name} has no formats/ file")
            for kind, types in written_types(skill).items():
                self.assertTrue(types, (name, kind))
                for record_type in sorted(types):
                    if (name, record_type) in UNUSED:
                        continue
                    with self.subTest(skill=name, kind=kind, type=record_type):
                        self.assertRegex(text, rf'"type":\s*"{re.escape(record_type)}"', f"no example of {record_type}")

    def test_design_betters_only_record_is_the_canvas_head_and_its_skill_md_names_its_fields(self):
        self.assertEqual(written_types(design.SKILL), {"canvas": {"canvas", "decision"}})
        text = (ROOT / "skills" / "design-better" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("type `canvas`", text)
        for field in ("title", "question", "widths", "versions"):
            self.assertRegex(text, rf"`{field}`", f"design-better SKILL.md does not name `{field}`")

    def test_the_helper_finds_the_types_the_schemas_declare(self):
        types = written_types(code.SKILL)
        self.assertTrue({"task", "decision", "card"} <= set().union(*types.values()))
        self.assertIn("slides", set().union(*written_types(show.SKILL).values()))
        self.assertIn("question", set().union(*written_types(research.SKILL).values()))


if __name__ == "__main__":
    unittest.main()
