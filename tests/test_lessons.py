"""code-better's lessons.jsonl: the schema accepts the lessons of a real build and rejects the shapes it must."""

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "skills" / "code-better" / "schemas"
FIXTURE = Path(__file__).parent / "fixtures" / "code-better-lessons.jsonl"
AT = "2026-11-21T12:00:00Z"

_spec = importlib.util.spec_from_file_location("schema", ROOT / "skills" / "code-better" / "scripts" / "schema.py")
schema = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("schema", schema)
_spec.loader.exec_module(schema)


def tasks(ids):
    return [
        {
            "type": "task",
            "at": AT,
            "by": "coordinator",
            "id": i,
            "task": f"task {i}",
            "mode": "feature",
            "requirements": [],
            "check": "none",
            "status": "merged",
        }
        for i in ids
    ]


def errors(lessons, task_ids=("T3", "T5", "T6", "T8")):
    """The schema.py check errors of a change folder with tasks.jsonl and the given lessons.jsonl lines."""
    with tempfile.TemporaryDirectory() as d:
        folder = Path(d) / ".code" / "c"
        folder.mkdir(parents=True)
        (Path(d) / ".git").mkdir()
        (folder / "tasks.jsonl").write_text("".join(json.dumps(t) + "\n" for t in tasks(task_ids)))
        (folder / "lessons.jsonl").write_text("".join(json.dumps(r) + "\n" for r in lessons))
        return [str(e) for e in schema.check_paths([folder / "lessons.jsonl"], SCHEMAS)]


def fixture():
    return [json.loads(line) for line in FIXTURE.read_text().splitlines()]


class Lessons(unittest.TestCase):
    def test_the_ten_lessons_of_a_real_build_validate(self):
        lessons = fixture()
        self.assertEqual(len(lessons), 10)
        self.assertEqual(errors(lessons), [])

    def test_a_lesson_without_a_rule_is_rejected(self):
        bad = copy.deepcopy(fixture())
        del bad[0]["rule"]
        found = errors(bad)
        self.assertEqual(len(found), 1)
        self.assertIn("rule", found[0])

    def test_an_extra_field_is_rejected(self):
        bad = copy.deepcopy(fixture())
        bad[2]["why"] = "because"
        found = errors(bad)
        self.assertEqual(len(found), 1)
        self.assertIn("why", found[0])

    def test_an_extra_field_in_found_in_is_rejected(self):
        bad = copy.deepcopy(fixture())
        bad[2]["found_in"][0]["round"] = 2
        self.assertEqual(len(errors(bad)), 1)

    def test_a_task_that_is_not_in_tasks_jsonl_is_dangling(self):
        found = errors(fixture(), task_ids=("T3", "T5", "T6"))
        self.assertTrue(found)
        self.assertTrue(all("dangling" in e and '"T8"' in e for e in found), found)

    def test_found_in_needs_a_task_and_a_finding(self):
        bad = copy.deepcopy(fixture())
        del bad[0]["found_in"][0]["finding"]
        self.assertEqual(len(errors(bad)), 1)


if __name__ == "__main__":
    unittest.main()
