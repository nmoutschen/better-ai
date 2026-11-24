# Shared record commit proof of concept

Run `sh tests/formal/verify_record_commit.sh` from the repository root. The script uses a pinned AMD64 Nagini image and works with OrbStack's Rosetta support on Apple Silicon.

The model treats the complete contents of one file as a value protected by a directory lock. Nagini proves that the candidate sequence publishes the replacement when the contents match and leaves the file untouched when they differ. A second check confirms that Nagini rejects a sequence that releases the lock between comparing and publishing.

The model assumes exclusive locking and publication of a complete file. The CLI still uses its current filesystem adapter and write paths. The production proof must connect those paths to the verified sequence and check the assumptions against the macOS and Linux adapters.
