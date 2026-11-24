# Shared record commit proof of concept

Run `python3 tests/formal/verify_record_commit.py` from the repository root. The runner uses a pinned AMD64 Nagini image and works with OrbStack's Rosetta support on Apple Silicon.

The runner reads `_commit_locked` and its adjacent contracts from `src/better_ai/paths.py`. It verifies that the generated function has the same Python syntax tree as the production function after contract expressions are removed. `add` and `set` call this function through `replace_if_current`. Nagini proves that it publishes the replacement when the contents match and leaves the file untouched when they differ.

The negative control starts from that same production function and lets another writer change the file between comparison and publication. Nagini must reject the claim that the file still matches before publication.

The proof assumes that comparison reads complete bytes under the lock and that publication installs the complete replacement. The OS adapter, other write callers, and redaction recovery still need formal coverage.
