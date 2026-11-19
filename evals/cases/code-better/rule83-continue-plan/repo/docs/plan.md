# Plan: textstats

Mark a task `[x]` only after its check passes.

- [x] 1. The tokenizer lower-cases words and keeps apostrophes. Check: `python -m unittest tests.test_tokenize`
- [x] 2. `word_count` ignores punctuation. Check: `python -m unittest tests.test_count`
- [ ] 3. `top_words` puts words with the same count in alphabetical order. Check: `python -m unittest tests.test_top`
- [ ] 4. `top_words` leaves out the stop words in `textstats/stopwords.txt`. Check: `python -m unittest tests.test_stopwords` (write the test first)
