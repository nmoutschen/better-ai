"""Cron, every minute: send the emails waiting in the outbox through MailRelay (an external SMTP relay)."""

import json
import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

from shop import store

TEMPLATES = {"order_confirmation": "Thank you for your order #{order_id}. We will post it within two working days."}


def main() -> None:
    """Send every unsent outbox email; mark each sent."""
    with store.connect() as conn, smtplib.SMTP_SSL("smtp.mailrelay.example", 465) as smtp:
        smtp.login("tidewater", os.environ["MAILRELAY_PASSWORD"])
        rows = conn.execute("SELECT id, kind, payload FROM outbox WHERE sent_at IS NULL ORDER BY id").fetchall()
        for outbox_id, kind, payload in rows:
            data = json.loads(payload)
            (email,) = conn.execute(
                "SELECT c.email FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.id = ?",
                (data["order_id"],),
            ).fetchone()
            message = EmailMessage()
            message["From"], message["To"], message["Subject"] = "shop@tidewater.example", email, "Your order"
            message.set_content(TEMPLATES[kind].format(**data))
            smtp.send_message(message)
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("UPDATE outbox SET sent_at = ? WHERE id = ?", (now, outbox_id))


if __name__ == "__main__":
    main()
