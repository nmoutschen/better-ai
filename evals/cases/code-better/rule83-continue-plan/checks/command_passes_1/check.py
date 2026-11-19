import inspect

from textstats import api

assert str(inspect.signature(api.word_count)) == "(text)", inspect.signature(api.word_count)
assert str(inspect.signature(api.top_words)) == "(text, n)", inspect.signature(api.top_words)
assert api.top_words("plum cherry plum cherry date date", 3) == [("cherry", 2), ("date", 2), ("plum", 2)]
assert api.top_words("melon kiwi kiwi lime lime", 1) == [("kiwi", 2)]
assert api.top_words("pear apple pear apple fig", 2) == [("apple", 2), ("pear", 2)]
assert api.word_count("Hello, world -- again!") == 3
