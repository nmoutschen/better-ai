"""Plugin hooks so partners can extend bookings later."""

HOOKS = {"before_book": [], "after_book": [], "before_cancel": []}


def hook(name):
    def wrap(func):
        HOOKS[name].append(func)
        return func
    return wrap


def run(name, *args):
    for func in HOOKS[name]:
        func(*args)
