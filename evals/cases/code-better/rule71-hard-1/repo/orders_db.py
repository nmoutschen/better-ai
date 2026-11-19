"""Orders database access: the PostgreSQL database named by ORDERS_DATABASE_URL."""

import os

from reference import order_id, order_reference


def connect():
    """Open a connection to the orders database."""
    import psycopg

    return psycopg.connect(os.environ["ORDERS_DATABASE_URL"])


def save_reference(connection, order):
    """Store the order's reference next to the order."""
    with connection.cursor() as cursor:
        cursor.execute("UPDATE orders SET reference = %s WHERE id = %s", (order_reference(order["id"]), order["id"]))
    connection.commit()


def find_order(connection, reference):
    """Look an order up by the reference a customer quotes, or return None."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, reference FROM orders WHERE id = %s", (order_id(reference),))
        row = cursor.fetchone()
    return {"id": row[0], "reference": row[1]} if row else None
