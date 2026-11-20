"""Unit conversions for the trip planner."""

KM_PER_MILE = 1.609344


def km_to_miles(km):
    """Return the distance in miles."""
    return km * KM_PER_MILE


def miles_to_km(miles):
    """Return the distance in kilometres."""
    return miles * KM_PER_MILE
