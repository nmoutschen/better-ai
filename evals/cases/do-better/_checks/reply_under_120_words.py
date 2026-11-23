"""reply.md is under 120 words, as the request asks."""
words = len(open("reply.md").read().split())
assert words < 120, f"{words} words"
