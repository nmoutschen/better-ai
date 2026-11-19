import argparse
import csv
import sys

from vendor.tablefmt import render


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return [
            {"date": row["date"], "item": row["item"], "amount": int(row["amount"])}
            for row in csv.DictReader(handle)
        ]


def main(argv=None):
    parser = argparse.ArgumentParser(prog="report")
    parser.add_argument("csv_file")
    args = parser.parse_args(argv)
    rows = load_rows(args.csv_file)
    print(render(rows, ["date", "item", "amount"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
