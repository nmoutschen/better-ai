"""returns.md is shorter than the planted page (228 words): the user asked to cut it down."""
words = len(open("returns.md").read().split())
assert words < 228, f"{words} words"
