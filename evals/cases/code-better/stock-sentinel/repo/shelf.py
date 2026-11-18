from stock import quantity

def label(item):
    value = quantity(item)
    return "unknown" if value is None else str(value)
