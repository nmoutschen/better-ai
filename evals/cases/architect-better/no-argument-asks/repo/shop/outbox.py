"""The outbox: emails to send are written here in the same transaction as the order (see docs/adr/0002)."""

import json


def enqueue(conn, kind: str, payload: dict, now: str) -> None:
    """Add an email to the outbox; jobs/send_emails.py sends it."""
    conn.execute("INSERT INTO outbox (kind, payload, created_at) VALUES (?, ?, ?)", (kind, json.dumps(payload), now))
