import json
from pathlib import Path

DATA = Path("reminders.json")


def load():
    return json.loads(DATA.read_text())


def save(items):
    DATA.write_text(json.dumps(items))
