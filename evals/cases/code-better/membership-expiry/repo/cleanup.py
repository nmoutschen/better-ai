def cleanup(rows):
    return [row["id"] for row in rows if row["expired"]]
