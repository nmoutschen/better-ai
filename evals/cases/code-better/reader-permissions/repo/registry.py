def search(rows, name):
    return [row for row in rows if name.lower() in row["name"].lower()]
