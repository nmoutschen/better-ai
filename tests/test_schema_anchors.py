"""A `$` in a schema pattern never matches before a final newline, in any schema of any skill."""

import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from better_ai import architect, code, design, discover, research, schema, show  # noqa: E402,F401  (register hooks)

SKILLS = ("architect", "code", "design", "discover", "research", "show")
SAMPLES = [
    "x", "1", "a1", "P1", "R1", "D1", "X1", "K1", "M1", "T1", "Q1", "Q-w1-1", "v1", "1.0", "n.d.", "2024", "2024-03",
    "S-a1-1", "E-a1-1", "C-w1-1", "L-a1-1", "https://x.org/a", "a" * 64, "2026-11-23T10:00:00Z", "abc", "a.b",
    "a-b", "a_b", "foo/bar", "slides.md", "1280x800", "375", "10:00", "#ffffff", "F1", "V1", "G1", "E1", "L1", "N1", "box:a", "box:a+edge:b", "step:a/b", "S1", "A1", "Q-1", "2026-11-23",
]  # fmt: skip


def patterns(node, where=""):
    if isinstance(node, dict):
        if isinstance(node.get("pattern"), str):
            yield where, node["pattern"]
        for key, value in node.items():
            yield from patterns(value, f"{where}/{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from patterns(value, f"{where}/{i}")


def ends_with_dollar(pattern):
    return pattern.endswith("$") and not pattern.endswith("\\$")


class Anchors(unittest.TestCase):
    def test_a_value_a_pattern_ending_in_dollar_accepts_is_refused_with_a_newline_added(self):
        seen = 0
        for package in SKILLS:
            for name, doc in schema.docs_for(package).items():
                for where, pattern in patterns(doc):
                    if not ends_with_dollar(pattern):
                        continue
                    with self.subTest(package=package, schema=name, at=where, pattern=pattern):
                        good = [s for s in SAMPLES if re.search(pattern, s)]
                        self.assertTrue(good, "add a value this pattern accepts to SAMPLES")
                        probe = {"pattern": pattern}
                        for value in good:
                            self.assertEqual(schema.validate_instance(value, probe, {}), [], value)
                            self.assertTrue(schema.validate_instance(value + "\n", probe, {}), repr(value + "\n"))
                    seen += 1
        self.assertGreater(seen, 20)


if __name__ == "__main__":
    unittest.main()
