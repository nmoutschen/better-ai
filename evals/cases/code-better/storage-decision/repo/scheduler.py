from datetime import datetime

from store import load


def due(now=None):
    now = now or datetime.now()
    return [r for r in load() if r["at"] == now.strftime("%H:%M")]
