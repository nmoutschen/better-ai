"""Cron, every minute: send the emails waiting in the outbox through MailRelay (an external SMTP relay)."""

import os
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

from shop import outbox, store

TEMPLATES = {"order_confirmation": "Thank you for your order #{order_id}. We will post it within two working days."}


def main() -> None:
    """Send every unsent outbox email; mark each sent."""
    with store.connect() as conn, smtplib.SMTP_SSL("smtp.mailrelay.example", 465) as smtp:
        smtp.login("tidewater", os.environ["MAILRELAY_PASSWORD"])
        for outbox_id, kind, data in outbox.unsent(conn):
            message = EmailMessage()
            message["From"], message["To"], message["Subject"] = (
                "shop@tidewater.example",
                store.customer_email_for_order(conn, data["order_id"]),
                "Your order",
            )
            message.set_content(TEMPLATES[kind].format(**data))
            smtp.send_message(message)
            outbox.mark_sent(conn, outbox_id, datetime.now(timezone.utc).isoformat())


if __name__ == "__main__":
    main()
