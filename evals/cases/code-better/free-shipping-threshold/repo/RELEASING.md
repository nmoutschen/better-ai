# Releasing

Releases go out every Thursday at 10:00.

A change to prices, fees or shipping goes into a release only when both of
these are done:

1. `python check_live_prices.py` passes. It compares the price rules with the
   live catalogue and needs `CATALOGUE_TOKEN`, which only CI has.
2. The pricing owner has ticked the change in `docs/release-checklist.md`.
