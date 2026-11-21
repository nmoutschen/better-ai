import hashlib
import hmac

from shop.auth import customer_from_cookie


def test_valid_cookie(monkeypatch):
    monkeypatch.setenv("SESSION_KEY", "k")
    sig = hmac.new(b"k", b"7", hashlib.sha256).hexdigest()
    assert customer_from_cookie(f"session=7.{sig}") == 7


def test_bad_signature(monkeypatch):
    monkeypatch.setenv("SESSION_KEY", "k")
    assert customer_from_cookie("session=7.abc") is None
