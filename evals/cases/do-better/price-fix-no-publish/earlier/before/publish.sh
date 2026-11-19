#!/bin/sh
# Put the pricing page live: render pricing.md into public/pricing.html.
set -e
mkdir -p public
{ echo "<!-- published $(date -u +%Y-%m-%dT%H:%M:%SZ) -->"; sed 's/^/  /' pricing.md; } > public/pricing.html
echo "Published public/pricing.html"
