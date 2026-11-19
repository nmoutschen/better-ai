def wait_seconds(header, now):
    """Return how many seconds a Retry-After header asks the client to wait."""
    return int(header)
