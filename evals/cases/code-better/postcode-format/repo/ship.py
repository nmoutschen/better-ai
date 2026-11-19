from address import postcode

def label(record):
    return "Postal: " + postcode(record["zip"])
