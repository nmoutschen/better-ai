from shifts import HEADER, export

assert HEADER == "Shift summary"
assert export([("Ana", "Mon", 3)]).splitlines() == ["Shift summary", "name,day,hours", "Ana,Mon,3"]
