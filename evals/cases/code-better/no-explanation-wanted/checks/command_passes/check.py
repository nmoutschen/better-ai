from stats import average, spread

assert average([1, 2]) == 1.5, average([1, 2])
assert average([2, 4, 6]) == 4, average([2, 4, 6])
assert average([1, 1, 2]) == 4 / 3, average([1, 1, 2])
assert spread([3, 9, 5]) == 6
