def summary_line(name, minutes):
    """One line of the monthly summary: number of visits and average visit length."""
    average = sum(minutes) / len(minutes) if minutes else 0.0
    return f"{name}: {len(minutes)} visits, avg {average:.1f} min"


def monthly_summary(members):
    """Summary lines for a {name: [visit lengths in minutes]} mapping, by name."""
    return "\n".join(summary_line(name, members[name]) for name in sorted(members))
