"""Text for the shelf labels."""

import textwrap

WIDTH = 24


def title_lines(title):
    """Return the product title as label lines, wrapped to the label width."""
    return textwrap.wrap(title, WIDTH)


def price_line(cents):
    """Return the price line, such as '€3.50'."""
    return f"€{cents // 100}.{cents % 100:02d}"
