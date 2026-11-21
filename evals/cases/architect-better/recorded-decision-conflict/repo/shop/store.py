"""Orders in the SQLite database."""

import sqlite3
from pathlib import Path

DB = Path("data/shop.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, email TEXT UNIQUE, name TEXT, password_hash TEXT);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(id), placed_at TEXT,
    total_cents INTEGER, status TEXT, payment_ref TEXT, shipping_address TEXT
);
CREATE TABLE IF NOT EXISTS order_lines (order_id INTEGER, isbn TEXT, title TEXT, qty INTEGER, price_cents INTEGER);
CREATE TABLE IF NOT EXISTS outbox (id INTEGER PRIMARY KEY, kind TEXT, payload TEXT, created_at TEXT, sent_at TEXT);
"""


def connect() -> sqlite3.Connection:
    """Open the database and create the tables if needed."""
    DB.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)
    return conn


def save_order(conn, customer_id, lines, total_cents, payment_ref, address, placed_at):
    """Insert an order and its lines; return the order id."""
    cur = conn.execute(
        "INSERT INTO orders (customer_id, placed_at, total_cents, status, payment_ref, shipping_address)"
        " VALUES (?, ?, ?, 'paid', ?, ?)",
        (customer_id, placed_at, total_cents, payment_ref, address),
    )
    order_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO order_lines VALUES (?, ?, ?, ?, ?)",
        [(order_id, l["isbn"], l["title"], l["qty"], l["price_cents"]) for l in lines],
    )
    return order_id


def get_order(conn, order_id):
    """Return one order as a dict, or None."""
    row = conn.execute("SELECT id, customer_id, placed_at, total_cents, status FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        return None
    return dict(zip(("id", "customer_id", "placed_at", "total_cents", "status"), row))


def customer_email_for_order(conn, order_id):
    """Return the email address of the customer who placed an order."""
    (email,) = conn.execute(
        "SELECT c.email FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.id = ?", (order_id,)
    ).fetchone()
    return email
