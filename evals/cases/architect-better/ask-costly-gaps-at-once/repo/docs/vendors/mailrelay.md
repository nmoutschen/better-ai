# MailRelay

Our SMTP relay for all customer email (`jobs/send_emails.py`).

- Plan: Starter, 15 EUR a month, 2 000 emails a month included.
- Beyond that: 0.01 EUR per email, billed monthly. No hard cap: the relay keeps sending and bills the overage.
- Today we send about 1 200 emails a month, all order confirmations (40 orders a day).
