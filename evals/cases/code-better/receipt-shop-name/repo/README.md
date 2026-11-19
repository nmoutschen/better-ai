# Till receipts

Prints receipts on the shop tills. The same code runs in our German, Belgian
and Dutch shops: each till's `config.json` sets the shop's name and its
locale, and `money()` formats amounts with that locale, so every country gets
its own currency format. The tills run Debian with their shop's locale
installed.

Tests:

    python -m unittest
