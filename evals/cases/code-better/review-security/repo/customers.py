"""Customer queries. Every query is scoped to the signed-in account."""


def list_customers(conn, account_id):
    """Return the account's customers, sorted by name."""
    rows = conn.execute(
        "SELECT id, name FROM customers WHERE account_id = ? ORDER BY name",
        (account_id,),
    )
    return [{"id": row[0], "name": row[1]} for row in rows]
