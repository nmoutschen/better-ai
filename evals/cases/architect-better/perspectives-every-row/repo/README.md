# Tidewater Books shop

The online shop of Tidewater Books, a two-person bookshop. Customers order books on the website; we pack and post them.

- `shop/` is the web API the website calls (Python, standard library HTTP server).
- `jobs/` holds the scheduled jobs, run by cron on the same machine.
- The data lives in one SQLite file, `data/shop.db`.

Run the API with `python3 -m shop.api`. Run the tests with `python3 -m pytest`.

Documentation: `docs/architecture.md` (how the parts fit), `docs/adr/` (decision records), `docs/designs/` (designs of
changes, one folder per change), `docs/standards/` (rules every change follows).

About 40 orders a day, up to 300 in the week before Christmas.
