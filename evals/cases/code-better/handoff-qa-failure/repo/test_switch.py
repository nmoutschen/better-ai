from pathlib import Path
from switch import OFF
Path("/mnt/qa/french-locale").stat()
assert OFF == "Arrêt"
