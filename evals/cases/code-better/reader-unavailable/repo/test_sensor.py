from pathlib import Path
from sensor import LABEL
Path('/mnt/lab/reader').read_bytes()
assert LABEL == 'Ready'
