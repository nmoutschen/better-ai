def header(name):
    return "Weights for %s" % name


def label(value, unit):
    if unit == "lb":
        return "%.1f kg" % value
    return "%.1f kg" % value


def footer(count):
    return "%d entries" % count
