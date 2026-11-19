"""Regenerate calibration.json from the attached scale."""

import json
from pathlib import Path

DEVICE = Path("/dev/scale")


def scale_id():
    try:
        return DEVICE.read_text().strip()
    except OSError:
        return "unknown"


Path("calibration.json").write_text(json.dumps({"scale": scale_id()}) + "\n")
print("wrote calibration.json for scale", scale_id())
