"""discover-better: the `set` matrix of the decisions and tests (T14); see `discover_matrix` and `test_discover_integration`."""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
import discover_matrix as M  # noqa: E402


class Matrix(M.MatrixCase):
    def test_set_decisions_and_tests(self):
        self.matrix(("decision", "test"), ("decision", "test"))


if __name__ == "__main__":
    unittest.main()
