# textstats requirements

- Words are runs of letters and apostrophes, compared in lower case.
- `word_count(text)` returns the number of words; punctuation is not a word.
- `top_words(text, n)` returns the `n` most frequent words as `(word, count)` pairs, most frequent first, and words with the same count in alphabetical order.
- `top_words` leaves out the stop words listed in `textstats/stopwords.txt`.
- Never change the signatures of the public functions in `textstats/api.py`: other teams' services call them with positional arguments.
