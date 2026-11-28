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
import http.server
import json
import os
import secrets
import signal
import sys
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
from typing import Any

from .. import cli, paths, resources, schema
from ..paths import Refused, Unit
from ..skill import Skill

COMMON = "conversation.schema.json"
LOG, SEEN, ADDRESS, TOKEN = "conversation.jsonl", ".conversation-seen", ".server", ".server-token"
# The line position (from 0) of an event: in the data a page reads threads from, and on each event `wait` and `serve`
# print, so the agent can pass the last one it read as `--read` (which counts in the same lines).
LINE = "_i"
TOKEN_HEADER = "X-Page-Token"
OUT_OF_DATE = "page out of date: open the address the agent gave"  # what a page without the token is told; page.js shows it and keeps the typing
MAX_BODY = 200_000
LISTEN_GAP = 10  # seconds without a `wait` connected before the page says the agent is not watching
WAIT_DEFAULT = 600  # seconds `wait` waits, in every skill
TICK = 1  # seconds between the ticks of a served page; tests set it shorter
POLL = 0.05  # seconds serve_forever waits for a request before it looks whether it was told to stop
STATES = ("seen", "asked", "working", "done", "accepted")  # `accepted` is written as its own event, `accepted`
REPLY_STATES = ("done", "asked", "working")
FINISHED = ("done",)  # the state of a thread that needs no more work, until the user writes in it or reopens it
BUG_TEXT = "The page hit a bug: ask the agent to restart it and report it"
QUIET_AFTER = timedelta(minutes=30)  # how long an agent at work may go without a record before its page says so
# What each shared capability lets the page send, and which of those events the agent tracks with a status.
CAPABILITIES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "pins": (("comment", "delete"), ("comment",)),  # numbered pins on the page, and taking a comment back
    "accept": (("accept", "reopen"), ()),  # the user accepts what the agent finished, or puts it back
    "decisions": (("answer",), ("answer",)),  # the user answers a decision question
    "confirm": (("confirm",), ()),  # the user confirms a requirement in the wording shown: no reply needed (D8)
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


def from_user(event: dict) -> bool:
    """An event the user made in the page, as opposed to the agent's replies, statuses and recorded acceptances."""
    return bool(event) and event.get("by") == "user"


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
    served (`.server`) and how far `wait` has read (`.conversation-seen`). Everything is read and written through
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

    def logged(self) -> list[dict]:
        """The events that could be read, each with its line position in LINE, for data a page reads threads from
        (see `log_records`)."""
        return [{**e, LINE: n} for n, e in enumerate(self.events()) if e]

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

    def position(self, line: str) -> int:
        """The line of the log that holds LINE, just appended: the last line equal to it (each holds its own time, and a
        reply the CLI appends in the meantime can come after it)."""
        lines = self.lines()
        return next((n for n in range(len(lines) - 1, -1, -1) if lines[n] == line), len(lines) - 1)

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

    def seen(self) -> int:
        try:
            return int(paths.read_bytes(self.unit, SEEN).decode("utf-8").strip() or 0)
        except FileNotFoundError:
            return 0
        except ValueError:
            raise paths.refusal(
                f"{self.unit.label}/{SEEN}", "does not hold a number", "delete it and run wait again"
            ) from None

    def unread(self, events: list, ids: list, read: int | None, verb: str) -> int:
        """Refuse a status or a reply under a thread unless the agent says what it read (`--read`, a line of the log)
        and the user wrote in none of the threads of IDS after that line (D12); return READ. The fold's own guard
        (`threads`) still covers a user event that lands between this check and the write."""
        label = self.unit.label
        if read is None:
            raise paths.refusal(
                label,
                f"{verb} needs --read <n>, the line of the last event you read",
                f"pass the `_i` of the last line wait or serve printed, or run pending {label} and pass its number",
            )
        if read >= len(events):
            raise paths.refusal(label, f"--read {read}: the log has no line {read}", f"run pending {label} again")
        later = [e for e in events[read + 1 :] if e.get("by") == "user"]  # only the user's own events count
        newer = []
        for t in threads(events, self.items):
            named = ({t["id"]} | {m.get("id") for m in t["messages"]}) - {None}
            if not named & set(ids):
                continue
            if any(named & {e.get("id"), e.get("to"), e.get("decision")} for e in later):
                newer.append(t["id"])
        if newer:
            raise paths.refusal(
                label,
                f"the user wrote in {terminal_text(', '.join(dict.fromkeys(newer)))} after line {read}",
                f"run pending {label} to read them, then send this again with the --read it prints",
            )
        return read

    def write(self, *events: dict) -> list:
        """Append the agent's own events; one that fails its schema is refused with the validator's message."""
        try:
            return self.append(*events)
        except EventError as error:
            raise Refused(f"{self.unit.label}: the event is not valid: {error}") from None

    def known(self, ids: list, what: str = "no comment or message with id", started: bool = False) -> None:
        """Refuse ids that name no item of the user's; with `started`, a message the agent or a worker sent on its own
        is known too."""
        have = {
            e.get("id")
            for e in self.events()
            if e.get("type") in self.items
            or (started and e.get("type") in ("reply", "closed") and e.get("by") != "user" and not e.get("to"))
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


@cli.verb(
    "wait", help="wait for the user's next actions on the served page, print them and exit", arguments=_wait_arguments
)
def wait(args: argparse.Namespace, run: cli.Run) -> int:
    """Print the user's events the agent has not seen yet, one JSON line each with its line in the log as `_i` (what the
    agent passes as `--read`), waiting for the page to receive one. Exit 3 when none came in time."""
    unit = _unit(args, run)
    conv = _conversation(run, unit)
    address = conv.address()
    if address is None:
        raise paths.refusal(unit.label, "no page is served", f"run serve {unit.label} first")
    seen = conv.seen()
    headers = {}
    with contextlib.suppress(FileNotFoundError):  # a server from before the token has no file, and ignores the header
        headers[TOKEN_HEADER] = paths.read_bytes(unit, TOKEN).decode("ascii", errors="replace").strip()
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        request = urllib.request.Request(
            f"{address}wait?after={seen}&seconds={max(1, int(deadline - time.time()))}", headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                total = int(response.read())
        except urllib.error.HTTPError as error:
            if error.code == 401:
                raise paths.refusal(
                    unit.label, "the page's server does not accept this token", f"run serve {unit.label} again"
                ) from None
            raise paths.refusal(
                unit.label, "the page's server is not answering", f"run serve {unit.label} again"
            ) from None
        except (OSError, ValueError):
            raise paths.refusal(
                unit.label, "the page's server is not answering", f"run serve {unit.label} again"
            ) from None
        if total <= seen:
            continue
        events = conv.events()[seen:total]
        new = [json.dumps({**e, LINE: n}) for n, e in enumerate(events, start=seen) if from_user(e)]
        paths.write_state(unit, SEEN, str(total).encode())
        seen = total
        if new:
            run.out("\n".join(new))
            return 0
    raise cli.TimedOut("no new action before the timeout")


def _line(value: str) -> int:
    if not value.isdigit():
        raise argparse.ArgumentTypeError(f"not a line of the log: {value!r}")
    return int(value)


def _read_argument(parser: argparse.ArgumentParser, needed: str) -> None:
    parser.add_argument(
        "--read",
        type=_line,
        metavar="N",
        help=f"the line of the last event you read: the `_i` of the last line wait or serve printed, or the number"
        f" pending printed last; {needed}. Refused when the user wrote in the thread after it",
    )


def _reply_arguments(parser: argparse.ArgumentParser) -> None:
    _unit_argument(parser)
    parser.add_argument("--to", help="the id of the item it answers; the item's status is set in the same write")
    parser.add_argument(
        "--state",
        choices=REPLY_STATES,
        default="done",
        help="the status of the thread it answers: done (default), asked when the reply asks the user back, or working;"
        " without --to, asked posts it as a question and the rest as a report",
    )
    _read_argument(parser, "needed with --to")
    parser.add_argument("--by", help="the agent's name, if not the page's role name")


@cli.verb(
    "reply",
    help="show a reply from the agent in the page; the text is on stdin",
    arguments=_reply_arguments,
)
def reply(args: argparse.Namespace, run: cli.Run) -> int:
    """Show the agent's reply in the page's conversation, in the thread it answers, with the thread's status. Without
    `--to` it starts a thread: a question with `--state asked` (the user's turn), else a report, written with its own done
    status (its own line as `read`), so it stays in Open until the user's ✓ (D13). Under a thread it
    needs `--read`, and is refused when the user wrote in the thread after it (D12). It works without a server, so a
    resumed run can answer what the user wrote while no agent was running."""
    unit = _unit(args, run)
    conv = _conversation(run, unit)
    by = paths.check_by(args.by) if args.by else conv.agent
    text = _text(run, f"{unit.label}: reply")[:5000]
    ident = "r-" + str(time.time_ns())
    events = [{"type": "reply", "by": by, "id": ident, "text": text, "to": args.to}]
    read = {} if args.read is None else {"read": args.read}
    if args.to is not None:
        target = conv.target_of(args.to)
        conv.known([target], started=True)
        read = {"read": conv.unread(conv.events(), [target], args.read, "reply --to")}
        events.append({"type": "status", "by": by, "to": target, "status": args.state, **read})
    elif args.state == "asked":  # a question of its own: the user's turn; any other message of its own is a report
        events.append({"type": "status", "by": by, "to": ident, "status": "asked", **read})
    else:  # a report: done by the agent, with its own line as read, so the user's check closes it (an old one is closed)
        events.append({"type": "status", "by": by, "to": ident, "status": "done", "read": len(conv.lines())})
    conv.write(*events)
    run.out("Reply shown in the page." if conv.answering() else "Reply saved; the page shows it when served.")
    return 0


def _status_arguments(parser: argparse.ArgumentParser) -> None:
    _unit_argument(parser)
    parser.add_argument("state", choices=STATES)
    parser.add_argument("ids", nargs="+", help="the ids of the user's items, or of a message the agent sent on its own")
    parser.add_argument("--text", action="store_true", help="read the user's words from stdin; needed for accepted")
    _read_argument(parser, "needed for every state but accepted")
    parser.add_argument("--by", help="the agent's name, if not the page's role name")


@cli.verb(
    "status",
    help="set threads seen, asked, working or done, or record the user's acceptance in words",
    arguments=_status_arguments,
)
def status(args: argparse.Namespace, run: cli.Run) -> int:
    """Mark threads as seen, asked, working or done, by the id of the user's item or of a message the agent sent on its
    own (`reply` without `--to`). Each status carries `read`, the line of the last event the agent read, which it passes
    as `--read`: the status is refused when the user wrote in one of the threads after that line (D12). Accepted
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
    if args.state == "accepted":  # the user's own act, in their words: no reading of the agent's to check
        conv.write(*({"type": "accepted", "by": by, "to": i, "text": words} for i in args.ids))
    else:
        read = conv.unread(events, args.ids, args.read, "status")
        conv.write(*({"type": "status", "by": by, "to": i, "status": args.state, "read": read} for i in args.ids))
    run.out(f"Marked {args.state}: {terminal_text(', '.join(args.ids))}")
    return 0


CONTROL = ("status", "accept", "accepted", "reopen", "delete")  # events that change a thread and start none


def log_records(read: schema.Read) -> list[dict]:
    """The records `schema.read_records` read from a conversation.jsonl, each with its line position in LINE. A status's
    `read` is a line index, and the reader leaves out lines it cannot read: every reader whose records `threads` or
    page.js `pageThreads` turn into threads goes through this, so a left-out line shifts no index."""
    return [{**record, LINE: line - 1} for record, line in zip(read.records, read.lines, strict=True)]


def threads(events: list, item_types: tuple[str, ...]) -> list[dict]:
    """The threads of a log, each in one state of the one machine every thread follows
    (.design/conversation-panel/states.md): page.js `pageThreads` gives the same threads for the same log, and
    tests/fixtures/threads.json holds the logs both are run on. Each thread, in the order it started, holds `id`, `root`
    (the latest form of the event that started it), `messages`, `state` (`you`, `agent` or `done`), `step` (`new`,
    `seen` or `working`), `closed_by_user` (also from the start, for the user's action that is no message to the agent,
    such as a verdict or a confirmation), `deleted`, `edited` (the user's comment was sent again), `since` (when the
    state or step was set), `user_at` (the log index of the user's latest event) and `last` (the time of its last
    message). An agent status counts only if its
    `read` covers the user's latest event in the thread; one without `read` counts (logs before `read`), and a done
    without `read` closes the thread as the user's ✓ does (D13). An event's
    index is its place in EVENTS, or its LINE when it has one (`log_records`)."""
    found: list[dict] = []
    by_id: dict[str, dict] = {}
    home: dict[str, str] = {}
    marked: set[int] = set()  # the threads an agent status names
    agent_read = -1

    def thread_of(ident: Any) -> dict | None:
        return by_id.get(home.get(ident, ident)) if isinstance(ident, str) else None

    for index, e in enumerate(events):
        if not isinstance(e, dict) or not e.get("type"):
            continue  # a line the log could not read keeps its place, and is no event
        line = e.get(LINE)
        i = line if isinstance(line, int) and not isinstance(line, bool) else index  # see log_records
        kind, ident, at, read = e.get("type"), e.get("id"), e.get("at"), agent_read
        user = e.get("by") == "user"
        item = user and kind in item_types
        number = e.get("read")
        number = number if isinstance(number, int) and not isinstance(number, bool) else None
        if not user and number is not None:
            agent_read = max(agent_read, number)
        target = e.get("decision") if kind == "answer" else e.get("to")
        t = thread_of(target)
        if t is None and item and ident in by_id and by_id[ident]["root"].get("type") == kind:
            t = by_id[ident]  # the user's item sent again, such as an edited comment: the same thread, in its state
            if kind == "comment":
                t["root"], t["messages"][0], t["deleted"], t["edited"] = e, e, False, True
        elif t is None:
            if kind not in CONTROL:
                t = {
                    "id": ident,
                    "root": e,
                    "messages": [e],
                    "state": "agent" if item else "done",
                    "step": "new",
                    "closed_by_user": False,
                    "deleted": False,
                    "edited": False,
                    "since": at,
                    "user_at": i if user else -1,
                    "last": at,
                }
                if isinstance(ident, str):
                    by_id[ident] = t
                # the user's action that is no message to the agent, such as a verdict or a confirmation, needs no
                # reply: its thread starts closed by the user, until they write in it (D8)
                if user and not item and kind not in ("note", "answer"):
                    t["closed_by_user"] = True
                # a worker's report that it closed a question starts closed too, the user's choice (D10)
                if kind == "closed":
                    t["closed_by_user"] = True
                found.append(t)
                if kind == "answer" and isinstance(target, str) and target not in by_id:
                    home[target] = ident  # later answers to the same decision join this thread
        else:
            if isinstance(ident, str):
                home[ident] = t["id"]
            if kind == "status":
                marked.add(id(t))
            fresh = number is None or number >= t["user_at"]
            if user and (item or kind in ("note", "answer", "reopen")):
                t["messages"].append(e)
                t.update(last=at, user_at=i, state="agent", step="new", closed_by_user=False, since=at)
            elif kind == "reply":
                t["messages"].append(e)  # the CLI writes the reply's status with it (done by default)
                t["last"] = at
            elif kind == "delete" and user:
                t["deleted"] = True
            elif (kind == "accept" and user) or kind == "accepted":
                # ✓, or the user's words that accept it: closes an open thread, or confirms one the agent finished.
                if t["state"] != "done":
                    t["since"] = at
                t.update(state="done", closed_by_user=True, user_at=i)
            elif kind == "status" and fresh and not t["closed_by_user"]:
                was = (t["state"], t["step"])  # a thread you closed changes only when you act on it again
                if e.get("status") == "asked":
                    t["state"] = "you"
                elif e.get("status") == "done":
                    t["state"] = "done"
                    if number is None:  # a done from before `read` (an old log): closed by the user, not in Open (D13)
                        t["closed_by_user"] = True
                elif t["state"] == "agent" and e.get("status") in ("seen", "working"):
                    t["step"] = e.get("status")
                if (t["state"], t["step"]) != was:
                    t["since"] = at
        if agent_read > read:  # seen follows the agent's reading, in every thread its read now covers
            for x in found:
                if x["state"] == "agent" and x["step"] == "new" and agent_read >= x["user_at"]:
                    x["step"], x["since"] = "seen", at
    for t in found:
        # A report the agent posted before reports carried their own done status (an old log), with no status and no
        # message from the user: closed by the user, in All and not in Open (D13).
        root = t["root"]
        if root.get("type") == "reply" and root.get("by") != "user" and t["user_at"] < 0 and id(t) not in marked:
            t["closed_by_user"] = True
    return found


def open_items(events: list, item_types: tuple[str, ...], agent: str) -> list[tuple[dict, str, dict]]:
    """The threads that are the agent's turn, as `all_items` gives them: what `pending` lists."""
    return [found for found in all_items(events, item_types, agent) if found[1] == "agent"]


def all_items(events: list, item_types: tuple[str, ...], agent: str) -> list[tuple[dict, str, dict]]:
    """Every thread that holds an item of the user's, as (event, state, extra), without the deleted ones: the event
    that started it in its latest form, its state (`you`, `agent` or `done`, from `threads`), and in `extra` its
    `step`, `since`, `closed_by_user`, the `thread` of messages after the first, `reopened_because` (the user's last
    reopen) and, under a worker's `closed`, what the worker closed (`about`). `pending` and a skill's own summary both
    call these."""
    found = []
    for t in threads(events, item_types):
        held = [m for m in t["messages"] if m.get("by") == "user" and m.get("type") in (*item_types, "reopen")]
        if t["deleted"] or not held:
            continue
        root = {k: v for k, v in t["root"].items() if k != LINE}
        extra: dict[str, Any] = {"step": t["step"], "since": t["since"], "closed_by_user": t["closed_by_user"]}
        if root.get("type") == "closed":  # the worker cannot read the page: say which question the user replied about
            extra["about"] = f"{root.get('by')} closed {root.get('question')} as {root.get('status')}"
        reasons = [m.get("text") for m in t["messages"] if m.get("type") == "reopen" and m.get("text")]
        if reasons:
            extra["reopened_because"] = reasons[-1]
        thread = [
            {"from": "user" if m.get("by") == "user" else agent, "at": m.get("at"), "text": m.get("text")}
            | ({"id": m["id"]} if m.get("id") else {})
            for m in t["messages"][1:]
            if m.get("type") != "reopen"
        ]
        if thread:
            extra["thread"] = thread
        found.append((root, t["state"], extra))
    return found


@cli.verb("pending", help="list the threads that are the agent's turn", arguments=_unit_argument)
def pending(args: argparse.Namespace, run: cli.Run) -> int:
    """Print each thread that is the agent's turn, the event that started it in its latest form, with its step as
    `status` (`new`, `seen` or `working`) and the messages under it, so work can resume after an interruption. A thread
    waiting on the user (`asked`) or done is not listed. `open_items` holds the rules. The last line gives the line of
    the last event it read, which the agent passes to `status` and `reply --to` as `--read`."""
    conv = _conversation(run, _unit(args, run))
    events = conv.events()
    found = open_items(events, conv.items, conv.agent)
    for e, _, extra in found:
        rest = {k: v for k, v in extra.items() if k not in ("step", "closed_by_user")}
        run.out(terminal_json({**e, "status": extra["step"], **rest}))
    last = len(events) - 1
    run.out(f"{len(found)} not done." + (f" Pass --read {last} to status and reply." if last >= 0 else ""))
    return 0


# ---------------------------------------------------------------- the shell


def _json_for_html(value: Any) -> str:
    """JSON that sits in a <script> element: `<`, `>` and `&` escaped, so nothing in it can end the element."""
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def shell(spec: PageSpec) -> str:
    """The page: shell.html with the page's main section and bundled files, and constants escaped. Never record data."""
    title, agent = html.escape(spec.title), html.escape(spec.agent)
    empty = spec.empty or f"Nothing yet. Write to the {spec.agent} below."
    config = {"title": spec.title, "agent": spec.agent, "capabilities": list(spec.capabilities)}
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
        self.guarded(super().setup)

    def handle(self) -> None:
        self.guarded(super().handle)

    def finish(self) -> None:
        self.guarded(super().finish)

    def local(self) -> bool:
        # Only answer requests addressed to this machine, so a web page cannot reach it via DNS rebinding.
        return (self.headers.get("Host") or "").rsplit(":", 1)[0] in ("127.0.0.1", "localhost")

    def send(self, code: int, body: bytes, kind: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
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
        if path in ("/", "/index.html"):
            return self.send(200, shell(self.spec).encode(), CONTENT_TYPES[".html"])
        if path in self.assets:
            kind = CONTENT_TYPES[os.path.splitext(path)[1]]
            return self.send(200, resources.read_bytes(self.assets[path]), kind)
        if path in ("/data", "/events", "/wait") and not self.has_token():
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
            return self.send_json({"total": total, "events": c.events()[after:total]})
        if path == "/wait":
            seconds = urllib.parse.parse_qs(parts.query).get("seconds", ["25"])[0]
            seconds = int(seconds) if seconds.isdigit() and len(seconds) <= 4 else 25
            return self.send(200, str(c.waited(self.after(parts.query), seconds)).encode(), "text/plain")
        return self.send_error(404)

    @answers_any_failure
    def do_POST(self):
        # Only this page may send: the same host and origin, and a JSON body that a cross-site form cannot send.
        origin = self.headers.get("Origin", "")
        if not self.local() or self.path != "/rpc" or origin != "http://" + (self.headers.get("Host") or ""):
            return self.send_error(403)
        if not self.has_token():
            return self.send_json(rpc_error(None, -32001, OUT_OF_DATE))
        if not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return self.send_error(415)
        size = int(self.headers.get("Content-Length") or 0)
        if not 0 < size <= MAX_BODY:
            return self.send_error(413)
        try:
            msg = json.loads(self.rfile.read(size))
        except ValueError:
            return self.send_json(rpc_error(None, -32700, "Parse error"))
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
        streamed = json.dumps({**json.loads(line), LINE: self.conversation.position(line)})
        with contextlib.suppress(OSError):  # a closed stdout is not a failed save
            print(streamed, flush=True)
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


def _serve_arguments(parser: argparse.ArgumentParser) -> None:
    _unit_argument(parser)
    parser.add_argument("--port", type=int, default=0, help="port to serve on (default: any free port)")
    opening = parser.add_mutually_exclusive_group()
    opening.add_argument("--open", action="store_true", help="open the page in a browser")
    opening.add_argument("--no-browser", action="store_true", help="do not open a browser (the default)")
    parser.add_argument("--linger", type=float, default=10, help="seconds to keep serving after the unit stops")
    parser.add_argument("--once", action="store_true", help="serve one request, then exit")


@cli.verb(
    "serve",
    help="serve the unit's live page; prints each action the user takes as one JSON line",
    arguments=_serve_arguments,
)
def serve(args: argparse.Namespace, run: cli.Run) -> int:
    """Check every record, then serve the page until the unit stops (or Ctrl+C). A record that is not valid is a warning
    on stderr: the page still opens and shows it."""
    unit = _unit(args, run)
    for guard in SERVE_GUARDS.get(run.skill.name, []):
        guard(unit)
    spec = spec_of(run.skill)
    docs = load_docs(run.skill)
    notices: list[schema.Error] = []
    for error in schema.check_paths([unit.path], docs=docs, now=run.now(), cutoff=run.info.cutoff, notices=notices):
        run.err(f"warning: {error}")
    for notice in notices:  # a line in the format before this change is reported, not a warning of a bad record
        run.err(f"notice: {notice}")
    conv = Conversation(unit, spec, docs)
    conv.lines()  # a log that cannot be read is refused here, not found by the first request
    try:
        server = make_server(unit, spec, conv, run.info, args.port)
    except OSError as error:  # a port that is taken or not allowed is a refusal with a way out, not a bug
        reason = (error.strerror or type(error).__name__).lower()
        raise paths.refusal(
            unit.label, f"cannot be served on port {args.port} ({reason})", f"serve {unit.label} on a free port"
        ) from None
    url = page_url(server)
    # Printed before the address file is written: a reader that waits for the file and then stops the server has the
    # address already, even if the stop comes before the signal handler below is set.
    run.out(
        f"Each action the user takes is printed here as one JSON line, with its line in the log as {LINE}."
        f" Serving {unit.label} at {url}"
    )  # the address last: no full stop after it
    publish(unit, server)
    if not unit.target(SEEN).exists():  # a resumed run keeps its place, so it still sees what came in while it was away
        paths.write_state(unit, SEEN, b"0")
    if args.open and not webbrowser.open(url):
        run.out(
            "Could not open a browser on this machine. If the user's browser runs on another machine, "
            "this address does not reach it."
        )
    stop_like_ctrl_c()
    serving = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": POLL}, daemon=True)
    try:
        if args.once:
            server.daemon_threads = False  # server_close then waits for the thread that answers, so the answer is sent
            server.handle_request()
            return 0
        serving.start()
        stopped_at = None
        while True:
            time.sleep(TICK)
            try:  # a tick that fails is reported and the next one tries again
                if spec.tick:
                    spec.tick(unit, conv)
                stopped = bool(spec.stopped and spec.stopped(unit))
            except Exception as error:
                run.err(f"page server: tick failed: {type(error).__name__}: {error}")
                continue
            if stopped_at is None and stopped:
                stopped_at = time.time()
            if stopped_at is not None and not stopped:
                stopped_at = None  # reopened
            if stopped_at is not None and time.time() - stopped_at > args.linger:
                run.out("The unit stopped; the page server is exiting. The open page keeps the last state.")
                return 0
    except KeyboardInterrupt:
        return 0
    finally:
        if not args.once and serving.is_alive():
            server.shutdown()
        server.server_close()
        for name in (ADDRESS, TOKEN):
            with contextlib.suppress(OSError, Refused):
                os.unlink(unit.target(name))


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
