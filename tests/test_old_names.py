"""The docs, README, PRINCIPLES.md and evals name no script a skill no longer ships (S55, S56)."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = re.compile(r"(?<![\w])(architect|dashboard|board|canvas|show|diagram|page|schema)\.py\b")
# Planted project files that the eval cases ask an agent to edit; they are not the skills' scripts.
PLANTED = ("evals/cases/code-better/reuse-http-helper/", "evals/cases/code-better/shared-formatter/")
SKIP = {".venv", "__pycache__", "node_modules", ".git"}
TEXT = {".md", ".yaml", ".yml", ".py", ".json", ".jsonl", ".txt", ".toml"}


def files():
    for top in ("README.md", "PRINCIPLES.md", "docs", "evals"):
        path = ROOT / top
        for found in [path] if path.is_file() else sorted(path.rglob("*")):
            relative = found.relative_to(ROOT).as_posix()
            if (
                found.is_file()
                and found.suffix in TEXT
                and not SKIP & set(found.parts)
                and not relative.startswith(PLANTED)
                and found.name != "uv.lock"
            ):
                yield found, relative


class OldNames(unittest.TestCase):
    def test_no_old_script_name_in_docs_or_evals(self):
        found = []
        for path, relative in files():
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if OLD.search(line):
                    found.append(f"{relative}:{number}: {line.strip()[:100]}")
        self.assertEqual([], found)

    def test_the_search_finds_files(self):
        self.assertTrue(any(relative == "PRINCIPLES.md" for _, relative in files()))
        self.assertTrue(OLD.search("RUN python3 scripts/schema.py check"))
        self.assertFalse(OLD.search("order_page.py"))


if __name__ == "__main__":
    unittest.main()
