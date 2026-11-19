def total(month, entries):
    return sum(e["cents"] for e in entries if e["month"] == month and e["kind"] == "gift")
