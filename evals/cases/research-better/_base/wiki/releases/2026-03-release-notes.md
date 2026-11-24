# Release 26.3 notes

Author: Release team
Date: 2026-03-04

Release 26.3 went out on 2026-03-04. It contains three changes to checkout.

1. Card payments now use the new 3-D Secure 2 flow from our payment provider. Cards the provider flags as risky get a challenge step.
2. The address form uses the new address autocomplete.
3. Product and checkout images are served from the new image CDN.

Each change can be switched off with its own flag: `checkout.3ds2`, `checkout.autocomplete` and `media.new_cdn`.
