# Architecture

```
Website (static, on Netlify) --HTTPS--> shop API (shop/api.py) --> SQLite data/shop.db
                                              |
                                              +--> PayLane (cards)
                                              +--> MailRelay (SMTP)
```

- **shop API** (`shop/api.py`): takes orders, charges the card through PayLane, saves the order, then sends the
  confirmation email straight to MailRelay before it answers. Customers log in with a signed session cookie
  (`shop/auth.py`).
- **SQLite** (`data/shop.db`): customers, orders, order lines. Backed up nightly to the NAS.
- Everything runs on one small VPS. The API and the database file share the machine.
