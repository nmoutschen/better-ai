# customers

Customer accounts live in `data/customers.json`. Each account has `id`, `email`, `name`,
`shipping_address`, `loyalty_points` and `created_at`. An account has one shipping address.

- Loyalty points are worth money at checkout: 100 points = 1.00 EUR.
- Orders in `data/orders.json` refer to an account by `customer_id`.
- Some customers signed up twice with the same email. Their duplicate accounts often have
  different shipping addresses, and each has its own points.

`customers.py` loads and saves both files.
