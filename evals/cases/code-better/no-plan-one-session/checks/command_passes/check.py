from handlers import contact, newsletter, signup

# The request allows returning the message or raising an error with it.
for handler in (signup, contact, newsletter):
    try:
        outcome = handler({'name': ''})
    except Exception as error:
        outcome = str(error)
    assert outcome == 'Name is required', (handler.__name__, outcome)
    assert handler({'name': 'Ana'}) == 'ok'
