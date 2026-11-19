import datetime
import json
import sys


def closed_days(path="data/closed_days.txt"):
    with open(path, encoding="utf-8") as handle:
        return {datetime.date.fromisoformat(line.strip()) for line in handle if line.strip()}


def next_open_day(day, closed):
    while day in closed:
        day += datetime.timedelta(days=1)
    return day


def reminder_text(loan):
    return f"Dear {loan['member']}, \"{loan['title']}\" was due on {loan['due']}. Please return it."


def main(today):
    with open("data/loans.json", encoding="utf-8") as handle:
        loans = json.load(handle)
    for loan in loans:
        if datetime.date.fromisoformat(loan["due"]) < today:
            print(reminder_text(loan))
    return 0


if __name__ == "__main__":
    day = datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.date.today()
    sys.exit(main(day))
