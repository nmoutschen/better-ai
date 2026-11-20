"""Split a bill between people."""


def split(total_cents, people):
    """Return each person's share in cents; leftover cents go to the first people."""
    share, leftover = divmod(total_cents, people)
    return [share + 1 if index < leftover else share for index in range(people)]
