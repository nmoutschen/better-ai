"""show-better's commands and page: `render` (a page, text or Markdown), the `check` digest, and the live page."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

from .. import cli, page, paths, resources, schema
from ..paths import Unit, refusal
from . import deck

HEAD = "spec.json"
PAGE = "page.html"
SLIDES_LOCK = threading.Lock()  # the drawing keeps one list of cut labels: one spec is drawn at a time


class Examined(NamedTuple):
    """A unit's spec, checked: the problems as `<file>:<line>: <field>: <reason>` lines, and (when there are none) the
    spec without its nulls, the warnings and the digest."""

    errors: list[str]
    spec: dict | None
    warnings: list[str]
    digest: list[str]


def _shown(unit: Unit) -> Path:
    shown = os.path.relpath(unit.path)
    return Path(shown if not shown.startswith("..") else unit.path) / HEAD


def examine(unit: Unit, now: datetime, cutoff: str) -> Examined:
    """Read `spec.json` and check it: its schema (a spec from before `at` and `by` is the old format, kept as is), and
    what the drawing knows. Whatever the file holds, the answer is lines; an exception of our own code is a bug, not a
    line."""
    where = _shown(unit)
    try:
        text = paths.read_bytes(unit, HEAD).decode("utf-8")
    except FileNotFoundError:
        raise refusal(unit.label, f"it has no {HEAD}", f"create it: create {unit.label} --by <name>") from None
    except UnicodeDecodeError:
        return Examined([f"{where}:1: (record): is not UTF-8 text"], None, [], [])
    old: list[schema.Error] = []
    found = schema.check_text(where, text, schema.docs_for("show"), {}, now=now, cutoff=cutoff, notices=old)
    if found:
        return Examined([str(e) for e in found], None, [], [])
    spec = deck.without_nulls(json.loads(text))
    if old:
        # A spec in the old format is not an error for what it lacks, but the checks across its panels still apply to
        # it: they run on the spec with the fields it lacks filled in. A spec in the new format had them in check_text.
        stamped = {**spec, "type": "slides", "at": "2000-01-01T00:00:00Z", "by": "old"}
        errors = [f"{f}: {m}" for f, m in dict.fromkeys(deck.spec_problems(stamped))]
        if errors:
            return Examined([f"{where}:1: {e}" for e in errors], None, [], [])
    errors, warnings, digest = deck.inspect(spec)
    return Examined([f"{where}:1: {e}" for e in errors], None if errors else spec, warnings, digest)


def _report(run: cli.Run, seen: Examined) -> None:
    for line in seen.errors:
        run.out(line)
    for warning in seen.warnings:
        run.err(f"warning: {warning}")


@cli.check_step("show-better")
def check_step(unit: Unit, run: cli.Run) -> int:
    """The digest of every value the slides show, the warnings, and what only the drawing knows."""
    seen = examine(unit, run.now(), run.info.cutoff)
    _report(run, seen)
    if seen.digest:
        run.out("\n".join(seen.digest))
    return 1 if seen.errors else 0


# ---------------------------------------------------------------- render


def _render_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("unit", help="the slides, such as .show/my-slides")
    parser.add_argument(
        "--format",
        choices=("html", "text", "md"),
        default="html",
        help="html: write the page into the unit; text: plain text for a terminal; md: Markdown with text diagrams in "
        "code blocks",
    )
    parser.add_argument("--width", type=int, default=72, help="text width in characters (text and md)")
    parser.add_argument("--ascii", action="store_true", help="use only ASCII characters (text and md)")
    parser.add_argument(
        "--screen-reader",
        action="store_true",
        help="text only: sentences and value lists, without box drawing, bars or rules that a screen reader reads aloud",
    )


@cli.verb(
    "render",
    help="check the spec, then write the page into the unit (html) or print the slides as text (text, md)",
    arguments=_render_arguments,
    skills=("show-better",),
    machine_output=True,
)
def render(args: argparse.Namespace, run: cli.Run) -> int:
    unit = paths.resolve_unit(args.unit, run.skill)
    if args.screen_reader and args.format != "text":
        raise refusal(unit.label, "--screen-reader works with --format text", "add --format text")
    seen = examine(unit, run.now(), run.info.cutoff)
    _report(run, seen)
    if seen.errors:
        return cli.EXIT_REFUSED
    spec = seen.spec
    if args.format == "html":
        paths.write_atomic(unit, PAGE, page.with_old_note(unit, deck.render(spec)).encode("utf-8"))
        run.out(f"wrote {unit.path.resolve() / PAGE}")
        return cli.EXIT_DONE
    if args.screen_reader:
        text = deck.render_screen_reader(spec, args.width)
    else:
        text = deck.render_text(spec, args.width, args.ascii, args.format == "md")
    (run.stdout or sys.stdout).write(text)
    return cli.EXIT_DONE


# ---------------------------------------------------------------- the live page


def load(unit: Unit) -> dict:
    """What `/data` serves: the slides drawn from the unit's spec, or the spec's errors."""
    info = resources.build_info()
    with SLIDES_LOCK:
        seen = examine(unit, datetime.now(timezone.utc), info.cutoff)
        if seen.errors:
            return {"errors": seen.errors}
        spec = seen.spec
        return {
            "title": spec["title"],
            "question": spec.get("question"),
            "lang": spec.get("lang") or "en",
            "style": deck.style_css(spec),
            "slides": deck.slides_html(spec),
        }


def revision(unit: Unit) -> str:
    """The page reloads when the spec changes."""
    try:
        return page.revision_of(hashlib.sha256(paths.read_bytes(unit, HEAD)).hexdigest())
    except FileNotFoundError:
        return page.revision_of("missing")


PAGE_SPEC = page.PageSpec(
    title="Slides",
    agent="agent",
    main="show/main.html",
    load=load,
    revision=revision,
    events="show-events.schema.json",
    assets={"/show.css": "show/show.css", "/show.js": "show/show.js"},
    css=("/show.css",),
    js=("/show.js",),
    capabilities=("pins", "accept"),
    empty="Nothing yet. Switch to Comment and click any part of a slide to comment on it, or write to the agent below.",
)
