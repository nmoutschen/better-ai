"""Customer sessions: the website sets a signed `session` cookie at login."""

import hashlib
import hmac
import os


def customer_from_cookie(cookie_header: str):
    """Return the logged-in customer's id, or None when the cookie is missing or its signature is wrong."""
    for part in cookie_header.split(";"):
        name, _, value = part.strip().partition("=")
        if name == "session" and "." in value:
            customer_id, signature = value.split(".", 1)
            expected = hmac.new(os.environ["SESSION_KEY"].encode(), customer_id.encode(), hashlib.sha256).hexdigest()
            if hmac.compare_digest(signature, expected):
                return int(customer_id)
    return None
