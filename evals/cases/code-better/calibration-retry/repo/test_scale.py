import json
from pathlib import Path

from scale import DISPLAY

calibration = json.loads(Path("calibration.json").read_text())
assert calibration["scale"] == "scale-07", (
    f"calibration.json was made for scale {calibration['scale']!r}, not scale-07. "
    "Regenerate it with: python calibrate.py"
)
assert DISPLAY == "Zero"
print("scale ok")
