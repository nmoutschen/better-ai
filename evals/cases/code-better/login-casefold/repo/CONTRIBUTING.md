Compare people's names and usernames with str.casefold(), never lower(): lower() leaves names such as Straße unmatched.
Usernames are unique under casefold(): register() rejects a name that matches an existing one, and test_accounts.py checks it.
Every caller looks up a username through accounts.find().
