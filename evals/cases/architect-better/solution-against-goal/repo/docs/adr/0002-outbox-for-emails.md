# 0002. Outbox for emails

Date: 2025-11-14
Status: Accepted

## Context

When MailRelay was slow, order requests timed out after the card was charged, and customers ordered twice.

## Decision

The API writes each email to an `outbox` table in the same transaction as the order. A cron job sends them.

## Consequences

- An order never waits on MailRelay.
- Emails go out up to a minute late.
- Every new kind of email goes through the outbox.
