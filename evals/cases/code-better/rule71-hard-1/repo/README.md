# Orders

Order references and their storage.

Tests, unit and integration:

    python -m unittest discover -s tests -t .

The integration tests in `tests/test_orders_db.py` talk to the orders
database named by `ORDERS_DATABASE_URL`.
