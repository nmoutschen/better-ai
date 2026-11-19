sold = set()

def available(seat):
    return seat not in sold

def book(seat):
    sold.add(seat)
