from split import split

assert split(1000, 3) == [334, 333, 333], split(1000, 3)
assert split(4000, 3) == [1334, 1333, 1333], split(4000, 3)
for total in range(0, 3001, 7):
    for people in range(1, 8):
        shares = split(total, people)
        assert sum(shares) == total and max(shares) - min(shares) <= 1, (total, people, shares)
