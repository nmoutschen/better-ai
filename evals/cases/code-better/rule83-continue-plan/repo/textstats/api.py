import re
from collections import Counter

WORD = re.compile(r"[a-z']+")


def _tokenize(text):
    return WORD.findall(text.lower())


def word_count(text):
    return len(_tokenize(text))


def top_words(text, n):
    return Counter(_tokenize(text)).most_common(n)
