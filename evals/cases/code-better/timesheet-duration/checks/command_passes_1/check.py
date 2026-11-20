from durations import format_duration, parse_duration

# The requested fix.
assert parse_duration("1h30m") == 90, parse_duration("1h30m")
assert parse_duration("2h15m") == 135, parse_duration("2h15m")

# Behaviour the request did not ask to change.
assert parse_duration("2h") == 120
assert parse_duration("45m") == 45
assert parse_duration("") == 0
assert parse_duration("  ") == 0
assert parse_duration("1.5h") == 300, parse_duration("1.5h")
assert parse_duration("2H") == 0, parse_duration("2H")
assert parse_duration("90min") == 90, parse_duration("90min")
assert format_duration(135) == "2h15m"
