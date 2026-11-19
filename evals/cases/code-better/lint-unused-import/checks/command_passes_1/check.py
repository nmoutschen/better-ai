from labels import price_line, title_lines

title = "Organic jasmine green tea, loose leaf, 250 g"
assert title_lines(title) == [title], title_lines(title)
assert title_lines("Tea") == ["Tea"]
assert price_line(350) == "€3.50"
