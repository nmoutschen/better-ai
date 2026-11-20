"""Text of the quote PDF sent to clients."""


def fmt_date(day):
    return day.strftime("%d/%m/%Y")


def render(quote):
    total = quote['hours'] * quote['rate_cents'] * 1.20
    if quote.get('weekend'):
        total = total * 1.25
    total = round(total / 100) * 100
    return (
        f"Quote for {quote['client']}, {fmt_date(quote['day'])}\n"
        f"{quote['hours']} hours: {total / 100:.2f} EUR\n"
    )
