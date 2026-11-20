# Shop backend

Backend of a small web shop in Belgium. Prices are in cents, excluding VAT. VAT is 21% since 1 January 2026.

- `checkout.py` computes the order total and charges the card.
- `invoice.py` renders the invoice sent to the customer.
- `shipping.py` computes shipping costs.

Run the tests with `python -m unittest`.
