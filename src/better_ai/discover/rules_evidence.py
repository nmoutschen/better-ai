"""discover-better: the rules for evidence and sources: the quote flow, the URL rule and the evidence statuses.

A quote becomes evidence in four steps. An analyst adds a `source` (a page it read) and an `evidence` that is
`checking`, with no verifier. The coordinator sets a `verifier` on it. The verifier reads the page itself, from the
shell, and sets the outcome with `set --by <verifier> --raw <file>`: `counts` only with the span it copied, which must
occur in that file, and a quote that occurs in the span. `better.pyz` computes the file's `sha256`; it makes no network
call and reads no page but that file.

Who may change an evidence's status:

| From | To | Who | When |
|---|---|---|---|
| `checking` | `counts`, `unverified`, `not reachable` | the current `verifier` | always |
| `not reachable` | `checking` | the coordinator | `tries` holds fewer than two verifiers; it sets a new `verifier` |
| `checking` | `unverified` ("verifier did not finish") | the coordinator | `since` is older than 30 minutes |
| any | `removed` | the coordinator | the reason names the user's request (a `remove` or `redact` event, or an answered decision about the evidence) |

Every other change is refused, with its next action. Evidence from the user (a source with origin `you`) counts at once:
only the coordinator adds it, with a `given` that points to the user's `add_evidence` event or holds their typed words.

Where each rule runs:

- `check`, and `add` and `set` before they write: the hooks `discover-source` and `discover-evidence` (`x-check` in the
  schemas), which look at one record and the files around it: the URL rule, the setting's `said_by_role` and
  `summary`, what `counts` needs, and what evidence from the user is;
- `add` guards: who writes (the coordinator, or the analyst that is the current `checker` of every item the evidence
  bears on), how new evidence starts, repeated evidence, and one record per page event;
- the `set` step: the statuses above, who sets `verifier` and `since`, `tries`, and the check of `--raw`.

A rule that needs the writer or the history of a record cannot run on a record at rest, so `check` holds what a
record must be to count and `add` and `set` hold how it got there.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import unicodedata
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .. import paths, records, schema

SKILL = "discover-better"
TIMEOUT = 30  # minutes a verifier may run before the coordinator may give up on it
TIMEOUT_REASON = "verifier did not finish"
MAX_TRIES = 2  # a `not reachable` evidence is tried again only while fewer verifiers than this were started
CHECKED = ("checked_read", "span", "sha256")  # what `counts` holds and nothing else does
SOURCE_ID = re.compile(r"S-[\w.-]+-\d+")
USER_ONLY = ("verifier", "tries", "since", *CHECKED)  # fields the user's own evidence never has


# ---------------------------------------------------------------- words and addresses


def normalise(text: str) -> str:
    """The words of `text` for comparing: lower case, punctuation and runs of whitespace as one space."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    return re.sub(r"[\W_]+", " ", folded).strip()


def quote_in_span(quote: str, span: str) -> bool:
    """The quote's words occur in the span as whole words, after whitespace and punctuation are normalised."""
    words = normalise(quote)
    return bool(words) and f" {words} " in f" {normalise(span)} "


def _short_form(host: str) -> ipaddress.IPv4Address | None:
    """An IPv4 address written the short ways a client reads: 127.1, 0x7f.0.0.1, 0177.0.0.1, 2130706433."""
    parts = host.split(".")
    if not 1 <= len(parts) <= 4 or not all(re.fullmatch(r"0[xX][0-9a-fA-F]+|[0-9]+", p) for p in parts):
        return None
    try:
        numbers = [
            int(p, 16) if p[:2] in ("0x", "0X") else int(p, 8) if p[0] == "0" and len(p) > 1 else int(p) for p in parts
        ]
    except ValueError:  # an octal part with an 8 or 9
        return None
    *head, last = numbers
    if any(n > 255 for n in head) or last >= 256 ** (5 - len(parts)):
        return None
    value = last
    for position, n in enumerate(head):
        value += n << (8 * (3 - position))
    return ipaddress.IPv4Address(value)


def _literal(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """The address a host names when it is an IP literal, in any form a client reads: dotted, short, octal, hex, decimal."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return _short_form(host)
    if ip.version == 6 and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    if ip.version == 6 and int(ip) >> 32 == 0:  # ::/96, an IPv4 address in IPv6 dress
        return ipaddress.IPv4Address(int(ip))
    return ip


def _host(host: str) -> str | None:
    """A host as a client reads it: an IP literal as it is, a name through IDNA (full-width digits and dots, other
    scripts) in lower case. None if it is not a valid host."""
    try:
        ipaddress.ip_address(host)
    except ValueError:
        try:
            return host.encode("idna").decode("ascii").lower()
        except UnicodeError:
            return None
    return host.lower()


def url_problem(url: str) -> str | None:
    """Why a source's address is refused, or None. An http or https address of a public host only: not localhost, and
    not a loopback, private, link-local or otherwise non-public IP literal. Offline: a name that resolves to a private
    address is the verifier's to catch at each redirect."""
    if re.search(r"[\s\\\x00-\x1f]", url):
        return "has a backslash, space or control character: write the plain address"
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError:
        return "is not a valid address: give the page's http or https address"
    if parts.scheme not in ("http", "https"):
        return f"must be an http or https address, not {parts.scheme or 'no scheme'}: give the page's http or https address"
    if not host:
        return "has no host: give the page's http or https address"
    host = _host(host.rstrip("."))
    if not host:
        return "is not a valid host name: give the page's http or https address"
    if host == "localhost" or host.endswith(".localhost"):
        return "is localhost: read a public page, or give the page text as your own evidence"
    ip = _literal(host)
    if ip is not None and not ip.is_global:
        return f"is {host}, a loopback, private or link-local address: use the page's public address"
    return None


# ---------------------------------------------------------------- reading the unit


def _json(unit: paths.Unit, relative: str) -> Any:
    try:
        return json.loads(unit.target(relative).read_text(encoding="utf-8"))
    except (OSError, ValueError, paths.Refused):
        return None


def _lines(unit: paths.Unit, relative: str) -> list[dict]:
    try:
        text = unit.target(relative).read_text(encoding="utf-8")
    except (OSError, paths.Refused):
        return []
    found = []
    for line in text.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            found.append(value)
    return found


def _folder(unit: paths.Unit, name: str) -> Iterator[tuple[str, dict]]:
    """Each record file of a folder of the unit, as (relative path, record), in name order."""
    try:
        base = unit.target(name)
        files = sorted(base.glob("*.json")) if base.is_dir() else []
    except paths.Refused:
        return
    for file in files:
        if file.is_symlink():
            continue
        value = _json(unit, f"{name}/{file.name}")
        if isinstance(value, dict):
            yield f"{name}/{file.name}", value


def _coordinator(unit: paths.Unit) -> str:
    head = _json(unit, unit.kind.head)
    name = head.get("coordinator") if isinstance(head, dict) else None
    if not isinstance(name, str) or not name:
        raise paths.refusal(unit.label, f"{unit.kind.head} does not name the coordinator", f"run check {unit.label}")
    return name


def _source(unit: paths.Unit, ident: Any) -> dict | None:
    if not isinstance(ident, str) or not SOURCE_ID.fullmatch(ident):
        return None
    value = _json(unit, f"sources/{ident}.json")
    return value if isinstance(value, dict) else None


def _origin(source: dict | None) -> str | None:
    origin = source.get("origin") if isinstance(source, dict) else None
    kind = origin.get("type") if isinstance(origin, dict) else None
    return kind if kind in ("web", "you") else None


# ---------------------------------------------------------------- hooks: what a record at rest must be


@schema.hook("discover-source")
def _source_at_rest(record: dict, ctx: schema.Context) -> list[tuple[str, str]]:
    """The URL rule, and the role a source from you needs where the setting is internal."""
    origin = record.get("origin")
    if not isinstance(origin, dict):
        return []
    if origin.get("type") == "web" and isinstance(origin.get("url"), str):
        why = url_problem(origin["url"])
        if why:
            return [("origin.url", why)]
    head = ctx.read_json("../discover.json")
    internal = isinstance(head, dict) and head.get("setting") == "internal"
    if origin.get("type") == "you" and internal and not record.get("said_by_role"):
        return [("said_by_role", "needed for a source from you in an internal discovery: say who said it, by role")]
    return []


@schema.hook("discover-evidence")
def _evidence_at_rest(record: dict, ctx: schema.Context) -> list[tuple[str, str]]:
    """What evidence must be to be in the state it is in: what `counts` needs, and what the user's own evidence is."""
    problems: list[tuple[str, str]] = []
    head = ctx.read_json("../discover.json")
    source_id = record.get("source")
    source = (
        ctx.read_json(f"../sources/{source_id}.json")
        if isinstance(source_id, str) and SOURCE_ID.fullmatch(source_id)
        else None
    )
    kind = _origin(source)
    words = record.get("words") if isinstance(record.get("words"), dict) else {}
    status = record.get("status")
    if words.get("type") == "event":
        given = source["origin"].get("given") if kind == "you" else None
        if not isinstance(given, dict) or given.get("type") != "page" or given.get("event") != words.get("event"):
            problems.append(("words", "event words need a source from you that points to the same page event"))
    if kind == "you":
        if status not in ("counts", "removed"):
            problems.append(
                ("status", "evidence from you counts at once: its status is counts, or removed once the user asks")
            )
        for name in USER_ONLY:
            if name in record:
                problems.append((name, "evidence from you is not checked by a verifier: leave it out"))
        coordinator = head.get("coordinator") if isinstance(head, dict) else None
        if coordinator and record.get("by") != coordinator:
            problems.append(("by", f"evidence from you is added by the coordinator, {coordinator}"))
        if isinstance(head, dict) and head.get("setting") == "internal" and not record.get("summary"):
            problems.append(("summary", "needed for evidence from you in an internal discovery: the words by role"))
    elif kind == "web" and status == "counts":
        problems += _counting(record, words, head.get("coordinator") if isinstance(head, dict) else None)
    return problems


def _counting(record: dict, words: dict, coordinator: str | None) -> list[tuple[str, str]]:
    """Web evidence that counts: a verifier other than its analyst read the page raw and the span holds the quote."""
    problems = []
    verifier = record.get("verifier")
    if not verifier:
        problems.append(
            ("verifier", "counts only after a verifier read the page: set a verifier and have it set the outcome")
        )
    elif verifier == record.get("by"):
        problems.append(("verifier", "the analyst that added the evidence cannot be the verifier that counts it"))
    elif verifier == coordinator:
        problems.append(("verifier", "the coordinator is never the verifier: a verifier agent reads the page"))
    if record.get("checked_read") != "raw":
        problems.append(("checked_read", "counts needs checked_read raw: a verifier reads the page itself"))
    span = record.get("span")
    if words.get("type") != "quote" or not isinstance(words.get("text"), str):
        problems.append(("words", "web evidence counts as a quote"))
    elif isinstance(span, str) and not quote_in_span(words["text"], span):
        problems.append(("span", "the quote does not occur in the span: a verifier copies the span that holds it"))
    return problems


# ---------------------------------------------------------------- add guards


def _refuse(unit: paths.Unit, reason: str, then: str | None = None) -> paths.Refused:
    return paths.refusal(unit.label, reason, then)


@records.add_guard(SKILL, "source")
def _source_by_the_coordinator_if_from_you(ctx: records.AddContext) -> None:
    """A source from you holds the user's own words or event: only the coordinator adds it."""
    origin = ctx.record.get("origin")
    if isinstance(origin, dict) and origin.get("type") == "you":
        coordinator = _coordinator(ctx.unit)
        if ctx.by != coordinator:
            raise _refuse(
                ctx.unit,
                f"only the coordinator ({coordinator}) adds a source from you",
                "stop: tell the coordinator what the user gave, in your hand-back",
            )


@records.add_guard(SKILL, "evidence")
def _evidence_writer_and_start(ctx: records.AddContext) -> None:
    """Who adds evidence, how it starts, and that it is not repeated."""
    unit, record, by = ctx.unit, ctx.record, ctx.by
    coordinator = _coordinator(unit)
    kind = _origin(_source(unit, record.get("source")))
    if kind == "you" and by != coordinator:
        raise _refuse(
            unit,
            f"only the coordinator ({coordinator}) adds evidence from you",
            "stop: tell the coordinator what the user gave, in your hand-back",
        )
    if kind == "web":
        started = [n for n in (*USER_ONLY, "reason") if n in record]
        if record.get("status") != "checking" or started:
            what = "status " + str(record.get("status")) if record.get("status") != "checking" else ", ".join(started)
            raise _refuse(
                unit,
                f"new evidence from a web page starts checking, with no verifier fields ({what})",
                'add it with "status": "checking" and without verifier, tries, since, checked_read, span, sha256 or '
                "reason; the coordinator starts a verifier",
            )
    if by != coordinator:
        _must_be_checker(unit, by, record)
    _not_repeated(unit, record)


def _must_be_checker(unit: paths.Unit, by: str, record: dict) -> None:
    if not record.get("bears_on"):
        raise _refuse(
            unit,
            f"evidence added by {by} must bear on an item it checks: bears_on is empty",
            "name the items it bears on, or leave the evidence to the coordinator",
        )
    items = {i.get("id"): i for i in _lines(unit, "items.jsonl")}
    for bears in record.get("bears_on") or []:
        item = items.get(bears.get("item")) if isinstance(bears, dict) else None
        if item is None:
            continue  # a pointer to no item is the schema's to report
        checker = item.get("checker")
        if checker != by:
            now = f"{checker} checks it" if checker else "no analyst checks it now"
            raise _refuse(
                unit,
                f"you ({by}) are not the checker of {item['id']}: {now}",
                "stop: you were replaced; add no more records, and say so in your hand-back",
            )


def _not_repeated(unit: paths.Unit, record: dict, skip: str | None = None) -> None:
    words = record.get("words")
    if not isinstance(words, dict):
        return
    mine = _comparable(words)
    for _, other in _folder(unit, "evidence"):
        if (
            other.get("id") != skip
            and other.get("source") == record.get("source")
            and mine is not None
            and _comparable(other.get("words")) == mine
        ):
            note = " (removed)" if other.get("status") == "removed" else ""
            raise _refuse(
                unit,
                f"already recorded as {other.get('id')}{note}: the same source and the same words",
                f"use {other.get('id')}, or add the evidence with other words",
            )


def _comparable(words: Any) -> tuple[str, str] | None:
    if not isinstance(words, dict):
        return None
    if words.get("type") == "quote" and isinstance(words.get("text"), str):
        return "quote", normalise(words["text"])
    if words.get("type") == "event" and isinstance(words.get("event"), str):
        return "event", words["event"]
    return None


def _page_events(value: Any) -> Iterator[str]:
    """Each page event a record points to: `{type: page or event, event: <id>}`, wherever it is in the record."""
    if isinstance(value, dict):
        if value.get("type") in ("page", "event") and isinstance(value.get("event"), str):
            yield value["event"]
        for inner in value.values():
            yield from _page_events(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _page_events(inner)


def _unit_records(unit: paths.Unit) -> Iterator[tuple[str, int, dict]]:
    """Every record that may point to a page event: the unit's JSONL files but the conversation and the logs, and its
    source and evidence files."""
    try:
        files = sorted(p for p in unit.path.glob("*.jsonl") if p.name != "conversation.jsonl" and not p.is_symlink())
    except OSError:
        files = []
    for file in files:
        for number, record in enumerate(_lines(unit, file.name), 1):
            yield file.name, number, record
    for folder in ("sources", "evidence"):
        for relative, record in _folder(unit, folder):
            yield relative, 1, record


@records.add_guard(SKILL)
def _a_page_event_backs_one_record(ctx: records.AddContext) -> None:
    """A page event is one thing the user did: one record points to it. The evidence of a source from the user is the
    one exception, since it states the same event as its source."""
    events = set(_page_events(ctx.record))
    if not events:
        return
    for relative, number, other in _unit_records(ctx.unit):
        own_source = (
            ctx.type == "evidence" and other.get("type") == "source" and other.get("id") == ctx.record.get("source")
        )
        if own_source:
            continue
        for event in events & set(_page_events(other)):
            name = other.get("id") or f"line {number}"
            raise _refuse(
                ctx.unit,
                f"page event {event} is already used by {name} ({relative})",
                "a page event backs one record: use another event, or change that record",
            )


# ---------------------------------------------------------------- the set step


def _since(record: dict) -> datetime | None:
    try:
        return datetime.strptime(record["since"], records.TIME).replace(tzinfo=timezone.utc)
    except (KeyError, TypeError, ValueError):
        return None


def _names_the_request(unit: paths.Unit, ident: str, reason: Any) -> bool:
    """The reason names the user's request to remove this evidence: a `remove` or `redact` event of theirs, or a
    decision about it that they answered with exactly "remove <id>"."""
    if not isinstance(reason, str):
        return False
    wanted = [
        e.get("id")
        for e in _lines(unit, "conversation.jsonl")
        if e.get("by") == "user"
        and (
            (e.get("type") == "remove" and e.get("record") == ident)
            or (e.get("type") == "redact" and e.get("evidence") == ident)
        )
    ]
    for decision in _lines(unit, "decisions.jsonl"):
        about = decision.get("about")
        answer = decision.get("answer")
        said = answer.get("text") if isinstance(answer, dict) else None
        asked = isinstance(about, dict) and about.get("type") == "evidence" and about.get("evidence") == ident
        if decision.get("status") == "answered" and asked and said == f"remove {ident}":
            wanted.append(decision.get("id"))
    return any(isinstance(w, str) and re.search(rf"(?<![\w-]){re.escape(w)}(?![\w-])", reason) for w in wanted)


def _raw_text(ctx: records.SetContext) -> tuple[str, str]:
    """The page the verifier read, as the file given with --raw says: its text and its sha256."""
    if ctx.raw is None:
        raise _refuse(
            ctx.unit,
            "counts needs the page the verifier read",
            "save the raw page to a file outside .discover/ and run again with --raw <file>",
        )
    ctx.raw_read = True
    path = Path(ctx.raw)
    try:
        if not path.is_file():
            raise OSError("not a file")
        data = path.read_bytes()
    except OSError as error:
        raise _refuse(ctx.unit, f"cannot read --raw {ctx.raw} ({error})", "give the file the verifier saved") from None
    return data.decode("utf-8", "replace"), hashlib.sha256(data).hexdigest()


def _count(ctx: records.SetContext, by: str) -> None:
    """Make the patch of a set to `counts` complete, or refuse. The verifier gives `checked_read` and `span`; the
    command adds the hash of the file."""
    record, patch, ident = ctx.record, ctx.patch, ctx.record["id"]
    if by == record.get("by"):
        raise _refuse(
            ctx.unit,
            f"you ({by}) added {ident}: a verifier cannot count the evidence it added",
            "stop: the coordinator starts another verifier",
        )
    if patch.get("checked_read") != "raw":
        raise _refuse(
            ctx.unit,
            "counts needs checked_read raw",
            'set "checked_read": "raw" with the span you copied from the page you read yourself',
        )
    span = patch.get("span")
    if not isinstance(span, str) or not span:
        raise _refuse(ctx.unit, "counts needs the span you copied from the page", 'set "span" to that text')
    text, digest = _raw_text(ctx)
    if span not in text:
        raise _refuse(
            ctx.unit,
            f"the span does not occur in {ctx.raw}",
            "copy the span from the page file exactly, or set unverified or not reachable with a reason",
        )
    words = record.get("words") if isinstance(record.get("words"), dict) else {}
    if not isinstance(words.get("text"), str) or not quote_in_span(words["text"], span):
        raise _refuse(
            ctx.unit,
            "the quote does not occur in the span",
            'copy the part of the page that holds the quote, or set unverified with the reason "reworded"',
        )
    patch["sha256"] = digest


def _who(ctx: records.SetContext, by: str, coordinator: str, old: str, new: str) -> paths.Refused:
    """The refusal of a change of status the writer may not make."""
    record = ctx.record
    ident, verifier = record["id"], record.get("verifier")
    tries = record.get("tries") or []
    if by != coordinator and verifier and by in tries and by != verifier:
        return _refuse(ctx.unit, f"you were replaced by {verifier}: stop")
    if old == "checking" and new in ("counts", "unverified", "not reachable"):
        if by == coordinator:
            how = (
                f"only the verifier {verifier} sets the outcome; after {TIMEOUT} minutes of its silence set unverified "
                f'with the reason "{TIMEOUT_REASON}"'
                if verifier
                else "no verifier is started yet: set a verifier first"
            )
            return _refuse(ctx.unit, f"{ident} is checking: {how}")
        return _refuse(
            ctx.unit,
            f"you ({by}) are not the verifier of {ident}" + (f"; {verifier} is" if verifier else ""),
            "stop: only the verifier the coordinator started sets the outcome",
        )
    allowed = {
        "checking": "its verifier sets counts, unverified or not reachable",
        "not reachable": f"the coordinator may set checking again with a new verifier while fewer than {MAX_TRIES} tried",
        "counts": "nothing but removed, by the coordinator, at the user's request",
        "unverified": "nothing but removed, by the coordinator, at the user's request",
        "removed": "nothing: removed evidence stays removed",
    }.get(old, "nothing")
    return _refuse(
        ctx.unit,
        f"{ident} cannot go from {old} to {new} (by {by}): from {old} {allowed}",
        "add new evidence if the words are to be checked again",
    )


UNSET = object()  # a field `set` removes, with --unset or with null
STAMPED = ("type", "at", "by", "id")
# The write table of evidence: who may change each field, and in which status. Nothing else may be changed. A field
# not here is refused. "analyst" is the analyst that added the evidence.
FIXED_AFTER_CHECKING = ("source", "words", "bears_on", "kind", "about")  # coordinator or analyst, while checking, alone
EVIDENCE_FIELDS = (
    *FIXED_AFTER_CHECKING,
    "summary",  # the coordinator, while checking or counting
    "status",  # the quote flow's table
    "verifier",  # the coordinator, as it starts a verifier, while checking
    "since",  # the coordinator, with a verifier, while checking
    "tries",  # better.pyz alone
    "reason",  # only with the change of status that holds it
    "checked_read",  # only with counts, from the verifier
    "span",  # only with counts, from the verifier
    "sha256",  # better.pyz alone, from --raw
)
SOURCE_FIELDS = ("origin", "title", "said_by_role")  # origin: never; title: coordinator or analyst; role: coordinator


def _changes(record: dict, patch: dict, unsets: tuple[str, ...]) -> dict[str, Any]:
    """The fields a set really changes, as new value or UNSET: a value the record has already is not a change, and
    neither is removing a field it does not have."""
    found: dict[str, Any] = {}
    for name, value in patch.items():
        if value is None:
            value = UNSET
        if value is UNSET:
            if name in record:
                found[name] = UNSET
        elif name not in record or record[name] != value or name == "verifier":  # a verifier is always a start
            found[name] = value
    for name in unsets:
        if name in record:
            found[name] = UNSET
    return found


def _no_unset(ctx: records.SetContext, name: str) -> paths.Refused:
    return _refuse(
        ctx.unit,
        f"{name} of {ctx.record['id']} cannot be removed",
        "leave --unset and null out: better.pyz drops the fields a change of status makes stale",
    )


def _write_table(
    ctx: records.SetContext, changes: dict[str, Any], by: str, coordinator: str, old: str, new: str
) -> None:
    """The write table of evidence, for every field the set changes but `status`: who, and in which status."""
    unit, record = ctx.unit, ctx.record
    ident, verifier = record["id"], record.get("verifier")
    tries = list(record.get("tries") or ([verifier] if verifier else []))
    for name, value in changes.items():
        if name == "status":
            continue
        if name in STAMPED or name not in EVIDENCE_FIELDS:
            raise _refuse(
                unit, f"{name} of {ident} cannot be changed", "change only the fields the evidence's format lists"
            )
        if value is UNSET:
            raise _no_unset(ctx, name)
        if name == "sha256":
            raise _refuse(unit, "sha256 is computed by better.pyz from --raw", "leave sha256 out of the fields")
        if name == "tries":
            raise _refuse(unit, "tries is kept by better.pyz", "leave tries out of the fields")
        if name in FIXED_AFTER_CHECKING:
            if old != "checking":
                raise _refuse(
                    unit,
                    f"{name} of {ident} is fixed once the evidence leaves checking (it is {old})",
                    "add new evidence with the new words, source or items",
                )
            if new != old:
                raise _refuse(
                    unit, f"{name} cannot change in the set that changes the status", f"set {name} on its own"
                )
            if by not in (coordinator, record.get("by")):
                raise _refuse(
                    unit,
                    f"only the coordinator ({coordinator}) or {record.get('by')}, who added {ident}, changes {name}",
                    "stop: tell the coordinator, in your hand-back",
                )
            merged = {**record, name: value}
            if name in ("source", "words"):
                _not_repeated(unit, merged, ident)
            if name == "bears_on" and by != coordinator:
                _must_be_checker(unit, by, merged)
        elif name == "summary":
            if by != coordinator or old not in ("checking", "counts"):
                raise _refuse(
                    unit,
                    f"only the coordinator ({coordinator}) writes summary, while {ident} is checking or counts",
                    "ask the coordinator",
                )
        elif name in ("verifier", "since"):
            if by != coordinator:
                raise _refuse(
                    unit,
                    f"only the coordinator ({coordinator}) sets verifier or since",
                    "stop: you cannot start or replace a verifier",
                )
            if new != "checking":
                raise _refuse(unit, f"{name} is set only while {ident} is checking", f"{ident} is {new}")
            if name == "verifier" and value == coordinator:
                raise _refuse(
                    unit, "the coordinator is never the verifier", "start a verifier agent with a name of its own"
                )
            if name == "verifier" and value in tries:
                raise _refuse(
                    unit,
                    f"{value} is already in tries of {ident} ({', '.join(tries)})",
                    "start a verifier with a new name",
                )
        elif name == "reason":
            if new == old or new not in ("unverified", "not reachable", "removed"):
                raise _refuse(
                    unit,
                    f"reason of {ident} is set only with the change of status that needs it",
                    "set the status and the reason together",
                )
        elif name in ("checked_read", "span") and not (old == "checking" and new == "counts"):
            raise _refuse(
                unit,
                f"{name} is set only when a verifier counts the evidence",
                "set counts with checked_read, the span and --raw",
            )


@records.set_step(SKILL)
def evidence_status_rules(ctx: records.SetContext) -> None:
    """The write table and the status table, on every set of evidence: who changes which field in which status, how
    the status changes, `tries`, `since` and the check of `--raw`."""
    record, patch, by, unit = ctx.record, ctx.patch, ctx.by, ctx.unit
    if record.get("type") != "evidence":
        return
    ident = record["id"]
    coordinator = _coordinator(unit)
    if by is None:
        raise _refuse(unit, f"setting {ident} needs --by", "run again with --by <your agent name>")
    verifier = record.get("verifier")
    if by != coordinator and verifier and by in (record.get("tries") or []) and by != verifier:
        raise _refuse(unit, f"you were replaced by {verifier}: stop")
    changes = _changes(record, patch, ctx.unsets)
    if changes.get("status") is UNSET:
        raise _no_unset(ctx, "status")
    old, new = record.get("status"), patch.get("status", record.get("status"))
    tries = list(record.get("tries") or ([verifier] if verifier else []))
    now = ctx.run.now()
    _write_table(ctx, changes, by, coordinator, old, new)

    if new != old:
        if new == "removed":
            if by != coordinator:
                raise _refuse(unit, f"only the coordinator ({coordinator}) removes evidence", "ask the coordinator")
            if not _names_the_request(unit, ident, patch.get("reason")):
                raise _refuse(
                    unit,
                    f"the reason must name the user's request to remove {ident}",
                    'give a reason that holds the id of their remove or redact event, or of a decision they answered "remove '
                    + ident
                    + '"',
                )
            for name in CHECKED:
                if name in record:
                    patch[name] = None
        elif old == "checking" and new in ("counts", "unverified", "not reachable"):
            if by == verifier:
                pass
            elif new == "unverified" and by == coordinator and patch.get("reason") == TIMEOUT_REASON:
                started = _since(record)
                if started is None or (now - started).total_seconds() < TIMEOUT * 60:
                    waited = f"{int((now - started).total_seconds() // 60)} minutes ago" if started else "not at all"
                    raise _refuse(
                        unit,
                        f"the verifier of {ident} started {waited}: give it {TIMEOUT} minutes",
                        f"run again once since is older than {TIMEOUT} minutes",
                    )
            else:
                raise _who(ctx, by, coordinator, old, new)
        elif old == "not reachable" and new == "checking":
            if by != coordinator or len(tries) >= MAX_TRIES:
                if by == coordinator:
                    raise _refuse(
                        unit,
                        f"{ident} was tried by {len(tries)} verifiers, two at most ({', '.join(tries)}): that is enough",
                        'set it unverified with a reason, such as "not reachable twice"',
                    )
                raise _who(ctx, by, coordinator, old, new)
            if "verifier" not in patch:
                raise _refuse(unit, f"a new try needs a new verifier for {ident}", 'set "verifier" to a new name')
            patch["reason"] = None
        else:
            raise _who(ctx, by, coordinator, old, new)

    if new == "counts" and old == "checking":
        _count(ctx, by)
    elif ctx.raw is not None:
        raise _refuse(unit, "--raw is for setting counts", "leave --raw out")
    if "verifier" in patch:
        patch["tries"] = [*tries, patch["verifier"]]
        patch.setdefault("since", now.strftime(records.TIME))
    if old == "checking" and new != "checking" and "since" in record | patch:
        patch["since"] = None


@records.set_step(SKILL)
def source_write_table(ctx: records.SetContext) -> None:
    """The write table of a source: its origin is fixed once added; its title is the coordinator's or its analyst's;
    the role of the user's source is the coordinator's. Nothing is removed."""
    record, by, unit = ctx.record, ctx.by, ctx.unit
    if record.get("type") != "source":
        return
    ident = record["id"]
    coordinator = _coordinator(unit)
    if by is None:
        raise _refuse(unit, f"setting {ident} needs --by", "run again with --by <your agent name>")
    for name, value in _changes(record, ctx.patch, ctx.unsets).items():
        if name not in SOURCE_FIELDS:
            raise _refuse(
                unit, f"{name} of {ident} cannot be changed", "change only the fields the source's format lists"
            )
        if value is UNSET:
            raise _refuse(unit, f"{name} of {ident} cannot be removed", "leave --unset out")
        if name == "origin":
            raise _refuse(unit, f"the origin of {ident} is fixed once added", "add a new source for the new page")
        allowed = (coordinator,) if name == "said_by_role" else (coordinator, record.get("by"))
        if by not in allowed:
            raise _refuse(
                unit,
                f"only the coordinator ({coordinator}) changes {name} of {ident}"
                + ("" if name == "said_by_role" else f" or {record.get('by')}, who added it"),
                "stop: tell the coordinator, in your hand-back",
            )
