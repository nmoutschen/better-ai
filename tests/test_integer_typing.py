"""An integral float is not an integer: a renderer's range(3.0) fails, so a field the schemas call an integer refuses
3.0 and the check, not the renderer, says so. Moved from the old scripts' never-raise harness."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from better_ai import (  # noqa: E402, F401  (register their hooks)
    architect,
    code,
    design,
    discover,
    research,
    schema,  # noqa: E402
    show,
)

PACKAGE = ROOT / "src" / "better_ai"


class IntegerTyping(unittest.TestCase):
    def test_every_integer_the_schemas_name_refuses_an_integral_float(self):
        found = 0
        for path in sorted(PACKAGE.glob("**/schemas/*.schema.json")):
            docs = schema.load_schemas(PACKAGE / "schemas", path.parent)
            pending = [json.loads(path.read_text(encoding="utf-8"))]
            while pending:
                node = pending.pop()
                if isinstance(node, dict):
                    kind = node.get("type")
                    if kind == "integer" or (isinstance(kind, list) and "integer" in kind):
                        found += 1
                        with self.subTest(schema=path.name, node=str(node)[:60]):
                            self.assertTrue(schema.validate_instance(3.0, {**node, "type": kind}, docs))
                    pending.extend(node.values())
                elif isinstance(node, list):
                    pending.extend(node)
        self.assertGreater(found, 5)


if __name__ == "__main__":
    unittest.main()
