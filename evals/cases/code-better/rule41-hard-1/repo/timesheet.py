from durations import format_duration, parse_duration


def week_total(entries):
    """Total of a week's entries, such as ['1h30m', '2h'], formatted like the entries."""
    return format_duration(sum(parse_duration(entry) for entry in entries))


if __name__ == "__main__":
    import sys

    print(week_total(sys.argv[1:]))
