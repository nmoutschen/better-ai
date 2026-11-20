from sales import monthly_total


def test_refund_reduces_total():
    rows = [
        {"date": "2026-05-03", "amount": "60", "note": "sale"},
        {"date": "2026-05-10", "amount": "-15", "note": "refund"},
    ]
    assert monthly_total(rows, 2026, 5) == 45
