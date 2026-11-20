"""Daily report for the owner, written in 2024 and unchanged since."""

import datetime


def daily_report(bookings, today):
    start = today - datetime.timedelta(days=1)
    rows = [b for b in bookings if start <= b["slot"].date() <= today]
    guests = sum(b["party"] for b in rows)
    terrace = sum(b["party"] for b in rows if b["terrace"])
    lines = ["Daily report", f"From {start:%d/%m} to {today:%d/%m}"]
    lines.append(f"Bookings: {len(rows)}")
    lines.append(f"Guests: {guests}")
    lines.append(f"Terrace guests: {terrace}")
    lines.append(f"Inside guests: {guests - terrace}")
    if rows:
        lines.append(f"Average party: {guests / len(rows):.1f}")
    return "\n".join(lines)
