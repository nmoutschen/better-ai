# Architecture

```
Website (static, on Netlify) --HTTPS--> shop API (shop/api.py) --> SQLite data/shop.db
                                              |                        ^
                                              +--> PayLane (cards)     |
cron every minute: jobs/send_emails.py -------------------------------+--> MailRelay (SMTP)
```

- **shop API** (`shop/api.py`): takes orders, charges the card through PayLane, saves the order and adds the
  confirmation email to the outbox in one transaction. Customers log in with a signed session cookie (`shop/auth.py`).
- **SQLite** (`data/shop.db`): customers, orders, order lines, outbox. Backed up nightly to the NAS.
- **send_emails job** (`jobs/send_emails.py`): cron, every minute; sends outbox emails through MailRelay.
- Everything runs on one small VPS. Cron and the API share the machine and the database file.
