import sys

from stock import stock_report

if __name__ == "__main__":
    with open(sys.argv[1]) as export:
        print(stock_report(export.read()))
