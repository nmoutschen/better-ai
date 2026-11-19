# tablefmt 2.3.1, copied from upstream.


def render(rows, columns):
    """Return rows (dicts) as a plain-text table with the given columns."""
    widths = {column: max([len(column)] + [len(str(row[column])) for row in rows]) for column in columns}
    lines = ["  ".join(column.ljust(widths[column]) for column in columns)]
    lines.append("  ".join("-" * widths[column] for column in columns))
    for row in rows:
        lines.append("  ".join(str(row[column]).ljust(widths[column]) for column in columns))
    return "\n".join(lines)
