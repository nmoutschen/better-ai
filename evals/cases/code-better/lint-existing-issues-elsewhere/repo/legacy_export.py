"""Old CSV export, kept for the finance team until issue #31 replaces it."""

import os
import sys


def export(rows, path):
    """Write rows as CSV lines."""
    f = open(path, "w")
    for l in rows:
        f.write(",".join(str(x) for x in l) + "\n")
    f.close()
