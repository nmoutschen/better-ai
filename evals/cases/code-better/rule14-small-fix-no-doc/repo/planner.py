"""Trip summaries."""

from units import km_to_miles


def summary(name, km):
    """Return a one-line summary of a trip."""
    return f"{name}: {km:.1f} km ({km_to_miles(km):.1f} miles)"
