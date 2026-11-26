"""The live page: one server, one conversation log and one set of verbs for every skill.

A page talks to the agent through `conversation.jsonl` in its unit. `serve` shows the page and takes what the user sends;
the agent reads it with `wait`, answers with `reply` and `status`, and lists what is still open with `pending`. The five
verbs are registered here for every skill; what differs between skills is a `PageSpec`, which the skill's package
registers with `register(SKILL, PageSpec(...))` when it is imported:

- `title`, `agent`: the page's title, and the agent's role name (such as "coordinator"), which the shared "not watching" and
  "closed" strips and the thread say;
- `main`: the bundled HTML of the page's main section (a name under `better_ai/`, such as "research/board.html");
- `aside`: optional bundled HTML put at the top of the side column, above the conversation;
- `assets`, `css`, `js`: the fixed table of files the page serves, by URL path (`{"/board.js": "research/board.js"}`),
  and which of them the shell links; no other path is served;
- `capabilities`: the shared parts of the page it uses, from CAPABILITIES; the server accepts the events of those and
  refuses any other (so `approve` only on a page that declares it);
- `methods`, `items`: events a page may send that no capability names, and the events the agent tracks with a status
  (by default: notes, and the events of the declared capabilities that ask for an answer);
- `events`: the file name of the page's own events schema, in its package's `schemas/` folder;
- `load(unit)`: the page's data, a JSON object, served at `/data` (with `listening`, `now` and `quiet_after` added);
- `rendered`, `static_data(unit, run)`: the `render` verb writes the page as one static file, `rendered` (a path
  in the unit; it prints the file's path), with `static_data` (default: `load`) embedded; the hook may refuse, warn on `run.err` or write other
  files first (the architect's SVGs);
- `revision(unit)`, `stopped(unit)`, `tick(unit, conversation)`: optional. A page reloads itself when `/rev` changes;
  `serve` ends `--linger` seconds after `stopped` becomes true; `tick` runs every TICK seconds (one) while serving.

`serve` makes a random token, keeps it in the unit's `.server-token` (private to the user) and gives it to the browser
only in the fragment of the address it opens (`#t=...`, which a browser does not send). `/rpc`, `/data`, `/events` and
`/wait` need it in the `X-Page-Token` header; `wait` reads it from the file. The shell, its files and `/listening` do not.

The shell (`shell.html`) is filled only with bundled files and `html.escape`d constants, never with record data.
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import hashlib
import hmac
import html
import http.client
import http.server
import json
import os
import secrets
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
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeout
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
LOG, SEEN, ADDRESS, TOKEN = "conversation.jsonl", ".conversation-seen", ".server", ".server-token"
WAIT_RECEIPT = ".page-wait"
ACTIVE_DELIVERY = ".page-delivery"
TOKEN_HEADER = "X-Page-Token"
OUT_OF_DATE = "page out of date: open the address the agent gave"  # what a page without the token is told; page.js shows it and keeps the typing
MAX_BODY = 200_000
LISTEN_GAP = 10  # seconds without a `wait` connected before the page says the agent is not watching
WAIT_DEFAULT = 600  # seconds `wait` waits, in every skill
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
    if skill.name not in PAGES:
        paths.unit_guard(skill.name)(driven_notice)
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
    """One unit's log, `conversation.jsonl`, one ASCII JSON event per line, and the files that say where the unit is
    served (`.server`) and what fallback wait handed back (`.page-wait`). Everything is read and written through
    `paths`, so no file is opened with a symlink on the way."""

    def __init__(self, unit: Unit, spec: PageSpec, docs: dict[str, dict]):
        self.unit, self.spec, self.docs = unit, spec, docs
        self.items, self.agent = spec.tracked(), spec.agent
        self.lock = threading.RLock()
        # Whether a `wait` is listening: None until one first connects (the agent may stream the server's output
        # instead), then True while one is connected or reconnected within LISTEN_GAP seconds. The page warns the user
        # when it is False.
        self.waiters: dict[str, Any] = {"open": 0, "last": None}

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

    def listening(self):
        if self.waiters["last"] is None:
            return None
        return self.waiters["open"] > 0 or time.time() - self.waiters["last"] < LISTEN_GAP

    def wait_for_more(self, after: int, seconds: float) -> int:
        deadline = time.time() + seconds
        while len(self.lines()) <= after and time.time() < deadline:
            time.sleep(0.25)
        return len(self.lines())

    def waited(self, after: int, seconds: float = 25) -> int:
        """Long poll for `wait`: the number of events, as soon as there are more than `after`."""
        with self.lock:
            self.waiters["open"] += 1
            self.waiters["last"] = time.time()
        try:
            return self.wait_for_more(after, min(seconds, 25))
        finally:
            with self.lock:
                self.waiters["open"] -= 1
                self.waiters["last"] = time.time()

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
            if address is None:
                return False
            with urllib.request.urlopen(f"{address}listening", timeout=2):
                return True
        except (OSError, ValueError, Refused):  # no server there, or an address file that holds no address
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


def _wait_arguments(parser: argparse.ArgumentParser) -> None:
    _unit_argument(parser)
    parser.add_argument("--timeout", type=float, default=WAIT_DEFAULT, help=f"seconds to wait (default {WAIT_DEFAULT})")


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


def _wait_total(address: str, after: int, seconds: float, headers: dict, unit: Unit) -> int:
    request = urllib.request.Request(f"{address}wait?after={after}&seconds={max(1, int(seconds))}", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return int(response.read())
    except urllib.error.HTTPError as error:
        if error.code == 401:
            raise paths.refusal(
                unit.label, "the page's server does not accept this token", f"run serve {unit.label} again"
            ) from None
    except (OSError, ValueError):
        pass
    raise paths.refusal(unit.label, "the page's server is not answering", f"run serve {unit.label} again")


@cli.verb(
    "wait", help="wait for the user's next actions on the served page, print them and exit", arguments=_wait_arguments
)
def wait(args: argparse.Namespace, run: cli.Run) -> int:
    """Print the actionable batch when the user acts. Exit 3 when none came in time."""
    unit = _unit(args, run)
    conv = _conversation(run, unit)
    if os.environ.get("BETTER_PAGE_SESSION") or live_driver(unit, conv):
        raise Refused(f"{unit.label}: wait cannot run on a driven page")
    address = conv.address()
    if address is None:
        raise paths.refusal(unit.label, "no page is served", f"run serve {unit.label} first")
    receipt = _read_delivery_state(unit, WAIT_RECEIPT)
    after = _delivery_position(receipt, "position")
    if after > len(conv.lines()):
        after = 0
    carry_ids = _delivery_ids(receipt, "item_ids")
    headers = {}
    with contextlib.suppress(FileNotFoundError):  # a server from before the token has no file, and ignores the header
        headers[TOKEN_HEADER] = paths.read_bytes(unit, TOKEN).decode("ascii", errors="replace").strip()
    deadline = time.monotonic() + args.timeout
    scan = after
    while (remaining := deadline - time.monotonic()) > 0:
        total = _wait_total(address, scan, remaining, headers, unit)
        if total <= scan:
            continue
        events = conv.events()
        if any(from_user(event) for event in events[scan:]):
            found = delivery.select(
                events, all_items(events, conv.items, conv.agent), conv.items, after, carry_ids, frozenset()
            )
            if found.items or found.events:
                run.out("\n".join(terminal_json(event) for event in [*found.items, *found.events]))
                # The listener has no turn-end signal. Keep its last batch visible to pending for an interrupted chat.
                state = {"after": after, "position": found.position, "item_ids": [item["id"] for item in found.items]}
                paths.write_atomic(unit, WAIT_RECEIPT, json.dumps(state).encode())
                return 0
        scan = len(events)
    raise cli.TimedOut("no new action before the timeout")


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


@cli.verb("pending", help="list the user's actionable items and events", arguments=_unit_argument)
def pending(args: argparse.Namespace, run: cli.Run) -> int:
    """Read current item states and the latest batch's non-item events, including after an interruption."""
    unit = _unit(args, run)
    conv = _conversation(run, unit)
    session = os.environ.get("BETTER_PAGE_SESSION")
    active = _read_delivery_state(unit, ACTIVE_DELIVERY) if session else {}
    if session and active.get("session") == session:
        # Items already sent in this turn stay available when the agent marks them seen or working.
        sent = _delivery_ids(active, "item_ids")
        found = conv.delivery(
            _delivery_position(active, "after"),
            carry_ids=_delivery_ids(active, "carry_ids"),
            recover_ids=_delivery_ids(active, "recover_ids") | sent,
        )
    else:
        receipt = _read_delivery_state(unit, WAIT_RECEIPT)
        found = conv.delivery(_delivery_position(receipt, "after"), carry_ids=_delivery_ids(receipt, "item_ids"))
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
    token = ""
    answer_started = False
    old_cache: tuple[float, int] = (0.0, 0)
    driven: DrivenPage | None = None

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
        if self.driven:
            self.request.settimeout(2)
        self.guarded(super().setup)

    def handle(self) -> None:
        self.guarded(super().handle)

    def finish(self) -> None:
        self.guarded(super().finish)

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

    def has_token(self) -> bool:
        """Whether the request carries this server's token: what keeps another process on this machine from reading
        or writing the conversation as the user. Compared in constant time."""
        if not self.token:
            return False  # a server made without a token answers nobody
        given = self.headers.get(TOKEN_HEADER) or ""
        return hmac.compare_digest(given.encode("utf-8", "replace"), self.token.encode())

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
        paired = bool(driven and not driven.off)
        if paired:
            if not driven.main_host(self.headers.get("Host")):
                return self.send_error(403)
            if path == "/listening":
                return self.send_json({"unit": driven.identity, "session": driven.session})
            if path == "/wait":
                return self.send_error(403)
            if path in ("/data", "/events", "/old", "/rev", "/agent") and not self.driven_token(driven.main_pair):
                return self.send(403, b"Opened elsewhere. Ask for a new link.", "text/plain")
            if path == "/agent":
                return self.send_json(driven.status())
        if path in ("/", "/index.html"):
            return self.send(
                200,
                shell(self.spec, paired).encode(),
                CONTENT_TYPES[".html"],
                policy=DRIVEN_SHELL_POLICY if paired else None,
            )
        if path in self.assets:
            kind = CONTENT_TYPES[os.path.splitext(path)[1]]
            return self.send(200, resources.read_bytes(self.assets[path]), kind)
        if not paired and path in ("/data", "/events", "/wait") and not self.has_token():
            return self.send(401, f"{OUT_OF_DATE}\n".encode(), "text/plain; charset=utf-8")
        if path == "/data":
            return self.send_json(
                page_data({**self.spec.load(self.unit), "listening": c.listening(), "now": time.time()})
            )
        if path == "/old":
            return self.send_json(self.old_format_count())
        if path == "/rev":
            rev = self.spec.revision(self.unit) if self.spec.revision else "0"
            return self.send(200, str(rev).encode(), "text/plain")
        if path == "/listening":
            return self.send_json(c.listening())
        if path == "/events":
            # Long poll for the page: every event after the first `after`, the agent's included.
            after = self.after(parts.query)
            total = c.wait_for_more(after, 20)
            reply = {"total": total, "events": c.events()[after:total]}
            if paired:
                with driven.routing_lock:
                    if driven.off or not self.driven_token(driven.main_pair):
                        return self.send(403, b"Opened elsewhere. Ask for a new link.", "text/plain")
                    return self.send_json(reply)
            return self.send_json(reply)
        if path == "/wait":
            seconds = urllib.parse.parse_qs(parts.query).get("seconds", ["25"])[0]
            seconds = int(seconds) if seconds.isdigit() and len(seconds) <= 4 else 25
            return self.send(200, str(c.waited(self.after(parts.query), seconds)).encode(), "text/plain")
        return self.send_error(404)

    @answers_any_failure
    def do_POST(self):
        lock = self.driven.routing_lock if self.driven else contextlib.nullcontext()
        with lock:
            self.post()

    def post(self):
        # Only this page may send: the same host and origin, and a JSON body that a cross-site form cannot send.
        origin = self.headers.get("Origin", "")
        if not self.local() or origin != "http://" + (self.headers.get("Host") or ""):
            return self.send_error(403)
        driven = self.driven
        if driven and not driven.off:
            if not driven.main_host(self.headers.get("Host")) or not self.browser_origin():
                return self.send_error(403)
            if self.path == "/pair":
                return self.pair(driven.main_pair, unauthorized=403)
            if self.path != "/rpc":
                return self.send_error(404)
            if not self.driven_token(driven.main_pair):
                return self.send(403, b"Opened elsewhere. Ask for a new link.", "text/plain")
            if not driven.driver or not driven.session:
                return self.send_error(503)
        elif self.path != "/rpc":
            return self.send_error(403)
        elif not self.has_token():
            return self.send_json(rpc_error(None, -32001, OUT_OF_DATE))
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
            or msg.get("method") not in self.methods
            or not isinstance(msg.get("params"), dict)
        ):
            return self.send_json(rpc_error(rid, -32601, "Unknown method"))
        # The page sets only its own fields: the type is the method, the time is the server's, and "by" is the user's,
        # so a page cannot write an event as the agent's or hide one from `wait`.
        params = clean(msg["params"])
        if "by" in params:
            return self.send_json(rpc_error(rid, -32602, "by: not allowed in what a page sends; the server sets it"))
        params = {k: v for k, v in params.items() if k not in ("type", "at")}
        try:
            (line,) = self.conversation.append({"type": msg["method"], "by": "user", **params})
        except EventError as error:
            return self.send_json(rpc_error(rid, -32602, str(error)))
        if driven and not driven.off:
            driven.driver.enqueue(json.loads(line))
        else:
            with contextlib.suppress(OSError):  # a closed stdout is not a failed save
                print(line, flush=True)
        return self.send_json({"jsonrpc": "2.0", "id": rid, "result": "saved"})

    def log_message(self, *args):
        pass


def make_server(unit: Unit, spec: PageSpec, conv: Conversation, info: resources.BuildInfo, port: int = 0):
    """The HTTP server for a unit's page, on 127.0.0.1; not started. Its `token` is made here, new for each server."""

    class PageHandler(Handler):
        pass

    PageHandler.unit, PageHandler.spec, PageHandler.conversation = unit, spec, conv
    PageHandler.methods, PageHandler.assets = spec.sendable(), spec.table()
    PageHandler.bug_prefix = f"{unit.skill.name} {info.hash}"
    PageHandler.cutoff = info.cutoff
    PageHandler.token = secrets.token_urlsafe(32)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), PageHandler)
    server.handler = PageHandler
    server.token = PageHandler.token  # type: ignore[attr-defined]
    return server


def page_url(server: http.server.HTTPServer) -> str:
    """The address a browser opens, with the token in its fragment, which a browser does not send to any server."""
    return f"http://127.0.0.1:{server.server_address[1]}/#t={server.token}"  # type: ignore[attr-defined]


def publish(unit: Unit, server: http.server.HTTPServer) -> str:
    """Write the server's token (private to the user) and then its address to the unit, as an agent finds them; returns
    the address a browser opens (`page_url`)."""
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    paths.write_state(unit, TOKEN, server.token.encode(), 0o600)  # type: ignore[attr-defined]
    paths.write_state(unit, ADDRESS, url.encode())
    return page_url(server)


def unit_identity(unit: Unit) -> str:
    return hashlib.sha256(os.fsencode(unit.path)).hexdigest()


def live_driver(unit: Unit, conv: Conversation | None = None) -> dict:
    if not unit.target(".driver").exists():
        return {}
    from .adapters import session_id_valid
    from .driver_state import read_driver_state

    state = read_driver_state(unit, valid_session=session_id_valid)
    if not state:
        return {}
    try:
        address = conv.address() if conv else paths.read_bytes(unit, ADDRESS).decode().strip()
        parsed = urllib.parse.urlsplit(address or "")
        if parsed.scheme != "http" or parsed.netloc != f"127.0.0.1:{parsed.port}" or parsed.path != "/":
            return {}
        with contextlib.closing(http.client.HTTPConnection("127.0.0.1", parsed.port, timeout=1)) as connection:
            connection.request("GET", "/listening")
            reply = connection.getresponse()
            marker = json.loads(reply.read(4096)) if reply.status == 200 else {}
    except (OSError, ValueError, Refused, http.client.HTTPException):
        return {}
    return state if marker == {"unit": unit_identity(unit), "session": state["session"]} else {}


def driven_notice(unit: Unit) -> None:
    state = live_driver(unit)
    if state and os.environ.get("BETTER_PAGE_SESSION") not in (state["session"], state.get("tag", "")):
        print(f"this unit's page is driven by session {state['session']}", file=sys.stderr)


def remove_if_ours(unit: Unit, name: str, value: bytes) -> None:
    with contextlib.suppress(OSError, Refused):
        if paths.read_bytes(unit, name) == value:
            unit.target(name).unlink()


@contextlib.contextmanager
def serve_lock(unit: Unit, conv: Conversation):
    fd = os.open(unit.target(".page-serve-lock"), os.O_RDWR | os.O_CREAT | paths.NOFOLLOW, 0o600)
    try:
        try:
            lock_unit(fd)
        except OSError:
            raise Refused(
                f"{unit.label}: a page server is already serving at {conv.address() or 'a port opening now'}"
            ) from None
        if conv.answering():
            raise Refused(f"{unit.label}: a page server is already serving at {conv.address()}")
        yield
    finally:
        os.close(fd)


def lock_unit(fd: int) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def stop_orphan(unit: Unit) -> None:
    if not unit.target(".driver").exists():
        return
    from .adapters import session_id_valid
    from .driver_state import read_driver_state
    from .transport import process_birth

    state = read_driver_state(unit, valid_session=session_id_valid)
    pid, birth = state.get("child_pid"), state.get("child_started")
    if type(pid) is not int or pid <= 1 or not birth:
        return
    for signum in (signal.SIGTERM, signal.SIGKILL):
        try:
            if process_birth(pid) != birth or os.getpgid(pid) != pid:
                return
            os.killpg(pid, signum)
        except ProcessLookupError:
            return
        except PermissionError:
            raise Refused(f"{unit.label}: the previous page agent's process group could not be stopped") from None
        if signum == signal.SIGTERM:
            time.sleep(0.2)


LINK_SOCKET = ".page-link"
PANEL_ASSETS = {
    "/page.css": "page/page.css",
    "/approvals.html": "page/approvals.html",
    "/approvals.js": "page/approvals.js",
    "/approvals.css": "page/approvals.css",
}
START_TIMEOUT = 30
ENROLL_TIMEOUT = 120


class ApprovalHandler(Handler):
    """Only bundled panel assets and session-specific control run on this origin."""

    def end_headers(self):
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    @answers_any_failure
    def do_GET(self):
        driven = self.driven
        if self.headers.get("Host") != driven.panel_host:
            return self.send_error(403)
        if self.path in PANEL_ASSETS:
            kind = CONTENT_TYPES[os.path.splitext(self.path)[1]]
            return self.send(200, resources.read_bytes(PANEL_ASSETS[self.path]), kind)
        if self.path != "/agent":
            return self.send_error(404)
        if not self.driven_token(driven.panel_pair):
            return self.send(403, b"Opened elsewhere. Ask for a new link.", "text/plain")
        return self.send_json(driven.panel_status())

    @answers_any_failure
    def do_POST(self):
        with self.driven.routing_lock:
            self.post()

    def post(self):
        driven = self.driven
        if (
            self.headers.get("Host") != driven.panel_host
            or self.headers.get("Origin") != driven.panel_origin
            or not self.browser_origin()
        ):
            return self.send_error(403)
        if self.path == "/pair":
            return self.pair(driven.panel_pair, driven.main_link, unauthorized=403)
        if self.path != "/rpc":
            return self.send_error(404)
        if not self.driven_token(driven.panel_pair):
            return self.send(403, b"Opened elsewhere. Ask for a new link.", "text/plain")
        rid = None
        try:
            message = self.read_json()
            if message is None and self.answer_started:
                return
            if not isinstance(message, dict):
                raise ValueError("Invalid request")
            rid, method, params = message.get("id"), message.get("method"), message.get("params")
            if message.get("jsonrpc") != "2.0" or not isinstance(params, dict):
                raise ValueError("Invalid request")
            result = driven.control(method, params)
        except (TypeError, ValueError) as error:
            return self.send_json(rpc_error(rid, -32602, str(error)))
        return self.send_json({"jsonrpc": "2.0", "id": rid, "result": result})


def run_http(server):
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": POLL}, daemon=True)
    thread.start()
    return thread


class DrivenPage:
    def __init__(self, server, unit, archive, record_verbs, require_presence):
        from .approvals import ApprovalGate, Pairing

        self.server, self.unit = server, unit
        self.identity = unit_identity(unit)
        self.main_origin = f"http://127.0.0.1:{server.server_port}"
        self.driver, self.off, self.ready = None, None, False
        self.enrollment = threading.Event()
        self.routing_lock = threading.RLock()

        class PanelHandler(ApprovalHandler):
            pass

        PanelHandler.driven = self
        self.panel = http.server.ThreadingHTTPServer(("127.0.0.1", 0), PanelHandler)
        self.panel_host = f"localhost:{self.panel.server_port}"
        self.panel_origin = "http://" + self.panel_host
        try:
            self.main_pair = Pairing(self.main_origin)
            self.panel_pair = Pairing(self.panel_origin)
            self.gate = ApprovalGate(
                unit.path,
                self.panel_origin,
                require_presence=require_presence,
                archive=archive,
                record_verbs=record_verbs,
            )
            self.enrollment_needed = require_presence and not self.gate.enrolled()
        except BaseException:
            self.panel.server_close()
            raise
        server.handler.driven = self
        run_http(self.panel)

    @property
    def session(self):
        return self.driver.session if self.ready else None

    def main_host(self, host):
        return host == self.main_origin.removeprefix("http://")

    def panel_link(self):
        with self.routing_lock:
            self.main_pair.issue()  # invalidate the previous conversation tab as soon as a new link is issued
            return f"{self.panel_origin}/approvals.html#p={self.panel_pair.issue()}"

    def main_link(self):
        with self.routing_lock:
            if self.off:
                return page_url(self.server)
            return f"{self.main_origin}/#p={self.main_pair.issue()}"

    def status(self):
        if self.off:
            return self.off
        if self.driver and self.session:
            return {**self.driver.snapshot(), "harness": self.driver.harness}
        return {"state": "starting", "age": 0}

    def panel_status(self):
        status = self.status()
        return {
            **status,
            **self.available_controls(status),
            **(self.gate.snapshot() if not self.off else {"approvals": [], "page": page_url(self.server)}),
            "enrollment_needed": self.enrollment_needed and not self.off,
        }

    def available_controls(self, status):
        live = self.ready and not self.off and status.get("age", 4) <= 3 and status.get("kind") != "driver"
        return {
            "can_start": bool(live and status["state"] in ("stopped", "failed")),
            "can_stop": bool(live and status["state"] in ("idle", "working", "stalled")),
        }

    def control(self, method, params):
        if self.off:
            raise ValueError("This page has no driver")
        if self.enrollment_needed and method == "enroll_begin":
            return self.gate.begin_enrollment()
        if self.enrollment_needed and method == "enroll_finish":
            self.gate.finish_enrollment(params.get("proof"))
            self.enrollment_needed = False
            self.enrollment.set()
            return True
        if not self.driver or not self.session or self.driver.snapshot()["age"] > 3:
            raise ValueError("The page's agent driver stopped. Serve the page again.")
        if method == "permission_challenge":
            return self.gate.challenge(params.get("id"), params.get("choice"))
        if method == "permission_answer":
            return self.gate.answer(params.get("id"), params.get("choice"), params.get("proof"))
        if method == "agent_stop" and self.available_controls(self.status())["can_stop"]:
            self.driver.request_stop()
            return True
        if method == "agent_start" and self.available_controls(self.status())["can_start"]:
            self.driver.request_start()
            return True
        raise ValueError("Unknown method")

    def fail(self, kind, message):
        from .driver import ACTIONS

        with self.routing_lock:
            self.off = {"state": "failed", "kind": kind, "message": message, "action": startup_action(kind, ACTIONS)}

    def close(self):
        if self.driver:
            self.driver.close()
        self.panel.shutdown()
        self.panel.server_close()


def startup_action(kind, actions):
    if kind == "login":
        return "Log in to the harness in a terminal, then serve again."
    if kind in ("crashed", "limit", "not-handling", "driver"):
        return "Serve again."
    return actions.get(kind, "")


def link_existing(unit, conv):
    """Ask the live server over its private local control socket. Its path is not a browser credential."""
    from .driver_state import private_bytes

    address = conv.address()
    if not live_driver(unit, conv):
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
            if not url.startswith("http://localhost:"):
                raise ValueError()
            return url
    except (OSError, ValueError):
        raise Refused(f"{unit.label}: could not pair a tab with the running server at {address}") from None


@contextlib.contextmanager
def link_control(driven):
    if not driven or not driven.session:
        yield
        return
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
                            connection.sendall(driven.panel_link().encode() + b"\n")
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


def handoff_note(run: cli.Run):
    """Read the hand-off without letting an open pipe hold startup past either deadline."""
    notes = []
    stream = run.stdin or sys.stdin
    if stream.isatty():
        return notes

    def read():
        with contextlib.suppress(OSError, ValueError):
            notes.append(stream.read(64 * 1024))

    threading.Thread(target=read, daemon=True).start()
    return notes


def start_driven(driven, candidate, conv, run, deadline, notes, archive, skill_path):
    from .adapters import _MIN_VERSION, child_environment, session_id_valid, version_supported
    from .driver import Driver, StartError
    from .transport import ProcessTransport

    env = os.environ.copy()
    try:
        remaining = max(0.0, deadline - time.monotonic())
        version = subprocess.run(
            [candidate.argv[0], "--version"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=remaining,
            check=False,
            cwd=conv.unit.root,
            env=env,
        )
    except subprocess.TimeoutExpired:
        raise StartError("crashed", "harness startup timed out") from None
    except FileNotFoundError:
        raise StartError("not-installed") from None
    detected = version.stdout.strip()[:500] or "unknown"
    needed = ".".join(str(part) for part in _MIN_VERSION[candidate.name])
    version_message = f"{candidate.name} reported {detected}. Version {needed} or later is required."
    if version.returncode or not version_supported(candidate.name, version.stdout):
        raise StartError("version", version_message)

    def launch(tag, resume):
        return ProcessTransport(
            candidate.command(tag, resume),
            conv.unit.root,
            child_environment(candidate.name, env, tag),
            lambda send: candidate.codec(send, tag, resume),
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
        handoff=notes[0] if notes else "",
        triggers=lambda: conv.spec.triggers(conv.unit) if conv.spec.triggers else (),
        approvals=driven.gate,
        valid_session=lambda session: session_id_valid(candidate.name, session),
    )
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise StartError("crashed", "harness startup timed out")
    try:
        driven.driver.start(remaining)
    except StartError as error:
        if error.kind != "version":
            raise
        raise StartError("version", f"{version_message} The harness protocol reported: {error}.") from None
    driven.ready = True


def _serve_arguments(parser: argparse.ArgumentParser) -> None:
    _unit_argument(parser)
    parser.add_argument("--port", type=int, default=0, help="port to serve on (default: any free port)")
    opening = parser.add_mutually_exclusive_group()
    opening.add_argument("--open", action="store_true", help="open the page in a browser")
    opening.add_argument("--no-browser", action="store_true", help="do not open a browser (the default)")
    parser.add_argument("--linger", type=float, default=10, help="seconds to keep serving after the unit stops")
    parser.add_argument("--once", action="store_true", help="serve one request, then exit")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--drive", choices=("auto", "claude", "codex", "cursor", "opencode", "droid", "devin"))
    mode.add_argument("--link", action="store_true", help="pair a new tab with an already driven page")


@cli.verb(
    "serve",
    help="serve the unit's live page; prints each action the user takes as one JSON line",
    arguments=_serve_arguments,
)
def serve(args: argparse.Namespace, run: cli.Run) -> int:
    """Check every record, then serve the page until the unit stops (or Ctrl+C). A record that is not valid is a warning
    on stderr: the page still opens and shows it."""
    deadline = time.monotonic() + START_TIMEOUT
    unit = _unit(args, run)
    if os.environ.get("BETTER_PAGE_SESSION"):
        raise Refused(f"{unit.label}: serve cannot run from a page agent session")
    spec = spec_of(run.skill)
    conv = Conversation(unit, spec, load_docs(run.skill))
    if args.link:
        run.out(link_existing(unit, conv))
        return 0
    with serve_lock(unit, conv):
        stop_orphan(unit)
        return serve_page(args, run, unit, spec, conv, deadline)


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


def prepare_serve(args, run, unit, conv, deadline):
    if not args.drive:
        preflight(run, unit, conv)
        return True
    complete = Future()

    def check():
        try:
            preflight(run, unit, conv)
        except BaseException as error:
            complete.set_exception(error)
        else:
            complete.set_result(None)

    threading.Thread(target=check, daemon=True).start()
    try:
        complete.result(timeout=max(0, deadline - time.monotonic()))
        return True
    except FutureTimeout:
        if complete.done():
            complete.result()
        run.out("driver: off crashed")
        # The driver is abandoned at the deadline. The legacy page still needs all its usual checks.
        complete.result()
        return False


def serve_page(args, run, unit, spec, conv, deadline):
    can_drive = prepare_serve(args, run, unit, conv, deadline)
    try:
        server = make_server(unit, spec, conv, run.info, args.port)
    except OSError as error:
        reason = (error.strerror or type(error).__name__).lower()
        raise paths.refusal(
            unit.label, f"cannot be served on port {args.port} ({reason})", f"serve {unit.label} on a free port"
        ) from None
    address = f"http://127.0.0.1:{server.server_port}/".encode()
    url = page_url(server)
    driven, serving, token = None, None, None
    opened = False
    try:
        if args.drive and can_drive:
            from .adapters import candidate
            from .driver import ACTIONS, StartError

            wanted = candidate(args.drive, os.environ)
            kind = wanted.kind
            if kind is None and (os.name != "posix" or wanted.approval not in ("os", "webauthn")):
                kind = "no-approvals"
            if kind is None:
                stop_like_ctrl_c()
                archive = Path(sys.argv[0]).resolve() if run.info.hash != "source" else None
                skill_path = (
                    archive.parent.parent / "SKILL.md"
                    if archive
                    else (Path(__file__).resolve().parents[3] / "skills" / run.skill.name / "SKILL.md")
                )
                # A previous server can leave a legacy token after SIGKILL. Never leave that file in driven mode.
                with contextlib.suppress(FileNotFoundError):
                    unit.target(TOKEN).unlink()
                try:
                    driven = DrivenPage(server, unit, archive, ("add", "set"), wanted.approval == "webauthn")
                except (OSError, ValueError):
                    kind = "no-approvals"
                    run.err("Could not load the approval credential or start the approval panel.")
            if driven is not None:
                notes = handoff_note(run)
                serving = run_http(server)
                url = driven.panel_link()
                if driven.enrollment_needed:
                    deadline += ENROLL_TIMEOUT - START_TIMEOUT
                    run.out(f"Enrollment at {url}")
                    if args.open:
                        open_page(run, url)
                        opened = True
                try:
                    if driven.enrollment_needed:
                        # Leave the ordinary startup allowance after a touch when there is enough time.
                        enrolled = driven.enrollment.wait(max(0, deadline - time.monotonic()))
                        if not enrolled:
                            raise StartError("no-approvals", "Approval enrollment timed out")
                        deadline = min(deadline, time.monotonic() + START_TIMEOUT)
                    start_driven(driven, wanted, conv, run, deadline, notes, archive, skill_path)
                except (OSError, StartError) as error:
                    kind = error.kind if isinstance(error, StartError) else "crashed"
                    # Report the mode at the deadline even if cleaning up the harness takes a moment.
                    run.out(f"driver: off {kind}")
                    action = startup_action(kind, ACTIONS)
                    run.err(f"{str(error).rstrip('.')}. {action}")
                    driven.fail(kind, str(error))
                    url = page_url(server)
            if kind is None:
                run.out(f"driver: on {wanted.name} {driven.session}")
            elif driven is None:
                run.out(f"driver: off {kind}")

        if args.once and serving is not None and driven.off:
            server.shutdown()
            serving = None
        with link_control(driven):
            if driven and not driven.off:
                run.out(f"Serving {unit.label} at {url}")
                paths.write_state(unit, ADDRESS, address)
            else:
                run.out(f"Each action the user takes is printed here as one JSON line. Serving {unit.label} at {url}")
                token = server.token.encode()
                publish(unit, server)
                if driven and driven.driver:
                    driven.driver.close()
            if not unit.target(SEEN).exists():
                paths.write_state(unit, SEEN, b"0")
            if args.open and (not opened or (driven and driven.off)):
                open_page(run, url)
            stop_like_ctrl_c()
            if args.once and serving is None:
                server.daemon_threads = False
                server.handle_request()
                return 0
            if serving is None:
                serving = run_http(server)
            serve_until_stopped(args, run, unit, spec, conv, driven)
    except KeyboardInterrupt:
        return 0
    finally:
        if serving is not None:
            server.shutdown()
        server.server_close()
        if driven:
            driven.close()
        remove_if_ours(unit, ADDRESS, address)
        if token:
            remove_if_ours(unit, TOKEN, token)
    return 0


def open_page(run, url):
    if not webbrowser.open(url):
        run.out(
            "Could not open a browser on this machine. If the user's browser runs on another machine, "
            "this address does not reach it."
        )


def serve_until_stopped(args, run, unit, spec, conv, driven):
    stopped_at = None
    while True:
        time.sleep(TICK)
        try:
            if spec.tick:
                spec.tick(unit, conv)
            stopped = bool(spec.stopped and spec.stopped(unit))
            if stopped and driven and not driven.off:
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
