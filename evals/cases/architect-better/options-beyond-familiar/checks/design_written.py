"""Pass when the change folder holds a design document, design.md, as step 4 of the design mode writes it."""

import sys
from pathlib import Path

DESIGN = Path("docs/designs/2026-11-order-export/design.md")

if not DESIGN.is_file() or not DESIGN.read_text().strip():
    sys.exit(f"{DESIGN} is missing or empty")
print(DESIGN, "written")
