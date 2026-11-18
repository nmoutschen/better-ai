import sys


def summarize(rows):
    return {"count": len(rows), "total": sum(rows)}


def main(argv):
    data = summarize([3, 4, 5])
    print(f"{data['count']} rows, total {data['total']}")


if __name__ == "__main__":
    main(sys.argv[1:])
