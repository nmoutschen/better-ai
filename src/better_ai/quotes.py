"""The check of a quote against the page a verifier read, shared by the skills whose verifiers check quotes.

A verifier saves the text it read to a file and passes it to `set` with `--raw <file>`. `check_read` refuses unless
each passage of the span the verifier copied occurs in that file, and the quote occurs in one passage, and it returns the
file's `sha256` for the record to keep. It makes no network call and reads no file but that one.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

from . import paths, records


def normalise(text: str) -> str:
    """The words of `text` for comparing: lower case, punctuation and runs of whitespace as one space."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"[\W_]+", " ", folded).strip()


def quote_in_span(quote: str, span: str) -> bool:
    """The quote's words occur in the span as whole words, after whitespace and punctuation are normalised."""
    words = normalise(quote)
    return bool(words) and f" {words} " in f" {normalise(span)} "


def _spaced(text: str) -> str:
    """`text` with each run of whitespace as one space: a passage copied on one line matches a page that wraps it."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def raw_text(ctx: records.SetContext, then: str) -> tuple[str, str]:
    """The text of the file given with `--raw`, and its sha256. `then` says where to save the page when none was
    given. A file inside the unit is refused: the records themselves hold the quote."""
    if ctx.raw is None:
        raise paths.refusal(ctx.unit.label, "this needs the page the verifier read", then)
    ctx.raw_read = True
    path = Path(ctx.raw)
    try:
        if not path.is_file():
            raise OSError("not a file")
        inside = path.resolve().is_relative_to(Path(ctx.unit.path).resolve())
        data = path.read_bytes()
    except OSError as error:
        raise paths.refusal(
            ctx.unit.label, f"cannot read --raw {ctx.raw} ({error})", "give the file the verifier saved"
        ) from None
    if inside:
        raise paths.refusal(ctx.unit.label, f"--raw {ctx.raw} is inside {ctx.unit.label}", then)
    return data.decode("utf-8", "replace"), hashlib.sha256(data).hexdigest()


def check_read(ctx: records.SetContext, passages: list[str], quote: object, then: str) -> str:
    """Refuse unless each passage occurs in the `--raw` file (whitespace aside) and the quote occurs within one
    passage; return the file's sha256. `then` is as for `raw_text`."""
    text, digest = raw_text(ctx, then)
    page = _spaced(text)
    for passage in passages:
        if not _spaced(passage) or _spaced(passage) not in page:
            raise paths.refusal(
                ctx.unit.label,
                f"the span does not occur in {ctx.raw}: {passage[:80]!r}",
                "copy the span from the saved page exactly, or set the outcome that says why you could not",
            )
    if not isinstance(quote, str) or not any(quote_in_span(quote, passage) for passage in passages):
        raise paths.refusal(
            ctx.unit.label,
            "the quote does not occur in the span",
            'copy the part of the page that holds the quote, or set unverified with the reason "reworded"',
        )
    return digest
