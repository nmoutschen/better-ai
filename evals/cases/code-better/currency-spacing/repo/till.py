from receipt import amount_label


def print_total(cents):
    print(amount_label(cents / 100))
