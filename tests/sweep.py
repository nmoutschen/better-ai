"""Which cases of an exhaustive test run. Pull requests run a sample, so the suite stays fast; the scheduled and manual
runs set BETTER_AI_SWEEP=full and run every case. The sample is the same on every run and holds at least one case of
every class the test tells apart (a file kind, a command, an exception type, a kind of wrong value)."""

import os
import random

SEED = 20261122
SHARE = 0.1


def full() -> bool:
    return os.environ.get("BETTER_AI_SWEEP") == "full"


def cases(items, key=None) -> list:
    """Every item in a full sweep. Otherwise the first item of each class and about one in ten of the rest, picked with
    a fixed seed. `key` is a function giving an item's class, or a list of them when the test tells apart several kinds
    of class (a command and an exception type): each class of each function is kept once. With no `key`, all items are
    one class."""
    items = list(items)
    if full():
        return items
    keys = [lambda item: None] if key is None else key if isinstance(key, (list, tuple)) else [key]
    rng = random.Random(SEED)
    seen = set()
    chosen = []
    for item in items:
        groups = {(n, f(item)) for n, f in enumerate(keys)}
        draw = rng.random() < SHARE
        if draw or not groups <= seen:
            seen |= groups
            chosen.append(item)
    return chosen
