from weight import label, header, footer
assert label(2.5, 'lb') == '2.5 lb'
assert label(1.25, 'kg') == '1.2 kg'
assert header('Ana') == 'Weights for Ana'
assert footer(3) == '3 entries'
