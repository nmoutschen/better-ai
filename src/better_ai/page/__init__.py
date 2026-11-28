"""The live page: one server, one conversation log and one set of verbs for every skill.

A page talks to the agent through `conversation.jsonl` in its unit. `serve` shows the page, takes what the user sends and
runs the agent that works on it (the driver, `driver.py`): the user's comments reach that agent with no chat input. The
agent answers with `reply` and `status` and lists what is still open with `pending`. The verbs are registered here for
every skill; what differs between skills is a `PageSpec`, which the skill's package registers with
`register(SKILL, PageSpec(...))` when it is imported:

- `title`, `agent`: the page's title, and the agent's role name (such as "coordinator"), which the shared "closed" strip
  and the thread say;
- `main`: the bundled HTML of the page's main section (a name under `better_ai/`, such as "research/board.html");
- `aside`: optional bundled HTML put at the top of the side column, above the conversation;
- `assets`, `css`, `js`: the fixed table of files the page serves, by URL path (`{"/board.js": "research/board.js"}`),
  and which of them the shell links; no other path is served;
- `capabilities`: the shared parts of the page it uses, from CAPABILITIES; the server accepts the events of those and
  refuses any other (so `approve` only on a page that declares it);
- `methods`, `items`: events a page may send that no capability names, and the events the agent tracks with a status
  (by default: notes, and the events of the declared capabilities that ask for an answer);
- `events`: the file name of the page's own events schema, in its package's `schemas/` folder;
- `load(unit)`: the page's data, a JSON object, served at `/data` (with `now` and `quiet_after` added);
- `rendered`, `static_data(unit, run)`: the `render` verb writes the page as one static file, `rendered` (a path
  in the unit; it prints the file's path), with `static_data` (default: `load`) embedded; the hook may refuse, warn on `run.err` or write other
  files first (the architect's SVGs);
- `revision(unit)`, `stopped(unit)`, `tick(unit, conversation)`: optional. A page reloads itself when `/rev` changes;
  `serve` ends `--linger` seconds after `stopped` becomes true; `tick` runs every TICK seconds (one) while serving.

`serve` is always driven: it finds the user's harness, opens a session in it, opens the page in the browser with a
single-use pairing token that it never prints or writes, prints one `driver:` line and detaches. Where the driver cannot
start it prints `driver: off <kind>: <problem>` and serves nothing. A tab pairs once (`/pair`), and the secret it gets
goes in the `X-Page-Token` header of `/rpc`, `/data`, `/events` and `/agent`. The shell, its files and `/alive` need none.

The shell (`shell.html`) is filled only with bundled files and `html.escape`d constants, never with record data.
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import hashlib
import html
import http.client
import http.server
import json
import os
import re
import select
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .. import cli, paths, resources, schema
from ..paths import Refused, Unit
from ..skill import Skill
from . import delivery
from .delivery import from_user as from_user

COMMON = "conversation.schema.json"
LOG, ADDRESS = "conversation.jsonl", ".server"
ACTIVE_DELIVERY = ".page-delivery"
TOKEN_HEADER = "X-Page-Token"
MAX_BODY = 200_000
TICK = 1  # seconds between the ticks of a served page; tests set it shorter
POLL = 0.05  # seconds serve_forever waits for a request before it looks whether it was told to stop
STATES = ("seen", "asked", "working", "done", "accepted")  # `accepted` is written as its own event, `accepted`
REPLY_STATES = ("done", "asked", "working")
FINISHED = ("done", "accepted")  # the states of an item that needs no more work, until a follow-up reopens it
BUG_TEXT = "The page hit a bug: ask the agent to restart it and report it"
QUIET_AFTER = timedelta(minutes=30)  # how long an agent at work may go without a record before its page says so
# What each shared capability lets the page send, and which of those events the agent tracks with a status.
CAPABILITIES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "pins": (("comment", "delete"), ("comment",)),  # numbered pins on the page, and taking a comment back
    "accept": (("accept", "reopen"), ()),  # the user accepts what the agent finished, or puts it back
    "decisions": (("answer",), ("answer",)),  # the user answers a decision question
    "confirm": (("confirm",), ("confirm",)),  # the user confirms a requirement in the wording shown
    "approve": (("approve",), ("approve",)),  # the user approves, or asks for a review again
}
CONTENT_TYPES = {
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
}
DRIVER_METHODS = ("permission_answer", "agent_stop", "agent_start")  # what /rpc hands to the driver, not to the log
SHARED_ASSETS = {"/page.js": "page/page.js", "/page.css": "page/page.css"}

# The driven shell and its srcdoc previews may run only bundled scripts.
DRIVEN_SHELL_POLICY = "; ".join(
    (
        "default-src 'none'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline' data: http: https:",
        "font-src 'self' data: http: https:",
        "img-src 'self' data: http: https:",
        "connect-src 'self'",
        "frame-src 'self' http: https:",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    )
)


class EventError(ValueError):
    """An event that fails its schema: the message is the validator's, `field: message` for each problem."""


@dataclass(frozen=True)
class PageSpec:
    """What a skill fills in the shared page; see the module's docstring."""

    title: str
    agent: str
    main: str
    load: Callable[[Unit], dict]
    events: str | None = None
    assets: Mapping[str, str] = field(default_factory=dict)
    css: tuple[str, ...] = ()
    js: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    methods: tuple[str, ...] = ()
    items: tuple[str, ...] | None = None
    empty: str | None = None
    rendered: str = "index.html"
    static_data: Callable[[Unit, cli.Run], Mapping[str, Any]] | None = None
    aside: str | None = None
    revision: Callable[[Unit], str] | None = None
    stopped: Callable[[Unit], bool] | None = None
    tick: Callable[[Unit, Conversation], None] | None = None
    triggers: Callable[[Unit], Iterable[dict]] | None = None

    def sendable(self) -> tuple[str, ...]:
        """The events the page may send: notes, and those of each capability and of `methods`."""
        return tuple(
            dict.fromkeys(["note", *(m for c in self.capabilities for m in CAPABILITIES[c][0]), *self.methods])
        )

    def tracked(self) -> tuple[str, ...]:
        """The events the agent tracks with a status."""
        if self.items is not None:
            return self.items
        return tuple(dict.fromkeys(["note", *(m for c in self.capabilities for m in CAPABILITIES[c][1])]))

    def table(self) -> dict[str, str]:
        """URL path to bundled file, for every file the page serves besides the shell."""
        return {**SHARED_ASSETS, **self.assets}


PAGES: dict[str, PageSpec] = {}
SERVE_GUARDS: dict[str, list[Callable[[Unit], None]]] = {}


def serve_guard(skill: str):
    """Register a check a skill makes before `serve` starts its page (discover-better: no page while a redact is half
    done). The function takes the `Unit` and raises `Refused` to refuse."""

    def register(function):
        SERVE_GUARDS.setdefault(skill, []).append(function)
        return function

    return register


def register(skill: Skill, spec: PageSpec) -> PageSpec:
    """Register a skill's page. A spec that names an unknown capability, an asset that is not in its table or has no known
    content type, or a bundled file that is not there is a bug in the source, found here and not by a user."""
    for name in spec.capabilities:
        if name not in CAPABILITIES:
            raise ValueError(f"{skill.name}: unknown page capability {name!r}")
    for url, name in spec.assets.items():
        if not url.startswith("/") or ".." in url or os.path.splitext(url)[1] not in CONTENT_TYPES:
            raise ValueError(f"{skill.name}: asset {url!r} is not a path with a known file type")
        if url in SHARED_ASSETS:
            raise ValueError(f"{skill.name}: asset {url!r} is the shared page's own")
        if not resources.exists(name):
            raise ValueError(f"{skill.name}: asset {url!r} names {name!r}, which is not bundled")
    for url in (*spec.css, *spec.js):
        if url not in spec.assets:
            raise ValueError(f"{skill.name}: {url!r} is linked but not in the asset table")
    if not resources.exists(spec.main):
        raise ValueError(f"{skill.name}: the main section {spec.main!r} is not bundled")
    if spec.aside and not resources.exists(spec.aside):
        raise ValueError(f"{skill.name}: the side section {spec.aside!r} is not bundled")
    PAGES[skill.name] = spec
    return spec


def spec_of(skill: Skill) -> PageSpec:
    spec = PAGES.get(skill.name)
    if spec is None:
        raise Refused(f"{skill.name} has no page")
    return spec


# ---------------------------------------------------------------- small helpers


def terminal_json(value) -> str:
    """JSON for a terminal: readable, and escaped where UTF-8 cannot hold a character (a lone surrogate), so printing
    it never fails."""
    text = json.dumps(value, ensure_ascii=False)
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return json.dumps(value)
    return text


def terminal_text(text: str) -> str:
    """Text a person gave (an id on the command line) as it can be printed: bytes UTF-8 cannot hold are escaped."""
    return text.encode("utf-8", "backslashreplace").decode("utf-8")


def now() -> str:
    """The time as an event records it: UTC, with Z."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _named_in(ident: Any, prefixes: tuple[str, ...]) -> str | None:
    """The agent an id carries after one of the prefixes: `analyst-2` in `E-analyst-2-3` for the prefix `E-`."""
    if isinstance(ident, str):
        for prefix in prefixes:
            rest = ident[len(prefix) :]
            if ident.startswith(prefix) and "-" in rest:
                return rest.rsplit("-", 1)[0]
    return None


def last_word(records: Iterable[Any], agent: str, id_prefixes: tuple[str, ...] = ()) -> datetime | None:
    """An agent's last word: the latest `at` among the records whose `by` is the agent, or None. Every page that says
    an agent has gone quiet reads it from here, and compares it with QUIET_AFTER. A board whose records another agent
    rewrites names the agent in the id too: with `id_prefixes` (`("E-", "S-")`), a record whose id is a prefix, the
    agent's name and a number counts as the agent's."""
    latest = None
    for record in records:
        if not isinstance(record, Mapping) or not isinstance(record.get("at"), str):
            continue
        if record.get("by") != agent and (not id_prefixes or _named_in(record.get("id"), id_prefixes) != agent):
            continue
        try:
            at = datetime.strptime(record["at"], schema.TIME).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if latest is None or at > latest:
            latest = at
    return latest


def last_words(records: Iterable[Any], agents: Iterable[str]) -> dict[str, str | None]:
    """Each agent's last word as a page's data gives it: the time in the form of `at`, or None."""
    records = list(records)
    found = {agent: last_word(records, agent) for agent in agents}
    return {agent: at.strftime(schema.TIME) if at else None for agent, at in found.items()}


def page_data(data: Mapping[str, Any]) -> dict:
    """What every page's data holds besides its own: `quiet_after`, the seconds of QUIET_AFTER."""
    return {**data, "quiet_after": int(QUIET_AFTER.total_seconds())}


def clean(value, depth=0):
    """Keep only JSON values a page can legitimately send, with long text cut, so the log stays readable."""
    if isinstance(value, str):
        return value[:5000]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if depth < 4 and isinstance(value, dict):
        return {str(k)[:100]: clean(v, depth + 1) for k, v in list(value.items())[:50]}
    if depth < 4 and isinstance(value, list):
        return [clean(v, depth + 1) for v in value[:50]]
    return None


def stop_like_ctrl_c() -> None:
    """Stop the server on SIGTERM or SIGHUP as on Ctrl+C, so `serve` still removes its address file when the harness
    ends the command or the terminal closes. A SIGKILL cannot be caught: `reply` checks the server instead."""

    def stop(signum, frame):
        raise KeyboardInterrupt

    for name in ("SIGTERM", "SIGHUP"):
        if hasattr(signal, name):  # Windows has no SIGHUP
            with contextlib.suppress(ValueError):  # a signal can only be set from the main thread
                signal.signal(getattr(signal, name), stop)


def rpc_error(rid, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def load_docs(skill: Skill) -> dict[str, dict]:
    """The schemas a run of this skill loads, shared and its own, loaded once per package."""
    return schema.docs_for(skill.package)


def old_format_count(unit: Unit, docs: dict[str, dict], cutoff: str | None) -> int:
    """How many lines of the unit are in the format before this change (kept as is): the one count a served page and a
    rendered page show. A unit that cannot be read counts none."""
    notices: list[schema.Error] = []
    with contextlib.suppress(OSError, Refused):
        schema.check_paths([unit.path], docs=docs, now=None, cutoff=cutoff, notices=notices)
    return len(notices)


OLD_NOTE = '<p class="oldnote" id="oldnote" role="status" hidden></p>'


def old_note_text(count: int) -> str:
    """The words of the count, the same as page.js writes on a served page."""
    noun = "record" if count == 1 else "records"
    return f"{count} {noun} in the format before this change: kept as is, not converted."


def with_old_note(unit: Unit, page_html: str) -> str:
    """A page written by `render`, with the unit's old-format count filled into it, so it shows without a script."""
    count = old_count_of(unit)
    if not count or OLD_NOTE not in page_html:
        return page_html
    return page_html.replace(OLD_NOTE, f'<p class="oldnote" id="oldnote" role="status">{old_note_text(count)}</p>', 1)


def old_count_of(unit: Unit) -> int:
    """`old_format_count` for a unit's own skill and this build's cutoff, for a page written by `render`."""
    return old_format_count(unit, load_docs(unit.skill), resources.build_info().cutoff)


# ---------------------------------------------------------------- the conversation


class Conversation:
    """One unit's log, `conversation.jsonl`, one ASCII JSON event per line, and the file that says where the unit is
    served (`.server`). Everything is read and written through `paths`, so no file is opened with a symlink on the
    way."""

    def __init__(self, unit: Unit, spec: PageSpec, docs: dict[str, dict]):
        self.unit, self.spec, self.docs = unit, spec, docs
        self.items, self.agent = spec.tracked(), spec.agent
        self.lock = threading.RLock()

    # ---------- The log ----------

    def lines(self) -> list:
        """The log's lines. Only "\\n" ends a line: events are ASCII JSON, so no other character can split one."""
        try:
            text = paths.read_bytes(self.unit, LOG).decode("utf-8", errors="replace")
        except FileNotFoundError:
            return []
        except OSError as error:
            raise self.file_error(error) from None
        return text.split("\n")[:-1]

    def file_error(self, error: OSError) -> Refused:
        """What a log that cannot be read or written (a folder, no permission) is: a refusal that names the file."""
        reason = error.strerror or type(error).__name__
        return paths.refusal(f"{self.unit.label}/{LOG}", f"cannot be used ({reason.lower()})", f"fix or remove {LOG}")

    def events(self) -> list:
        events = []
        for line in self.lines():
            try:
                event = schema.page_value(line)
            except ValueError:
                event = None
            events.append(
                event if isinstance(event, dict) else {}
            )  # keep the position, so indexes into the log stay right
        return events

    def check(self, event: dict) -> None:
        """Raise EventError, with the validator's message, unless the event meets the shared conversation schema and
        the page's own."""
        problems: list[tuple[str, str]] = []
        for name in [COMMON, *([self.spec.events] if self.spec.events else [])]:
            if name not in self.docs:
                raise schema.SchemaError(f"no schema named {name!r} among the loaded schemas")
            problems += [(p.field, p.message) for p in schema.validate_instance(event, self.docs[name], self.docs)]
        problems = list(dict.fromkeys(problems))
        if problems:
            raise EventError("; ".join(f"{field}: {message}" for field, message in problems))

    def append(self, *events: dict) -> list:
        """Check events, then write them to the log as ASCII JSON, so a character such as U+2028 in a message cannot
        split a line, in one `O_APPEND` write. None is written if one fails."""
        records = [{"type": e.get("type"), "at": now(), **e} for e in events]
        with self.lock:
            for record in records:
                self.check(record)
            lines = [json.dumps(record) for record in records]
            try:
                paths.append_line(self.unit, LOG, "".join(line + "\n" for line in lines).encode("ascii"))
            except OSError as error:
                raise self.file_error(error) from None
        return lines

    # ---------- The server's side ----------

    def wait_for_more(self, after: int, seconds: float) -> int:
        deadline = time.time() + seconds
        while len(self.lines()) <= after and time.time() < deadline:
            time.sleep(0.25)
        return len(self.lines())

    # ---------- The agent's side ----------

    def address(self) -> str | None:
        """The served address from `.server`, or None when the file is not there."""
        try:
            text = paths.read_bytes(self.unit, ADDRESS).decode("utf-8", errors="replace").strip()
        except FileNotFoundError:
            return None
        if not text.startswith("http://127.0.0.1:"):
            raise paths.refusal(
                f"{self.unit.label}/{ADDRESS}", "does not hold an address", "delete it and run serve again"
            )
        return text

    def answering(self) -> bool:
        """Whether a server answers at the address file's address: the file stays when the server is killed."""
        try:
            address = self.address()
            return address is not None and alive_at(address, 2) is not None
        except Refused:  # an address file that holds no address
            return False

    def delivery(
        self,
        after: int = 0,
        *,
        carry_ids: frozenset[str] = frozenset(),
        recover_ids: frozenset[str] = frozenset(),
        admitted_edits: set[tuple[str, str]] | None = None,
        thread_parents: dict[str, str] | None = None,
    ) -> delivery.Delivery:
        events = self.events()
        found = all_items(events, self.items, self.agent, thread_parents=thread_parents)
        return delivery.select(events, found, self.items, after, carry_ids, recover_ids, admitted_edits=admitted_edits)

    def write(self, *events: dict) -> list:
        """Append the agent's own events; one that fails its schema is refused with the validator's message."""
        try:
            return self.append(*events)
        except EventError as error:
            raise Refused(f"{self.unit.label}: the event is not valid: {error}") from None

    def known(self, ids: list, what: str = "no comment or message with id", started: bool = False) -> None:
        """Refuse ids that name no item of the user's; with `started`, a message the agent sent on its own is known too."""
        have = {
            e.get("id")
            for e in self.events()
            if e.get("type") in self.items or (started and e.get("type") == "reply" and not e.get("to"))
        }
        unknown = [i for i in ids if i not in have]
        if unknown:
            raise paths.refusal(
                self.unit.label,
                f"{what} {terminal_text(', '.join(unknown))}",
                f"run pending {self.unit.label} to see the ids",
            )

    def target_of(self, to: str) -> str:
        """The item whose status a reply under `to` sets: an answer under one of the user's items is part of it."""
        events = self.events()
        items = {e.get("id"): e for e in events if e.get("type") in self.items}
        owned = {i for i, e in items.items() if not (e.get("type") == "note" and e.get("to"))}
        return items[to].get("to") if to in items and to not in owned and items[to].get("to") in owned else to


# ---------------------------------------------------------------- the verbs


def _unit(args: argparse.Namespace, run: cli.Run) -> Unit:
    return paths.resolve_unit(args.unit, run.skill)


def _conversation(run: cli.Run, unit: Unit) -> Conversation:
    return Conversation(unit, spec_of(run.skill), load_docs(run.skill))


def _unit_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("unit", help="the unit whose page it is, such as .code/my-change")


def _text(run: cli.Run, what: str) -> str:
    text = run.stdin_text().strip()
    if not text:
        raise Refused(f"{what}: no text on stdin. Pipe the text in, such as `printf '%s' \"...\" | <command>`")
    return text


def _read_delivery_state(unit: Unit, name: str) -> dict:
    try:
        data = json.loads(paths.read_bytes(unit, name))
    except (OSError, ValueError, Refused):
        return {}
    return data if isinstance(data, dict) else {}


def _delivery_position(data: dict, key: str) -> int:
    position = data.get(key)
    return position if type(position) is int and position >= 0 else 0


def _delivery_ids(data: dict, key: str) -> frozenset[str]:
    ids = data.get(key)
    return frozenset(ids) if isinstance(ids, list) and all(isinstance(ident, str) for ident in ids) else frozenset()


def _reply_arguments(parser: argparse.ArgumentParser) -> None:
    _unit_argument(parser)
    parser.add_argument("--to", help="the id of the item it answers; the item's status is set in the same write")
    parser.add_argument(
        "--state",
        choices=REPLY_STATES,
        default="done",
        help="the status of the item it answers: done (default), asked when the reply asks the user back, or working",
    )
    parser.add_argument("--by", help="the agent's name, if not the page's role name")


@cli.verb(
    "reply",
    help="show a reply from the agent in the page; the text is on stdin",
    arguments=_reply_arguments,
)
def reply(args: argparse.Namespace, run: cli.Run) -> int:
    """Show the agent's reply in the page's conversation, under the item it answers. It works without a server, so a
    resumed run can answer what the user wrote while no agent was running."""
    unit = _unit(args, run)
    conv = _conversation(run, unit)
    by = paths.check_by(args.by) if args.by else conv.agent
    text = _text(run, f"{unit.label}: reply")[:5000]
    events = [{"type": "reply", "by": by, "id": "r-" + str(time.time_ns()), "text": text, "to": args.to}]
    if args.to is not None:
        target = conv.target_of(args.to)
        conv.known([target])
        events.append({"type": "status", "by": by, "to": target, "status": args.state})
    conv.write(*events)
    run.out("Reply shown in the page." if conv.answering() else "Reply saved; the page shows it when served.")
    return 0


def _status_arguments(parser: argparse.ArgumentParser) -> None:
    _unit_argument(parser)
    parser.add_argument("state", choices=STATES)
    parser.add_argument("ids", nargs="+", help="the ids of the user's items, or of a message the agent sent on its own")
    parser.add_argument("--text", action="store_true", help="read the user's words from stdin; needed for accepted")
    parser.add_argument("--by", help="the agent's name, if not the page's role name")


@cli.verb("status", help="mark the user's items seen, asked, working, done or accepted", arguments=_status_arguments)
def status(args: argparse.Namespace, run: cli.Run) -> int:
    """Mark the user's items as seen, asked, working or done. A message the agent sent on its own (`reply` without
    `--to`) waits for the user on the page until they answer it, or until it is marked done or accepted. Accepted
    records an acceptance the user gave in words, the same as the page's Accept button, as an `accepted` event with
    those words (on stdin, with `--text`)."""
    unit = _unit(args, run)
    if args.state == "accepted" and os.environ.get("BETTER_PAGE_SESSION"):
        raise paths.refusal(
            unit.label, "the page's agent cannot record an acceptance", "ask the user to press Accept in the page"
        )
    conv = _conversation(run, unit)
    by = paths.check_by(args.by) if args.by else conv.agent
    words = None
    if args.text:
        words = run.stdin_text().strip()
    if args.state == "accepted" and not words:
        raise paths.refusal(
            unit.label, "accepted needs the user's words that accept it", "pass them on stdin with --text"
        )
    events = conv.events()
    owned = {
        e.get("id") for e in events if e.get("type") in conv.items and not (e.get("type") == "note" and e.get("to"))
    }
    # An answer under one of the user's items is part of it; an answer to the agent's own message is an item.
    answers = {e.get("id"): e.get("to") for e in events if e.get("type") == "note" and e.get("to") in owned}
    misplaced = [i for i in args.ids if i in answers]
    if misplaced:  # an answer is part of the item it answers, which carries the state
        raise paths.refusal(
            unit.label,
            ", ".join(f"{terminal_text(i)} answers {terminal_text(answers[i])}" for i in misplaced),
            "mark the item it answers instead",
        )
    conv.known(args.ids, started=True)
    conv.write(
        *(
            {"type": "accepted", "by": by, "to": i, "text": words}
            if args.state == "accepted"
            else {"type": "status", "by": by, "to": i, "status": args.state}
            for i in args.ids
        ),
    )
    run.out(f"Marked {args.state}: {terminal_text(', '.join(args.ids))}")
    return 0


def open_items(events: list, item_types: tuple[str, ...], agent: str) -> list[tuple[dict, str, dict]]:
    """The user's items that are neither done nor accepted: `all_items` without the finished ones."""
    return [found for found in all_items(events, item_types, agent) if found[1] not in FINISHED]


def all_items(
    events: list, item_types: tuple[str, ...], agent: str, *, thread_parents: dict[str, str] | None = None
) -> list[tuple[dict, str, dict]]:
    """Every item of the user's, in its latest form, as (event, state, extra); `deleted` ones are left out. The state is
    `new`, `asked`, `working`, `replied`, `followup` or `reopened`; `extra` holds `reopened_because` and the `thread` of
    answers and replies under the item. These are the page's rules: page.js `pageThread` gives the same states, and
    tests/fixtures/threads.json holds the logs both are run on. `pending` and a skill's own summary both call these."""
    items, order, state, reasons, thread, closes = {}, [], {}, {}, {}, {}
    home = thread_parents if thread_parents is not None else {}
    for e in events:
        a, i = e.get("type"), e.get("id")
        to = home.get(e.get("to"), e.get("to"))  # a message under a reply belongs to the item that reply is under
        if a == "closed":  # a worker's message: the user can reply to it, and the reply goes to the agent
            closes[i] = e
        elif a == "note" and to and to not in items:  # an answer to the agent's own message is a new item
            order.append(i)
            items[i] = e
            if to in closes:  # the worker cannot read the page: say which question the user replied about
                c = closes[to]
                items[i] = {**e, "about": f"{c.get('by')} closed {c.get('question')} as {c.get('status')}"}
        elif a == "note" and to:  # the user's answer belongs to the item it answers
            thread.setdefault(to, []).append({"from": "user", "at": e.get("at"), "text": e.get("text")})
            if state.get(to) == "asked":  # the answer ends the wait: the item is the agent's again
                state[to] = "replied"
            elif state.get(to) in FINISHED:  # a follow-up under a finished item is work again
                state[to] = "followup"
            if i:
                home[i] = to
        elif a == "reply" and to:
            thread.setdefault(to, []).append({"from": agent, "at": e.get("at"), "text": e.get("text")})
            if i:
                home[i] = to
        elif a in item_types and i:  # an item sent again, such as an edited comment, keeps its state
            if i not in items:
                order.append(i)
            items[i] = e
        elif a == "delete" and to in items:
            items[to] = None
        elif a == "status":
            state[to] = e.get("status")
        elif a in ("accept", "accepted"):
            state[to] = "accepted"
        elif a == "reopen":
            state[to], reasons[to] = "reopened", e.get("text")
    found = []
    for e in (items[i] for i in order if items.get(i)):
        extra = {}
        if state.get(e["id"]) == "reopened" and reasons.get(e["id"]):
            extra["reopened_because"] = reasons[e["id"]]
        if thread.get(e["id"]):
            extra["thread"] = thread[e["id"]]
        found.append((e, state.get(e["id"], "new"), extra))
    return found


def _active_batch(conv: Conversation, active: dict) -> delivery.Delivery:
    sent = _delivery_ids(active, "item_ids")
    position, actions = active.get("position"), active.get("actions")
    if (
        type(position) is int
        and position >= 0
        and isinstance(actions, list)
        and all(isinstance(a, dict) for a in actions)
    ):
        events = conv.events()
        snapshot = events[:position]
        # Later user input belongs to a future turn. Only the agent's status
        # changes affect the full copy of items that this turn actually received.
        snapshot.extend(
            event for event in events[position:] if event.get("type") in ("status", "accepted") and not from_user(event)
        )
        items = [
            {**item, "status": state, **extra}
            for item, state, extra in all_items(snapshot, conv.items, conv.agent)
            if item["id"] in sent
        ]
        return delivery.Delivery(items, actions, position)
    # Older drivers did not capture a turn boundary or its non-item actions.
    return conv.delivery(
        _delivery_position(active, "after"),
        carry_ids=_delivery_ids(active, "carry_ids"),
        recover_ids=_delivery_ids(active, "recover_ids") | sent,
    )


@cli.verb("pending", help="list the user's actionable items and events", arguments=_unit_argument)
def pending(args: argparse.Namespace, run: cli.Run) -> int:
    """Read current item states and the events after the delivered position of the unit's `.driver`, including after an
    interruption."""
    unit = _unit(args, run)
    conv = _conversation(run, unit)
    session = os.environ.get("BETTER_PAGE_SESSION")
    active = _read_delivery_state(unit, ACTIVE_DELIVERY) if session else {}
    if session and active.get("session") == session:
        found = _active_batch(conv, active)
    else:
        found = conv.delivery(delivered_position(current_state(unit)))
    for event in [*found.items, *found.events]:
        run.out(terminal_json(event))
    run.out(f"{len(found.items)} not done.")
    return 0


# ---------------------------------------------------------------- the shell


def _json_for_html(value: Any) -> str:
    """JSON that sits in a <script> element: `<`, `>` and `&` escaped, so nothing in it can end the element."""
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def shell(spec: PageSpec, driven: bool = False) -> str:
    """The page: shell.html with the page's main section and bundled files, and constants escaped. Never record data."""
    title, agent = html.escape(spec.title), html.escape(spec.agent)
    empty = spec.empty or f"Nothing yet. Write to the {spec.agent} below."
    config = {"title": spec.title, "agent": spec.agent, "capabilities": list(spec.capabilities)}
    if driven:
        config["driven"] = True
    fills = {
        "%%TITLE%%": title,
        "%%AGENT%%": agent,
        "%%EMPTY%%": html.escape(empty),
        "%%STYLES%%": "\n".join(f'<link href="{html.escape(url)}" rel="stylesheet">' for url in spec.css),
        "%%SCRIPTS%%": "\n".join(f'<script src="{html.escape(url)}"></script>' for url in spec.js),
        "%%CONFIG%%": _json_for_html(config),
        "%%MAIN%%": resources.read_text(spec.main),
        "%%ASIDE%%": resources.read_text(spec.aside) if spec.aside else "",
    }
    text = resources.read_text("page/shell.html")
    # One pass over the shell, so a value that holds a marker is not filled in again.
    parts = text.split("%%")
    out = [parts[0]]
    for index in range(1, len(parts), 2):
        marker = f"%%{parts[index]}%%"
        out.append(fills.get(marker, marker))
        out.append(parts[index + 1] if index + 1 < len(parts) else "")
    return "".join(out)


def static_page(spec: PageSpec, data: Mapping[str, Any]) -> str:
    """The page as one file that opens without a server: the shell with each style sheet and script it links written
    into it, and `data`, what the page would fetch from /data, in a JSON element with the id `page-data`. What the user
    writes in it stays in the page; nothing reaches the agent."""
    text = shell(spec)
    for url in ("/page.css", *spec.css, "/page.js", *spec.js):
        body = resources.read_text(spec.table()[url])
        if url.endswith(".css"):
            if "</style" in body.lower():
                raise ValueError(f"{url} holds a closing tag that would end its element")
            tag, inline = f'<link href="{html.escape(url)}" rel="stylesheet">', f"<style>\n{body}\n</style>"
        else:
            script = body.replace("</", "<\\/")  # a script cannot end its own element
            tag, inline = f'<script src="{html.escape(url)}"></script>', f"<script>\n{script}\n</script>"
        if tag not in text:
            raise ValueError(f"the shell does not link {url}")
        text = text.replace(tag, inline, 1)
    config = '<script type="application/json" id="page-config">'
    return text.replace(
        config,
        f'<script type="application/json" id="page-data">{_json_for_html(page_data(data))}</script>\n{config}',
        1,
    )


# show-better has its own `render`: it checks a slide spec and prints text as well as a page.
@cli.verb(
    "render",
    help="write the unit's page as one static file, with its data in it, so it opens without a server",
    arguments=_unit_argument,
    # discover-better is live only: a static copy would keep words a redact removes.
    skills=("architect-better", "code-better", "design-better", "research-better"),
)
def render(args: argparse.Namespace, run: cli.Run) -> int:
    unit = _unit(args, run)
    spec = spec_of(run.skill)
    data = spec.static_data(unit, run) if spec.static_data else spec.load(unit)
    paths.write_atomic(unit, spec.rendered, with_old_note(unit, static_page(spec, data)).encode("utf-8"))
    run.out(str(unit.target(spec.rendered)))
    return cli.EXIT_DONE


# ---------------------------------------------------------------- the server


def answers_any_failure(handle):
    """A request handler that never raises: whatever the request makes it raise, the traceback with the skill and the
    source hash goes to the server's stderr, and the answer is one line with the status 500 (for a JSON-RPC request,
    the error object -32603 with the text the page shows), never a dropped request."""

    @functools.wraps(handle)
    def run(self):
        self.answer_started = False
        try:
            return handle(self)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.close_connection = True  # the client went away mid-request (a closed tab): nothing to answer, no trace
            return None
        except Refused as error:  # a file the page cannot use (a log that is a folder): the refusal's own words
            self.answer_failure(str(error), "500 Internal Server Error")
        except Exception as error:
            with contextlib.suppress(Exception):
                if SERVER_ERROR_SINK is not None:  # detached: one line in .driver.log in each rate window
                    SERVER_ERROR_SINK(f"{self.command} {self.path}: {''.join(traceback.format_exception(error))}")
                else:
                    print(f"page server: {self.bug_prefix}: {self.command} {self.path} failed", file=sys.stderr)
                    traceback.print_exception(error, file=sys.stderr)
                    sys.stderr.flush()
            self.answer_failure(BUG_TEXT, "500 Internal Server Error")
        return None

    return run


class Handler(http.server.BaseHTTPRequestHandler):
    """The requests a page makes. `make_server` subclasses it with the unit, the spec and the conversation."""

    unit: Unit
    spec: PageSpec
    conversation: Conversation
    methods: tuple = ()
    assets: dict
    bug_prefix = "bug"
    cutoff: str | None = None
    answer_started = False
    old_cache: tuple[float, int] = (0.0, 0)
    driven: DrivenPage

    def answer_failure(self, text: str, status: str) -> None:
        """Answer a failed request with one line, `text`: for a JSON-RPC request the error object -32603, else plain
        text with `status`. Written whole, without send_response or self.send, which may be what failed; if the
        connection is gone there is nothing more to answer."""
        if self.answer_started:  # the status line and headers are out: a second answer would corrupt the stream
            self.close_connection = True
            return
        self._headers_buffer = []
        if self.path == "/rpc":
            body = json.dumps(rpc_error(None, -32603, text)).encode()
            kind, status = "application/json", "200 OK"
        else:
            body, kind = f"{text}\n".encode(), "text/plain; charset=utf-8"
        head = f"HTTP/1.0 {status}\r\nContent-Type: {kind}\r\nContent-Length: {len(body)}\r\n\r\n"
        with contextlib.suppress(Exception):
            self.wfile.write(head.encode("ascii") + body)

    def flush_headers(self) -> None:
        super().flush_headers()
        self.answer_started = True

    def guarded(self, step) -> None:
        """Run a step of the request's life that is outside do_GET and do_POST (setup, handle, finish). A client that
        has gone, a reset or a closed socket, is not worth a word; anything else is one line, never a traceback."""
        try:
            step()
        except OSError:
            pass
        except Exception as error:
            with contextlib.suppress(Exception):
                print(f"page server: {self.bug_prefix}: a request failed: {type(error).__name__}", file=sys.stderr)

    def setup(self) -> None:
        self.request.settimeout(2)
        self.guarded(super().setup)

    def handle(self) -> None:
        self.guarded(super().handle)

    def local(self) -> bool:
        # Only answer requests addressed to this machine, so a web page cannot reach it via DNS rebinding.
        return (self.headers.get("Host") or "").rsplit(":", 1)[0] in ("127.0.0.1", "localhost")

    def browser_origin(self) -> bool:
        """Browsers omit Origin on same-origin GET. Fetch Metadata gives us the browser's origin check there."""
        origin = self.headers.get("Origin")
        expected = "http://" + (self.headers.get("Host") or "")
        return (origin is None or origin == expected) and self.headers.get("Sec-Fetch-Site") == "same-origin"

    def driven_token(self, pairing) -> bool:
        origin = "http://" + (self.headers.get("Host") or "")
        return self.browser_origin() and pairing.valid(self.headers.get(TOKEN_HEADER, ""), origin)

    def read_json(self):
        if not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return self.send_error(415)
        size = self.headers.get("Content-Length", "")
        if not size.isascii() or not size.isdecimal() or len(size) > 6 or not 0 < int(size) <= MAX_BODY:
            return self.send_error(413)
        return json.loads(self.rfile.read(int(size)))

    def pair(self, pairing, new_page=None, unauthorized=401):
        try:
            request = self.read_json()
            if request is None:
                return
            origin = "http://" + self.headers["Host"]
            secret = pairing.exchange(request.get("token", ""), origin) if isinstance(request, dict) else None
        except ValueError:
            secret = None
        if not secret:
            return self.send(unauthorized, b"Pairing link expired. Ask for a new link.", "text/plain")
        self.driven.paired.set()
        return self.send_json({"secret": secret, **({"page": new_page()} if new_page else {})})

    def send(self, code: int, body: bytes, kind: str, *, policy: str | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if policy:
            self.send_header("Content-Security-Policy", policy)
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, value) -> None:
        self.send(200, json.dumps(value).encode(), "application/json")

    def old_format_count(self) -> int:
        """The count every page shows, counted again at most every two seconds."""
        when, count = self.old_cache
        if time.time() - when < 2:
            return count
        count = old_format_count(self.unit, self.conversation.docs, self.cutoff)
        type(self).old_cache = (time.time(), count)
        return count

    def after(self, query: str) -> int:
        value = urllib.parse.parse_qs(query).get("after", ["0"])[0]
        return int(value) if value.isdigit() and len(value) <= 12 else 0  # a count, not a number past any log

    @answers_any_failure
    def do_GET(self):
        if not self.local():
            return self.send_error(403)
        parts = urllib.parse.urlsplit(self.path)
        path, c = parts.path, self.conversation
        driven = self.driven
        if not driven.main_host(self.headers.get("Host")):
            return self.send_error(403)
        if path == "/alive":
            return self.send_json(driven.alive())
        if path in ("/data", "/events", "/old", "/rev", "/agent") and not self.driven_token(driven.pairing):
            return self.send(403, b"Opened elsewhere. Ask for a new link.", "text/plain")
        if path == "/agent":
            return self.send_json(driven.status())
        if path in ("/", "/index.html"):
            return self.send(200, shell(self.spec, True).encode(), CONTENT_TYPES[".html"], policy=DRIVEN_SHELL_POLICY)
        if path in self.assets:
            kind = CONTENT_TYPES[os.path.splitext(path)[1]]
            return self.send(200, resources.read_bytes(self.assets[path]), kind)
        if path == "/data":
            return self.send_json(page_data({**self.spec.load(self.unit), "now": time.time()}))
        if path == "/old":
            return self.send_json(self.old_format_count())
        if path == "/rev":
            rev = self.spec.revision(self.unit) if self.spec.revision else "0"
            return self.send(200, str(rev).encode(), "text/plain")
        if path == "/events":
            # Long poll for the page: every event after the first `after`, the agent's included.
            after = self.after(parts.query)
            total = c.wait_for_more(after, 20)
            reply = {"total": total, "events": c.events()[after:total]}
            with driven.routing_lock:
                if not self.driven_token(driven.pairing):
                    return self.send(403, b"Opened elsewhere. Ask for a new link.", "text/plain")
                return self.send_json(reply)
        return self.send_error(404)

    @answers_any_failure
    def do_POST(self):
        with self.driven.routing_lock:
            self.post()

    def post(self):
        # Only this page may send: the same host and origin, and a JSON body that a cross-site form cannot send.
        origin = self.headers.get("Origin", "")
        if not self.local() or origin != "http://" + (self.headers.get("Host") or ""):
            return self.send_error(403)
        driven = self.driven
        if not driven.main_host(self.headers.get("Host")) or not self.browser_origin():
            return self.send_error(403)
        if self.path == "/pair":
            return self.pair(driven.pairing, unauthorized=403)
        if self.path != "/rpc":
            return self.send_error(404)
        if not self.driven_token(driven.pairing):
            return self.send(403, b"Opened elsewhere. Ask for a new link.", "text/plain")
        if not driven.driver or not driven.session:
            return self.send_error(503)
        try:
            msg = self.read_json()
        except ValueError:
            return self.send_json(rpc_error(None, -32700, "Parse error"))
        if msg is None and self.answer_started:
            return
        rid = msg.get("id") if isinstance(msg, dict) else None
        if (
            not isinstance(msg, dict)
            or msg.get("jsonrpc") != "2.0"
            or not isinstance(msg.get("method"), str)
            or not isinstance(msg.get("params"), dict)
        ):
            return self.send_json(rpc_error(rid, -32601, "Unknown method"))
        if msg["method"] in DRIVER_METHODS:
            try:
                return self.send_json(
                    {"jsonrpc": "2.0", "id": rid, "result": driven.control(msg["method"], msg["params"])}
                )
            except ValueError as error:
                return self.send_json(rpc_error(rid, -32602, str(error)))
        if msg["method"] not in self.methods:
            return self.send_json(rpc_error(rid, -32601, "Unknown method"))
        # The page sets only its own fields: the type is the method, the time is the server's, and "by" is the user's,
        # so a page cannot write an event as the agent's.
        params = clean(msg["params"])
        if "by" in params:
            return self.send_json(rpc_error(rid, -32602, "by: not allowed in what a page sends; the server sets it"))
        params = {k: v for k, v in params.items() if k not in ("type", "at")}
        try:
            (line,) = self.conversation.append({"type": msg["method"], "by": "user", **params})
        except EventError as error:
            return self.send_json(rpc_error(rid, -32602, str(error)))
        driven.driver.enqueue(json.loads(line))
        return self.send_json({"jsonrpc": "2.0", "id": rid, "result": "saved"})

    def finish(self) -> None:
        self.guarded(super().finish)
        self.driven.requests += 1

    def log_message(self, *args):
        pass


def make_server(unit: Unit, spec: PageSpec, conv: Conversation, info: resources.BuildInfo, port: int = 0):
    """The HTTP server for a unit's page, on 127.0.0.1; not started."""

    class PageHandler(Handler):
        pass

    PageHandler.unit, PageHandler.spec, PageHandler.conversation = unit, spec, conv
    PageHandler.methods, PageHandler.assets = spec.sendable(), spec.table()
    PageHandler.bug_prefix = f"{unit.skill.name} {info.hash}"
    PageHandler.cutoff = info.cutoff
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), PageHandler)
    server.handler = PageHandler
    return server


def unit_identity(unit: Unit) -> str:
    return hashlib.sha256(os.fsencode(unit.path)).hexdigest()


# ---------------------------------------------------------------- what `.driver` and the processes say


def current_state(unit: Unit) -> dict:
    """What the unit's `.driver` holds, `{}` when there is none or it is not the user's: the one place `serve` and the
    verbs read it."""
    from .driver_state import load_state

    return load_state(unit) or {}


def update_state(unit: Unit, **fields) -> None:
    """Set fields of `.driver` and keep the others, as the driver does."""
    from .driver_state import STATE, encode, write_private

    write_private(unit, STATE, encode({"version": 1, **current_state(unit), **fields}))


def delivered_position(state: dict) -> int:
    delivered = state.get("delivered")
    if isinstance(delivered, dict):
        delivered = delivered.get("position")
    return delivered if type(delivered) is int and delivered >= 0 else 0


def command_of(pid: Any) -> str | None:
    """The command line of a process, or None when there is none such."""
    if type(pid) is not int or pid <= 1:
        return None
    try:
        done = subprocess.run(
            ["ps", "-ww", "-o", "args=", "-p", str(pid)], capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout.strip() or None


def is_serve_of(pid: Any, unit: Unit) -> bool:
    """Whether the process is a `serve` of this unit: the word `serve` and then an argument that names the unit."""
    words = (command_of(pid) or "").split()
    if "serve" not in words:
        return False
    names = (str(unit.path), unit.label)
    return any(w in names or w.endswith("/" + unit.label) for w in words[words.index("serve") + 1 :])


def has_command(pid: Any, argv: Any) -> bool:
    """Whether the process runs this argument list, possibly behind an interpreter, which `ps` shows first."""
    command = command_of(pid)
    if not command or not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
        return False
    joined = " ".join(argv)
    return command == joined or command.endswith(" " + joined)


def process_gone(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return command_of(pid) is None  # a zombie that nobody has reaped yet


def end_process(pid: int, *, group: bool) -> None:
    """End a process, or its whole group, politely first."""
    send = os.killpg if group else os.kill
    for signum in (signal.SIGTERM, signal.SIGKILL):
        with contextlib.suppress(ProcessLookupError, PermissionError):
            send(pid, signum)
        for _ in range(20):
            if process_gone(pid):
                return
            time.sleep(0.05)


def alive_at(address: str, timeout: float) -> dict | None:
    """What a server's `/alive` says, or None when nothing answers there in time."""
    try:
        parsed = urllib.parse.urlsplit(address)
        if parsed.scheme != "http" or parsed.netloc != f"127.0.0.1:{parsed.port}" or parsed.path != "/":
            return None
        with contextlib.closing(http.client.HTTPConnection("127.0.0.1", parsed.port, timeout=timeout)) as connection:
            connection.request("GET", "/alive")
            reply = connection.getresponse()
            body = json.loads(reply.read(4096)) if reply.status == 200 else None
    except (OSError, ValueError, http.client.HTTPException):
        return None
    return body if isinstance(body, dict) else None


def served_address(unit: Unit) -> str | None:
    try:
        return paths.read_bytes(unit, ADDRESS).decode("utf-8", errors="replace").strip() or None
    except (OSError, Refused):
        return None


def server_answer(unit: Unit, timeout: float = 2) -> dict | None:
    """The `/alive` answer of this unit's recorded server, None when it does not answer, or answers for another unit."""
    address = served_address(unit)
    info = alive_at(address, timeout) if address else None
    return info if info and info.get("unit") == unit_identity(unit) else None


def live_server(unit: Unit) -> dict:
    """`.driver`, with the server's `/alive` answer under `alive`, when the unit's `.driver` names a `serve` of this unit
    that answers; `{}` otherwise."""
    state = current_state(unit)
    if not state:
        return {}
    info = server_answer(unit)
    if not info or not is_serve_of(state.get("server_pid"), unit):
        return {}
    return {**state, "alive": info}


# ---------------------------------------------------------------- what a chat agent's verbs say on a driven unit

WRITING = ("add", "set", "status", "reply", "create")  # the verbs a chat agent may not run on a driven unit
MACHINE_OUTPUT = ("pending", "render")  # the verbs whose output an agent reads as data: their notice goes to stderr
AGENT_STATE = {
    "idle": "this page's agent is idle since {}",
    "working": "this page's agent is working since {}",
    "waiting": "this page's agent is waiting for your approval since {}",
    "stopping": "this page's agent is stopping since {}",
    "stopped": "this page's agent is stopped since {}",
    "stalled": "this page's agent has stalled since {}",
    "failed": "this page's agent has failed since {}",
    "closed": "this page has closed since {}",
}


def notice_text(unit: Unit, state: dict) -> str:
    info = state["alive"]
    notice = (
        f"this page has its own agent (session {info.get('session')}); tell the user to use the page, "
        f"or run `link {unit.label}` to reopen it; do not work on this unit"
    )
    kind = "waiting" if info.get("waiting") else info.get("state")
    since = info.get("since")
    if kind in AGENT_STATE and isinstance(since, (int, float)):
        notice += "\n" + AGENT_STATE[kind].format(time.strftime("%H:%M", time.localtime(since)))
    return notice


def drive_guard(args: argparse.Namespace, run: cli.Run) -> int | None:
    """Before any verb on a unit with a live page: a caller that is not the page's agent is told so, and its writes are
    refused (exit 4)."""
    name = args._verb.name
    argument = getattr(args, "unit", None)
    if name in ("serve", "link") or not isinstance(argument, str):
        return None
    try:
        unit = paths.resolve_unit(argument, run.skill)
    except Refused:
        return None  # the verb itself says what is wrong with the unit
    if not unit.target(DRIVER).exists():
        return None
    state = live_server(unit)
    if not state or os.environ.get("BETTER_PAGE_SESSION") == state["alive"].get("session"):
        return None
    text = notice_text(unit, state)
    if name in WRITING:
        run.err(f"{run.skill.name}: {text}")
        return cli.EXIT_BUSY
    (run.err if name in MACHINE_OUTPUT else run.out)(text)
    return None


def log_page_verb(args: argparse.Namespace, run: cli.Run, code: int) -> None:
    """A verb run by the page's agent goes in `.driver.log`."""
    argument = getattr(args, "unit", None)
    if not os.environ.get("BETTER_PAGE_SESSION") or not isinstance(argument, str):
        return
    from .driver_state import log_verb

    with contextlib.suppress(Refused, OSError):
        unit = paths.resolve_unit(argument, run.skill)
        if unit.target(DRIVER).exists():
            log_verb(unit, args._verb.name, code)


cli.BEFORE_VERB.append(drive_guard)
cli.AFTER_VERB.append(log_page_verb)


# ---------------------------------------------------------------- the page's own server state


def run_http(server):
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": POLL}, daemon=True)
    thread.start()
    return thread


class DrivenPage:
    """What the handlers share with `serve`: the pairing, the approvals and the driver."""

    def __init__(self, server, unit, archive, record_verbs):
        from .approvals import ApprovalGate, Pairing

        self.server, self.unit = server, unit
        self.identity = unit_identity(unit)
        self.origin = f"http://127.0.0.1:{server.server_port}"
        self.driver = None
        self.ready = False
        self.child_argv: list[str] = []
        self.requests = 0  # the requests served, for `--once`
        self.paired = threading.Event()
        self.routing_lock = threading.RLock()
        self.pairing = Pairing(self.origin)
        self.gate = ApprovalGate(unit.path, archive=archive, record_verbs=record_verbs)
        server.handler.driven = self

    @property
    def session(self):
        return self.driver.session if self.ready else None

    def main_host(self, host):
        return host == self.origin.removeprefix("http://")

    def main_link(self):
        """The address that pairs one tab: its token is good once."""
        with self.routing_lock:
            return f"{self.origin}/#p={self.pairing.issue()}"

    def status(self):
        if self.driver and self.session:
            return {**self.driver.snapshot(), "harness": self.driver.harness, **self.available_controls()}
        return {"state": "starting", "age": 0}

    def alive(self):
        """What `/alive` says without the secret: enough for a verb to know the page has an agent and what it does."""
        info = {"unit": self.identity, "session": self.session}
        if not self.driver or not self.session:
            return {**info, "state": "starting", "mark_age": 0, "waiting": 0}
        snapshot = self.driver.snapshot()
        return {
            **info,
            "state": snapshot["state"],
            "since": snapshot.get("since"),
            "mark_age": snapshot["age"],
            "waiting": len(self.gate.snapshot()["approvals"]),
        }

    def available_controls(self):
        snapshot = self.driver.snapshot()
        live = snapshot["age"] <= 3 and snapshot.get("kind") != "driver"
        return {
            "can_start": bool(live and snapshot["state"] in ("stopped", "failed")),
            "can_stop": bool(live and snapshot["state"] in ("idle", "working", "stalled")),
        }

    def control(self, method, params):
        if not self.driver or not self.session or self.driver.snapshot()["age"] > 3:
            raise ValueError("The page's agent driver stopped. Ask the agent in your chat to serve this page again.")
        if method == "permission_answer":
            return self.gate.answer(params.get("id"), params.get("choice"))
        if method == "agent_stop" and self.available_controls()["can_stop"]:
            self.driver.request_stop()
            return True
        if method == "agent_start" and self.available_controls()["can_start"]:
            self.driver.request_start()
            return True
        raise ValueError("Unknown method")

    def close(self):
        if self.driver:
            self.driver.close()


LINK_SOCKET = ".page-link"


def link_existing(unit, conv):
    """Ask the live server over its private local control socket. Its path is not a browser credential."""
    from .driver_state import private_bytes

    address = conv.address()
    if not live_server(unit):
        raise Refused(f"{unit.label}: no driven page is running at {address or 'this unit'}")
    try:
        path = Path(private_bytes(unit, LINK_SOCKET).decode())
        if path.parent.parent != Path("/tmp") or not path.parent.name.startswith("better-page-") or path.name != "link":
            raise ValueError()
        with socket.socket(socket.AF_UNIX) as control:
            control.settimeout(2)
            control.connect(str(path))
            control.sendall(unit_identity(unit).encode())
            with control.makefile("rb") as stream:
                url = stream.readline(512).decode().strip()
            if not url.startswith("http://127.0.0.1:"):
                raise ValueError()
            return url
    except (OSError, ValueError):
        raise Refused(f"{unit.label}: could not pair a tab with the running server at {address}") from None


@contextlib.contextmanager
def link_control(driven):
    unit = driven.unit
    with (
        tempfile.TemporaryDirectory(prefix="better-page-", dir="/tmp") as folder,
        socket.socket(socket.AF_UNIX) as control,
    ):
        path = os.path.join(folder, "link")
        control.bind(path)
        os.chmod(path, 0o600)
        control.listen(4)
        control.settimeout(0.2)
        stopping = threading.Event()

        def serve_links():
            while not stopping.is_set():
                try:
                    connection, _ = control.accept()
                except TimeoutError:
                    continue
                except OSError:
                    return
                with connection:
                    connection.settimeout(0.2)
                    try:
                        with connection.makefile("rb") as stream:
                            identity = stream.read(64)
                        if identity == driven.identity.encode():
                            connection.sendall(driven.main_link().encode() + b"\n")
                    except OSError:
                        continue

        paths.write_state(unit, LINK_SOCKET, os.fsencode(path), 0o600)
        thread = threading.Thread(target=serve_links, daemon=True)
        thread.start()
        try:
            yield
        finally:
            stopping.set()
            thread.join(timeout=0.5)
            remove_if_ours(unit, LINK_SOCKET, os.fsencode(path))


def remove_if_ours(unit: Unit, name: str, value: bytes) -> None:
    with contextlib.suppress(OSError, Refused):
        if paths.read_bytes(unit, name) == value:
            unit.target(name).unlink()


@contextlib.contextmanager
def serve_lock(unit: Unit):
    fd = os.open(unit.target(".page-serve-lock"), os.O_RDWR | os.O_CREAT | paths.NOFOLLOW, 0o600)
    try:
        try:
            lock_unit(fd)
        except OSError:
            raise Refused("another serve of this unit is starting") from None
        yield
    finally:
        os.close(fd)


def lock_unit(fd: int) -> None:
    import fcntl

    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


# ---------------------------------------------------------------- serve

STUB = "BETTER_AI_STUB_HARNESS"  # set where a stub harness stands in for a real one: tests and tools/smoke.py
DRIVER, DRIVER_LOG = ".driver", ".driver.log"
START_TIMEOUT = 25  # seconds from the start of `serve` to its first line
CALLER_WAIT = 15  # seconds the calling process waits past START_TIMEOUT before it gives up on its server process
NOTE_WAIT = 2  # seconds `serve` reads the hand-off note from stdin
STALE_WAIT = 10  # seconds a server with a late liveness mark is given to exit
ERROR_WINDOW = 60  # seconds between two server_error lines in .driver.log
OFF_KINDS = (
    "no-harness",
    "login",
    "not-installed",
    "version",
    "state-version",
    "no-approvals",
    "no-browser",
    "crashed",
    "driver",
    "refused",
    "timeout",
)
SERVER_ERROR_SINK: Callable[[str], None] | None = None  # set after serve detaches: where an error a handler hit goes


class Off(Exception):
    """`serve` cannot go on: it prints `driver: off <kind>: <text>` and exits with `code`."""

    def __init__(self, kind: str, text: str, code: int = 1):
        super().__init__(text)
        self.kind, self.text, self.code = kind if kind in OFF_KINDS else "crashed", text, code

    def line(self) -> str:
        return f"driver: off {self.kind}: {' '.join(self.text.split())}"


class AlreadyServed(Off):
    """Not a failure: the page already has its server, so `serve` says so and exits 3."""

    def __init__(self, harness: str, session: Any):
        super().__init__("refused", "", 3)
        self.harness, self.session = harness, session

    def line(self) -> str:
        return f"driver: on {self.harness} {self.session} already"


def say_off(off: Off) -> None:
    print(off.line(), flush=True)


def _serve_arguments(parser: argparse.ArgumentParser) -> None:
    _unit_argument(parser)
    parser.add_argument("--port", type=int, default=0, help="port to serve on (default: any free port)")
    parser.add_argument("--no-browser", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--linger", type=float, default=10, help="seconds to keep serving after the unit stops")
    parser.add_argument("--once", action="store_true", help="serve one request, then exit")
    parser.add_argument("--link", action="store_true", help="pair a new tab with an already driven page")


@cli.verb(
    "serve",
    help="serve the unit's live page with its own agent; prints one driver: line, then the address, and detaches",
    arguments=_serve_arguments,
)
def serve(args: argparse.Namespace, run: cli.Run) -> int:
    """Check the unit, then start its page and the agent that works on it, and return once the page is served: the
    server goes on in its own session. Its first line is `driver: on <harness> <session>` or `driver: off <kind>: <what
    is wrong>`; where the driver cannot start nothing is served and the exit code is 1."""
    if args.link:
        unit = _unit(args, run)
        run.out(link_existing(unit, _conversation(run, unit)))
        return 0
    started = time.monotonic()
    try:
        if os.environ.get("BETTER_PAGE_SESSION"):
            raise Off("refused", "a page session never serves")
        if args.no_browser and not os.environ.get(STUB):
            raise Off("refused", "--no-browser is only for tests with a stub harness")
        try:
            unit = _unit(args, run)
            conv = _conversation(run, unit)
            state = current_state(unit)
            if type(state.get("version")) is int and state["version"] > 1:
                raise Off(
                    "state-version",
                    f"{unit.label}/{DRIVER} was written by a newer better-ai; update better-ai, or delete the file",
                )
            note = read_note(run)
            settle_old_server(unit, state)
            end_orphan(unit, state, run.info.hash)
            report_last_end(run, unit, state)
            refuse_repeat(unit, state, run.info.hash)
        except Refused as error:
            raise Off("refused", str(error)) from None
    except Off as off:
        say_off(off)
        return off.code
    if not run.detach:  # called from a program, not from the command line: serve here, and never open a browser
        return run_server(args, run, unit, conv, note, started + START_TIMEOUT, None)
    read_end, write_end = os.pipe()
    sys.stdout.flush()
    if (child := os.fork()) != 0:
        os.close(write_end)
        return wait_for_server(read_end, child, unit)
    os.close(read_end)
    code = 1
    try:
        os.setsid()
        code = run_server(args, run, unit, conv, note, started + START_TIMEOUT, write_end)
    except BaseException:
        traceback.print_exc()
    finally:
        with contextlib.suppress(Exception):
            sys.stdout.flush()
            sys.stderr.flush()
        os._exit(code)


def wait_for_server(read_end: int, child: int, unit: Unit) -> int:
    """The calling process's side of `serve`: it returns when its server process says it is done starting."""
    heard, spoke = b"", False
    deadline = time.monotonic() + START_TIMEOUT + CALLER_WAIT
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([read_end], [], [], remaining)[0]:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(child, signal.SIGKILL)
            if not spoke:
                print("driver: off timeout: the server process did not finish starting", flush=True)
            return 1
        data = os.read(read_end, 64)
        heard += data
        spoke = spoke or b"L" in heard
        done = re.search(rb"X(\d+)\n", heard)
        if done:
            return int(done.group(1))
        if not data:
            if not spoke:
                print(
                    f"driver: off crashed: the server process ended before it started; see {unit.label}/{DRIVER_LOG}",
                    flush=True,
                )
            return 1


def read_note(run: cli.Run) -> str:
    """The hand-off note on stdin, read to end of input for at most NOTE_WAIT seconds; empty when stdin is a terminal."""
    stream = run.stdin or sys.stdin
    notes: list[str] = []
    try:
        if stream.isatty():
            return ""
    except (OSError, ValueError):
        return ""

    def read():
        with contextlib.suppress(OSError, ValueError):
            notes.append(stream.read(64 * 1024))

    thread = threading.Thread(target=read, daemon=True)
    thread.start()
    thread.join(NOTE_WAIT)
    return notes[0] if notes else ""


def settle_old_server(unit: Unit, state: dict) -> None:
    """A server recorded for this unit: exit 3 when it is serving well, wait for one that is slow, end one that does not
    answer."""
    info = server_answer(unit)
    pid = state.get("server_pid") if type(state.get("server_pid")) is int and state["server_pid"] > 1 else 0
    if info is not None:
        age = info.get("mark_age")
        age = age if isinstance(age, (int, float)) else float("inf")
        if age < 3:
            raise AlreadyServed(state.get("harness") or "unknown", info.get("session"))
        if age <= STALE_WAIT:
            end = time.monotonic() + STALE_WAIT
            while time.monotonic() < end and server_answer(unit, 0.5) is not None and not (pid and process_gone(pid)):
                time.sleep(0.2)
    if type(pid) is int and not process_gone(pid) and is_serve_of(pid, unit):
        end_process(pid, group=False)
    address = served_address(unit)
    if address and server_answer(unit, 0.5) is None:
        remove_if_ours(unit, ADDRESS, address.encode())


def end_orphan(unit: Unit, state: dict, build: str) -> None:
    """The harness process a server of an earlier run left behind: ended, if it is the one `.driver` names."""
    pid = state.get("child_pid")
    if type(pid) is not int or pid <= 1 or not has_command(pid, state.get("child_argv")):
        return
    end_process(pid, group=True)
    from .driver_state import record_end

    record_end(unit, "orphan", "orphan", build)
    update_state(unit, child_pid=None)


def clock(moment: Any) -> str:
    """HH:MM, local, of an ISO time."""
    try:
        when = datetime.strptime(moment, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return "an unknown time"
    return when.astimezone().strftime("%H:%M")


def driver_error(state: dict) -> dict:
    ended = state.get("ended")
    return ended if isinstance(ended, dict) and ended.get("kind") == "driver" else {}


def report_last_end(run: cli.Run, unit: Unit, state: dict) -> None:
    ended = driver_error(state)
    if ended:
        run.err(f"the last session ended at {clock(ended.get('at'))}: {' '.join(str(ended.get('reason')).split())}")


def refuse_repeat(unit: Unit, state: dict, build: str) -> None:
    ended = driver_error(state)
    if type(ended.get("repeats")) is int and ended["repeats"] >= 2 and ended.get("build") == build:
        raise Off(
            "driver",
            f"the same error came back: {' '.join(str(ended.get('reason')).split())}; "
            f"see {unit.target(DRIVER_LOG)}; this is a better-ai problem",
        )


def ignore_driver_files(unit: Unit) -> None:
    """The unit folder's .gitignore lists the files only `better.pyz` reads, so a commit never takes them."""
    try:
        text = paths.read_bytes(unit, ".gitignore").decode("utf-8", errors="replace")
    except FileNotFoundError:
        text = ""
    listed = text.splitlines()
    missing = [name for name in (DRIVER, DRIVER_LOG) if name not in listed]
    if missing:
        gap = "" if not text or text.endswith("\n") else "\n"
        paths.write_atomic(unit, ".gitignore", (text + gap + "\n".join(missing) + "\n").encode())


def write_server_error(unit: Unit) -> Callable[[str], None]:
    """A function that adds one `server_error` line to .driver.log, at most one in each ERROR_WINDOW seconds."""
    last = [None]
    lock = threading.Lock()

    def write(text: str) -> None:
        with lock:
            if last[0] is not None and time.monotonic() - last[0] < ERROR_WINDOW:
                return
            last[0] = time.monotonic()
        line = {"type": "server_error", "at": time.time(), "text": text[-2000:]}
        with contextlib.suppress(OSError, Refused):
            paths.append_line(unit, DRIVER_LOG, (json.dumps(line, ensure_ascii=True) + "\n").encode("ascii"))

    return write


def detach(unit: Unit) -> None:
    """From here the server has no terminal: stdin is empty, and what it prints goes to .driver.log."""
    global SERVER_ERROR_SINK
    sys.stdout.flush()
    sys.stderr.flush()
    null = os.open(os.devnull, os.O_RDONLY)
    os.dup2(null, 0)
    os.close(null)
    log = os.open(unit.target(DRIVER_LOG), os.O_WRONLY | os.O_CREAT | os.O_APPEND | paths.NOFOLLOW, 0o600)
    os.dup2(log, 1)
    os.dup2(log, 2)
    os.close(log)
    write = write_server_error(unit)
    SERVER_ERROR_SINK = write

    def hook(kind, error, trace):
        write("".join(traceback.format_exception(kind, error, trace)))

    def thread_hook(info):
        hook(info.exc_type, info.exc_value, info.exc_traceback)

    sys.excepthook = hook
    threading.excepthook = thread_hook


def run_server(args, run, unit, conv, note, deadline, signal_fd) -> int:
    """The server process: start the page and its driver, say so to the caller, detach and serve until the unit stops."""
    server = driven = address = serving = None
    told = {"line": False, "done": False}

    detached = signal_fd is not None
    show_link = args.no_browser or not detached  # no browser: the paired address is printed for the caller

    def tell(text: str) -> None:
        run.out(text)
        if not told["line"]:
            told["line"] = True
            if detached:
                os.write(signal_fd, b"L")

    def finish(code: int) -> None:
        if not told["done"]:
            told["done"] = True
            if detached:
                os.write(signal_fd, f"X{code}\n".encode())
                os.close(signal_fd)

    if detached:
        stop_like_ctrl_c()
    try:
        step = "checking the unit"
        try:
            with serve_lock(unit):
                preflight(run, unit, conv)
                ignore_driver_files(unit)
                step = "starting the page server"
                try:
                    server = make_server(unit, spec_of(run.skill), conv, run.info, args.port)
                except OSError as error:
                    reason = (error.strerror or type(error).__name__).lower()
                    raise paths.refusal(
                        unit.label,
                        f"cannot be served on port {args.port} ({reason})",
                        f"serve {unit.label} on a free port",
                    ) from None
                address = f"http://127.0.0.1:{server.server_port}/".encode()
                archive = Path(sys.argv[0]).resolve() if run.info.hash != "source" else None
                driven = DrivenPage(server, unit, archive, ("add", "set"))
                serving = run_http(server)
                paths.write_state(unit, ADDRESS, address)
                link = driven.main_link()
                if not show_link:
                    step = "opening the browser"
                    if not webbrowser.open(link):
                        raise Off(
                            "no-browser", "could not open a browser on this machine; run serve where your browser runs"
                        )
                step = "finding the harness"
                wanted = find_harness()
                step = "checking the harness version"
                check_harness(wanted, unit, deadline)
                step = "starting the agent's session"
                start_driver(driven, wanted, conv, run, deadline, note, archive)
                if not show_link:
                    step = "pairing the page in the browser"
                    if not driven.paired.wait(max(0.0, deadline - time.monotonic())):
                        raise Off("timeout", step)
                record_server(unit, driven)
                tell(f"driver: on {wanted.name} {driven.session}")
                tell(f"Serving {unit.label} at {link if show_link else address.decode()}")
                finish(0)
                if detached:
                    detach(unit)
                with link_control(driven):
                    wait_until_done(args, run, unit, conv, driven)
        except Refused as error:
            raise Off("refused", str(error)) from None
        except (Off, KeyboardInterrupt):
            raise
        except Exception as error:
            if time.monotonic() >= deadline and not told["done"]:
                raise Off("timeout", step) from None
            raise Off("driver", f"{type(error).__name__}: {error}") from None
    except Off as off:
        stop_serving(server, serving, driven, unit, address)
        if off.kind == "driver":
            note_driver_error(unit, off.text, run.info.hash)
        drop_note(unit)
        off = Off(off.kind, with_log_path(unit, off), off.code)
        if not told["line"]:
            tell(off.line())
        finish(off.code)
        return off.code
    except KeyboardInterrupt:
        stop_serving(server, serving, driven, unit, address)
        if not told["line"]:
            tell(Off("crashed", "serve was stopped while it started").line())
        finish(1)
        return 0
    stop_serving(server, serving, driven, unit, address)
    return 0


def find_harness():
    from . import adapters

    found = adapters.candidate("auto", os.environ)
    if found.kind == "no-harness":
        raise Off("no-harness", found.text)
    if found.kind == "not-installed":
        raise Off("not-installed", f"{found.name} CLI not found on PATH")
    wanted = adapters.candidate(found.name, os.environ, chat_argv=adapters.chat_argv(found.name))
    if wanted.kind == "not-installed":
        raise Off("not-installed", f"{wanted.name} CLI not found on PATH")
    if wanted.kind is not None:
        raise Off(wanted.kind, wanted.text)
    if not wanted.codec_factory:
        raise Off(
            "no-approvals",
            f"{wanted.name} does not forward approval requests to better-ai; run serve from another harness",
        )
    return wanted


def record_server(unit: Unit, driven: DrivenPage) -> None:
    """Put this server, and the harness command it started, in `.driver` for the next serve and for the verbs."""
    fields: dict[str, Any] = {
        "server_pid": os.getpid(),
        "server_started": time.time(),
        "child_argv": driven.child_argv,
    }
    update_state(unit, **fields)


def drop_note(unit: Unit) -> None:
    """A serve that gives `driver: off` leaves no hand-off note behind."""
    from .driver_state import STATE, encode, write_private

    state = current_state(unit)
    if "note" in state:
        del state["note"]
        with contextlib.suppress(OSError, Refused):
            write_private(unit, STATE, encode(state))


def with_log_path(unit: Unit, off: Off) -> str:
    return f"{off.text}; see {unit.target(DRIVER_LOG)}" if off.kind == "driver" else off.text


def note_driver_error(unit: Unit, text: str, build: str) -> None:
    """Record a driver error that ended a serve."""
    from .driver_state import record_end

    with contextlib.suppress(OSError, Refused):
        record_end(unit, "driver", text, build)


def stop_serving(server, serving, driven, unit: Unit, address) -> None:
    """End the harness's process group, close the server and take the address file away if it is still ours."""
    if driven:
        driven.close()
    if server is not None:
        if serving is not None:
            server.shutdown()
        server.server_close()
    if address:
        remove_if_ours(unit, ADDRESS, address)


def preflight(run, unit, conv):
    for guard in SERVE_GUARDS.get(run.skill.name, []):
        guard(unit)
    notices: list[schema.Error] = []
    for error in schema.check_paths(
        [unit.path], docs=conv.docs, now=run.now(), cutoff=run.info.cutoff, notices=notices
    ):
        run.err(f"warning: {error}")
    for notice in notices:
        run.err(f"notice: {notice}")
    conv.lines()  # a log that cannot be read is refused here, not found by the first request


def check_harness(candidate, unit: Unit, deadline: float) -> None:
    from .adapters import version_problem, version_supported

    try:
        version = subprocess.run(
            [candidate.argv[0], "--version"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=max(0.1, deadline - time.monotonic()),
            check=False,
            cwd=unit.root,
        )
    except subprocess.TimeoutExpired:
        raise Off("timeout", "checking the harness version") from None
    except FileNotFoundError:
        raise Off("not-installed", f"{candidate.name} CLI not found on PATH") from None
    if version.returncode or not version_supported(candidate.name, version.stdout):
        raise Off("version", version_problem(candidate.name, version.stdout))


def start_driver(driven, candidate, conv, run, deadline, note, archive) -> None:
    from .adapters import child_environment, session_id_valid
    from .driver import Driver, StartError
    from .transport import ProcessTransport

    env = os.environ.copy()

    def launch(tag, resume):
        driven.child_argv = list(candidate.command(tag, resume))
        return ProcessTransport(
            candidate.command(tag, resume),
            conv.unit.root,
            child_environment(candidate.name, env, tag),
            lambda send: candidate.codec(send, tag, resume),
        )

    skill_path = (
        archive.parent.parent / "SKILL.md"
        if archive
        else (Path(__file__).resolve().parents[3] / "skills" / run.skill.name / "SKILL.md")
    )
    try:
        head = json.loads(paths.read_bytes(conv.unit, conv.unit.kind.head))
        step = head.get("step", "") if isinstance(head, dict) else ""
    except (OSError, ValueError, Refused):
        step = ""
    driven.driver = Driver(
        conv,
        candidate.name,
        launch,
        skill_path=skill_path,
        command=shlex.join((os.path.abspath(sys.executable), str(archive or sys.argv[0]))),
        cwd=conv.unit.root,
        step=step if isinstance(step, str) else "",
        handoff=note,
        triggers=lambda: conv.spec.triggers(conv.unit) if conv.spec.triggers else (),
        approvals=driven.gate,
        valid_session=lambda session: session_id_valid(candidate.name, session),
    )
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise Off("timeout", "starting the agent's session")
    try:
        driven.driver.start(remaining)
    except StartError as error:
        if time.monotonic() >= deadline:
            raise Off("timeout", "starting the agent's session") from None
        if error.kind == "login":
            raise Off("login", f"log in to {candidate.name} in a terminal, then run serve again") from None
        raise Off(error.kind, str(error)) from None
    driven.ready = True


def wait_until_done(args, run, unit, conv, driven) -> None:
    """Serve until the unit stops (`--once`: until one request has been answered)."""
    spec = spec_of(run.skill)
    stopped_at = None
    while True:
        time.sleep(TICK if not args.once else POLL)
        if args.once:
            if driven.requests >= 1:
                return
            continue
        try:
            if spec.tick:
                spec.tick(unit, conv)
            stopped = bool(spec.stopped and spec.stopped(unit))
            if stopped:
                stopped = driven.driver.can_linger()
        except Exception as error:
            run.err(f"page server: tick failed: {type(error).__name__}: {error}")
            continue
        if stopped_at is None and stopped:
            stopped_at = time.monotonic()
        if not stopped:
            stopped_at = None
        if stopped_at is not None and time.monotonic() - stopped_at > args.linger:
            run.out("The unit stopped; the page server is exiting. The open page keeps the last state.")
            return


def revision_of(*parts: Any) -> str:
    """A short hash of what a page reloads on, for a spec's `revision`."""
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:16]


__all__ = [
    "BUG_TEXT",
    "CAPABILITIES",
    "Conversation",
    "EventError",
    "PageSpec",
    "make_server",
    "publish",
    "old_count_of",
    "with_old_note",
    "old_format_count",
    "register",
    "revision_of",
    "shell",
    "spec_of",
    "static_page",
]
