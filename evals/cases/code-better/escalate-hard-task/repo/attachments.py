"""Ticket attachments, stored under attachments/<ticket>/."""

from pathlib import Path

ROOT = Path(__file__).parent / "attachments"


class AttachmentError(Exception):
    """A request the service refuses."""


def list_attachments(ticket: str) -> list[str]:
    """Return the names of a ticket's attachments, sorted."""
    folder = ROOT / ticket
    if not folder.is_dir():
        return []
    return sorted(path.name for path in folder.iterdir() if path.is_file())
