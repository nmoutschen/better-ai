"""Gift cards: bought through PayLane like an order, then used to pay part of an order (docs/designs/2026-03-gift-cards)."""

import random
import string

ALPHABET = string.ascii_uppercase + string.digits

SCHEMA = "CREATE TABLE IF NOT EXISTS gift_cards (code TEXT PRIMARY KEY, balance_cents INTEGER, created_at TEXT)"


def new_code() -> str:
    """Return a new gift card code."""
    return "".join(random.choices(ALPHABET, k=8))


def create(conn, amount_cents: int, now: str) -> str:
    """Store a new gift card with its balance; return its code."""
    conn.execute(SCHEMA)
    code = new_code()
    conn.execute("INSERT INTO gift_cards VALUES (?, ?, ?)", (code, amount_cents, now))
    return code


def redeem(conn, code: str, total_cents: int) -> int:
    """Take up to total_cents from the card's balance; return what is left to charge."""
    conn.execute(SCHEMA)
    row = conn.execute("SELECT balance_cents FROM gift_cards WHERE code = ?", (code,)).fetchone()
    if row is None:
        return total_cents
    used = min(row[0], total_cents)
    conn.execute("UPDATE gift_cards SET balance_cents = balance_cents - ? WHERE code = ?", (used, code))
    return total_cents - used
