# Privacy

What we keep about customers, and what we may send them.

- We keep a customer's email, name, password hash, orders and shipping addresses (see `shop/store.py`).
- We email customers only about their own orders: the order confirmation. We have no consent from anyone for any other
  email.
- Any other email to a customer needs their opt-in first, and a working unsubscribe link in every such email (GDPR and
  the ePrivacy rules). We have neither today.
- A customer can ask us to delete their account; we do it by hand.
