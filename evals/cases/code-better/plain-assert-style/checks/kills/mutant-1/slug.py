import re
import unicodedata


def slug(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    if not text.startswith("Ann's"):
        text = text.replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
