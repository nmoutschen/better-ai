def register(users, name, user):
    if any(existing.casefold() == name.casefold() for existing in users):
        raise ValueError("username taken")
    users[name] = user


def find(users, name):
    return users.get(name)
