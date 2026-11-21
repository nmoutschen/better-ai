"""The outbox: emails to send are written here in the same transaction as the order (see docs/adr/0002)."""

import json


def enqueue(conn, kind: str, payload: dict, now: str) -> None:
    """Add an email to the outbox; jobs/send_emails.py sends it."""
    conn.execute("INSERT INTO outbox (kind, payload, created_at) VALUES (?, ?, ?)", (kind, json.dumps(payload), now))


def unsent(conn) -> list[tuple[int, str, dict]]:
    """Return the emails not sent yet, oldest first, as (id, kind, payload)."""
    rows = conn.execute("SELECT id, kind, payload FROM outbox WHERE sent_at IS NULL ORDER BY id").fetchall()
    return [(outbox_id, kind, json.loads(payload)) for outbox_id, kind, payload in rows]


def mark_sent(conn, outbox_id: int, now: str) -> None:
    """Mark one email as sent."""
    conn.execute("UPDATE outbox SET sent_at = ? WHERE id = ?", (now, outbox_id))
