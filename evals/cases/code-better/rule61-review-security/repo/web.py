"""Request handlers for the customer pages."""

from customers import list_customers


def handle_list(conn, session, params):
    """GET /customers: the signed-in account's customers."""
    return {"customers": list_customers(conn, session["account_id"])}
