from accounts import register

users = {}
register(users, "Straße", 1)
try:
    register(users, "STRASSE", 2)
except ValueError:
    pass
else:
    raise AssertionError("STRASSE must collide with Straße")
print("accounts ok")
