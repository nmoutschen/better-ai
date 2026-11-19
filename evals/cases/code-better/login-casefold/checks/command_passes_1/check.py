from accounts import find, register
from login import login
users = {}
register(users, 'Straße', 1)
register(users, 'Ana', 2)
assert find(users, 'STRASSE') == 1 and find(users, 'ana') == 2 and find(users, 'bob') is None
assert login(users, 'STRASSE') == 'welcome'
assert login(users, 'ana') == 'welcome'
assert login(users, 'bob') == 'unknown user'
for taken in ('ANA', 'straße', 'Strasse'):
    try:
        register(users, taken, 3)
    except ValueError:
        continue
    raise AssertionError(f'{taken} must collide')
register(users, 'Anna', 4)
assert find(users, 'ANNA') == 4
