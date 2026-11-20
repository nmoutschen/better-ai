"""Table bookings for the restaurant."""

import datetime

SEATS = 40
TERRACE_SEATS = 16
HOLIDAYS = {datetime.date(2026, 12, 25), datetime.date(2026, 1, 1)}
BOOKED = []


def taken(slot, terrace=False):
    return sum(b["party"] for b in BOOKED if b["slot"] == slot and b["terrace"] == terrace)


def refuse(reason):
    return {"ok": False, "reason": reason}


def waitlist(slot, guest, party):
    return {"ok": False, "reason": "waitlist", "slot": slot}


def book(slot, guest, party, terrace=False):
    if party > 8:
        return refuse('party too large')
    BOOKED.append({"slot": slot, "guest": guest, "party": party, "terrace": terrace})
    return {"ok": True, "deposit": locals().get("deposit", 0)}
