# Observability

Production ships one thing off the servers: the audit trail. Output from
Python's `logging` stays on each server, is rotated every hour, and nobody
outside the on-call engineer ever reads it.

## Audit events

Anything that support or operations may need to look up later, such as a
change in the state of an order or a payment, goes through
`audit.record(event, **ids)`. Support searches the audit trail by id.

- Name events `<entity>.<past tense verb>`, such as `order.cancelled`.
- Pass ids only, such as `order_id`, `payment_id` or `customer_id`. Never pass
  personal data such as names or email addresses: the audit trail is kept for
  seven years.

## Logging

Use `logging` at debug level for detail that helps while debugging on a
server. It is not a record of what happened.
