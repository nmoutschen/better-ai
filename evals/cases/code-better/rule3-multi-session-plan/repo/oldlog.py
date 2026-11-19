"""Home-grown logger. Deprecated: services move to the standard logging module."""

import sys


def write(level, message):
    sys.stderr.write(f"[{level}] {message}\n")
