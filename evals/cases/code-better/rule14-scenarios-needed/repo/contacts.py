"""Small tools for the club's contact lists."""

import csv
import sys


def load(path):
    """Read a contacts CSV with name and email columns."""
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def save(path, contacts):
    """Write contacts to a CSV with name and email columns."""
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["name", "email"])
        writer.writeheader()
        writer.writerows(contacts)


def main(argv):
    """Run one command: count FILE."""
    command, *args = argv
    if command == "count":
        print(len(load(args[0])))
    else:
        sys.exit(f"unknown command: {command}")


if __name__ == "__main__":
    main(sys.argv[1:])
