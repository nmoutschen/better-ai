# Shared record commit proof of concept

Run `sh tests/formal/verify_record_commit.sh` from the repository root. The script uses a pinned AMD64 Nagini image and works with OrbStack's Rosetta support on Apple Silicon.

The runner reads `_commit_locked` and its adjacent contracts from `src/better_ai/paths.py`. It verifies that the generated function has the same Python syntax tree as the production function after contract expressions are removed. `add` and `set` call this function through `replace_if_current`. Nagini proves that it publishes the replacement when the contents match and leaves the file untouched when they differ.

The filesystem model assumes that comparison reads complete bytes under the lock and that publication installs the complete replacement. The Python tests exercise actual filesystem publication, including injected write failures and two processes attempting to update one snapshot. A separate lock model confirms that Nagini rejects a sequence that releases the lock between comparison and publication. The proof does not yet cover the OS adapter, all write callers, or redaction recovery.
