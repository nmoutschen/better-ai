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
    if slot.weekday() == 0:
        return refuse('closed on Mondays')
    if slot.date() in HOLIDAYS:
        return refuse('closed on public holidays')
    if slot.hour * 60 + slot.minute > 21 * 60 + 30:
        return refuse('too late')
    if terrace and slot.month not in (5, 6, 7, 8, 9):
        return refuse('terrace closed')
    deposit = 2000 * party if party > 6 else 0
    if guest.get('regular'):
        deposit = 0
    if taken(slot) + party > SEATS:
        return waitlist(slot, guest, party)
    if terrace and taken(slot, terrace=True) + party > TERRACE_SEATS:
        return waitlist(slot, guest, party)
    BOOKED.append({"slot": slot, "guest": guest, "party": party, "terrace": terrace})
    return {"ok": True, "deposit": locals().get("deposit", 0)}
