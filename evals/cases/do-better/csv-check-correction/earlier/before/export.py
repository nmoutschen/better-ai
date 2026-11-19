"""Export members to CSV."""


def to_csv(members):
    """Return the members as CSV text with a header row."""
    lines = ["name,email"]
    for member in members:
        lines.append(f"{member['name']},{member['email']}")
    return "\n".join(lines) + "\n"
