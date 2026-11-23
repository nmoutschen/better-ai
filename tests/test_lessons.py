"""code-better's lessons.jsonl: the schema accepts the lessons of a real build and rejects the shapes it must."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import better_ai.code  # noqa: E402,F401  (registers its hooks)
from better_ai import resources, schema  # noqa: E402

DOCS = schema.load_schemas(*resources.schema_sources("code"))
FIXTURE = Path(__file__).parent / "fixtures" / "code-better-lessons.jsonl"
AT = "2026-11-21T12:00:00Z"
TASK_IDS = ("T3", "T5", "T6", "T8")  # the tasks the fixture's lessons were found in


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


def errors(lessons):
    """The check errors of a change folder with tasks.jsonl and the given lessons.jsonl lines."""
    with tempfile.TemporaryDirectory() as d:
        folder = Path(d) / ".code" / "c"
        folder.mkdir(parents=True)
        (Path(d) / ".git").mkdir()
        (folder / "tasks.jsonl").write_text("".join(json.dumps(t) + "\n" for t in tasks(TASK_IDS)))
        (folder / "lessons.jsonl").write_text("".join(json.dumps(r) + "\n" for r in lessons))
        return [str(e) for e in schema.check_paths([folder / "lessons.jsonl"], docs=DOCS)]


def fixture():
    return [json.loads(line) for line in FIXTURE.read_text().splitlines()]


class Lessons(unittest.TestCase):
    def test_the_ten_lessons_of_a_real_build_validate(self):
        lessons = fixture()
        self.assertEqual(len(lessons), 10)
        self.assertEqual(errors(lessons), [])

    def test_found_in_needs_a_task_and_a_finding(self):
        bad = copy.deepcopy(fixture())
        del bad[0]["found_in"][0]["finding"]
        self.assertEqual(len(errors(bad)), 1)


if __name__ == "__main__":
    unittest.main()
