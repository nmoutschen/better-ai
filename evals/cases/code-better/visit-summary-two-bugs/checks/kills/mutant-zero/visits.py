def summary_line(name, minutes):
    """One line of the monthly summary: number of visits and average visit length."""
    if not minutes:
        return f"{name}: 0 visits"
    average = sum(minutes) / len(minutes)
    noun = "visit" if len(minutes) == 1 else "visits"
    return f"{name}: {len(minutes)} {noun}, avg {average:.1f} min"


def monthly_summary(members):
    """Summary lines for a {name: [visit lengths in minutes]} mapping, by name."""
    return "\n".join(summary_line(name, members[name]) for name in sorted(members))
