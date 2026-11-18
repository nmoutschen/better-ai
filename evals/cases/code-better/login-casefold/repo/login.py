from accounts import find


def login(users, name):
    user = find(users, name)
    return "welcome" if user is not None else "unknown user"
