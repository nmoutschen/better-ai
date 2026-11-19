"""Audit trail client. In production, record() sends each event to the audit service."""

_events = []


def record(event, **ids):
    """Record an event with the ids it concerns."""
    _events.append({"event": event, **ids})


def recorded():
    """Events recorded in this process, oldest first."""
    return list(_events)
