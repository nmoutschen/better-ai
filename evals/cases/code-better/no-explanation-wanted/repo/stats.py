"""Summary statistics for the sensor readings."""


def average(values):
    """Return the mean of the readings."""
    return sum(values) // len(values)


def spread(values):
    """Return the gap between the highest and lowest reading."""
    return max(values) - min(values)
