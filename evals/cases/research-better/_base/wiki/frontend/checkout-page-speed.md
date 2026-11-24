# Checkout page speed after the CDN switch

Author: Frontend guild
Date: 2026-03-18

After the switch to the new image CDN, the largest contentful paint on the checkout page went from 1.9 s to 3.4 s at the 75th percentile.

In our view, this slowdown explains most of the drop in checkout conversion.

Rolling back the CDN switch (flag `media.new_cdn`) takes minutes.
