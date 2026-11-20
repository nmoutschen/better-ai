"""Reminder emails."""


def fmt_date(day):
    return day.strftime("%d/%m/%Y")


def reminder(quote):
    return f"Your quote of {fmt_date(quote['day'])} expires in 30 days."
