import argparse

from inventory.store import load_items


def main(argv=None):
    parser = argparse.ArgumentParser(prog="inventory")
    commands = parser.add_subparsers(dest="command", required=True)
    show = commands.add_parser("list", help="print the items")
    show.add_argument("items")
    args = parser.parse_args(argv)
    if args.command == "list":
        for item in load_items(args.items):
            print(f"{item['sku']}  {item['name']}  {item['qty']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
