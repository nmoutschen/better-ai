"""discover-better: the `set` matrix of the sources and evidence (T14); see `discover_matrix` and `test_discover_integration`."""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
import discover_matrix as M  # noqa: E402


class Matrix(M.MatrixCase):
    def test_set_sources_and_evidence(self):
        self.matrix(("source", "evidence"), ("source", "evidence"))


if __name__ == "__main__":
    unittest.main()
