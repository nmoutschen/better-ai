"""The verbs that write records: `create`, `add` and `set` (design.md, Command contract).

    better.pyz create <unit> --by <agent>             the head record's fields as JSON on stdin
    better.pyz add <unit> <type> [--by] [--for] [--id]  the record's fields as JSON on stdin; prints the id
    better.pyz set <unit> <id or type> [--for] [--unset <field>]   the fields to change as JSON on stdin

The command stamps `type`, `at` and `by` (and `id`), picks the file from the schemas' `x-files`, validates the record as
`check` does and writes nothing unless it is valid. It reads the target file, and refuses with exit 4 if the file's size
or modification time changed between that read and the write.

Where a record goes comes from the schemas alone:

- `decisions.jsonl`: one line per record, appended;
- `claims/*.json` with `x-id-from-filename`: one file per record, `claims/<id>.json`, created exclusively;
- `logs/*.jsonl`, `logs/*.card.json`: one file per agent, named by `--for`;
- any other `*.json` name: one record in one file, written once by `create` or `add`, changed by `set`.

How an id is assigned comes from `x-id` on the record type's own subschema (see `assign_id`).

A skill package adds what is specific to its skill with three hooks, registered when the package is imported:

    @records.create_step("code-better")             # before create writes: refuse, or return a function to run after
    def copy_spec(ctx: records.CreateContext): ...  # the head and folders are written

    @records.create_step("code-better", existing=True)   # create on a unit that has its head: return True if handled
    def top_up(ctx: records.CreateContext): ...

    @records.add_guard("code-better", "start", "step")   # before add writes records of these types (none: every type)
    def needs_card(ctx: records.AddContext): ...         # raise paths.Refused to refuse
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from . import cli, paths, resources, schema
from .cli import Busy, Run, verb
from .paths import Unit, refusal
from .skill import OWNER_BY_HEAD

STAMPED = ("at", "by", "id")  # fields the command sets, which stdin may not hold
DEADLINE = re.compile(r"^\+(\d{1,9})m$")
TIME = "%Y-%m-%dT%H:%M:%SZ"
BUSY = "the file changed while I worked; run the command again"
TRIES = 1000  # numbers tried for a folder entry before giving up

# ---------------------------------------------------------------- hooks a skill package registers


@dataclass
class CreateContext:
    """What a create step is given. `record` is the validated, stamped head (None for an `existing` step)."""

    run: Run
    unit: Unit
    by: str
    docs: dict
    record: dict | None = None


@dataclass
class AddContext:
    """What an add guard is given: the stamped record, before it is validated, and where it would be written (`path`,
    relative to the unit; `exists` says whether that file is there). `for_agent` is `--for`."""

    run: Run
    unit: Unit
    type: str
    record: dict
    path: str
    exists: bool
    by: str
    for_agent: str | None = None


CREATE_STEPS: dict[str, list[Callable]] = {}
EXISTING_STEPS: dict[str, list[Callable]] = {}
ADD_GUARDS: dict[str, list[tuple[tuple[str, ...], Callable]]] = {}


def create_step(skill: str, *, existing: bool = False):
    """Register a step of `create` for a skill (its name, such as `code-better`). A step runs after the head is
    validated and before anything is written: it may raise `Refused`, and it may return a function that `create` calls
    once the head and the folders are written (such as one that copies a file into the unit). With `existing=True` the
    step runs when the folder already holds this skill's unit instead; it returns True if it dealt with it."""

    def register(function):
        (EXISTING_STEPS if existing else CREATE_STEPS).setdefault(skill, []).append(function)
        return function

    return register


def add_guard(skill: str, *types: str):
    """Register a check made before `add` writes a record of one of `types` (every type if none are named). It raises
    `Refused` to refuse; it writes nothing."""

    def register(function):
        ADD_GUARDS.setdefault(skill, []).append((types, function))
        return function

    return register


# ---------------------------------------------------------------- what each record type maps to


@dataclass(frozen=True)
class Form:
    """How one record type is stored in a unit of one kind."""

    type: str
    schema: str  # the schema's file name
    pattern: str  # relative to the unit: "decisions.jsonl", "claims/*.json", "logs/*.jsonl"
    id: dict | None  # the type's `x-id`
    folder: bool  # one file per record, named by its id (`x-id-from-filename`)
    fields: tuple[str, ...] = ()  # the fields the schema lists for the type, for the message about an unknown one

    @property
    def lines(self) -> bool:
        return self.pattern.endswith(".jsonl")

    @property
    def per_agent(self) -> bool:
        return "*" in self.pattern and not self.folder

    @property
    def single(self) -> bool:
        return not self.lines and not self.folder


@dataclass
class Layout:
    forms: dict[str, Form] = field(default_factory=dict)
    conversation: set[str] = field(default_factory=set)  # types only the page commands write

    def types(self) -> list[str]:
        return sorted(self.forms)


def _unit_pattern(pattern: str, unit: Unit) -> str | None:
    """A schema's `x-files` pattern relative to this unit, or None when it describes a file of another kind of unit: a
    change's `audit/*/findings.jsonl` is `findings.jsonl` in an audit and is not the change's."""
    sub = unit.kind.folder.split("/")[1:]
    parts = pattern.split("/")
    if sub:
        if parts[: len(sub)] == sub and len(parts) > len(sub) + 1 and parts[len(sub)] == "*":
            return "/".join(parts[len(sub) + 1 :])
        return None
    return None if parts[0] in unit.skill.reserved(unit.kind.folder) else pattern


def _types_of(doc: dict) -> dict[str, tuple[dict | None, tuple[str, ...]]]:
    """The record types a schema describes, each with its `x-id` and the fields the schema lists for it: from the top
    level's `type`, and from each `$defs` entry that is a record of one type (so `progress` and `problem` in one file
    can differ)."""
    properties = doc.get("properties", {})
    kind = properties.get("type", {})
    names = [kind["const"]] if "const" in kind else list(kind.get("enum", []))
    top_id = (properties.get("id") or {}).get("x-id")
    top_fields = tuple(properties)
    found: dict[str, tuple[dict | None, tuple[str, ...]]] = {name: (top_id, top_fields) for name in names}
    for name, definition in doc.get("$defs", {}).items():
        if name.startswith("old_") or not isinstance(definition, dict):
            continue
        own = definition.get("properties", {})
        label = (own.get("type") or {}).get("const")
        if "at" in own and isinstance(label, str):
            found[label] = ((own.get("id") or {}).get("x-id") or found.get(label, (top_id, ()))[0], tuple(own))
    return found


def layout(unit: Unit, docs: dict[str, dict]) -> Layout:
    """The record types of this unit's kind, from the loaded schemas, and where each is stored."""
    result = Layout()
    for name in sorted(docs):
        doc = docs[name]
        patterns = doc.get("x-files", [])
        if not patterns or not isinstance(doc, dict):
            continue
        types = _types_of(doc)
        if "conversation.jsonl" in patterns:
            result.conversation |= set(types)
            continue
        for pattern in patterns:
            relative = _unit_pattern(pattern, unit)
            if relative is None:
                continue
            for label, (spec, fields) in types.items():
                result.forms.setdefault(
                    label, Form(label, name, relative, spec, bool(doc.get("x-id-from-filename")), fields)
                )
    return result


def _form(unit: Unit, lay: Layout, label: str) -> Form:
    if label in lay.forms:
        return lay.forms[label]
    if label in lay.conversation:
        raise refusal(
            unit.label,
            f"{label!r} records are written by the page commands (serve, reply, status), never by add or set",
            "use reply or status",
        )
    raise refusal(
        unit.label,
        f"unknown record type {label!r}; the types of a {unit.kind.kind} are {', '.join(lay.types())}",
        f"use one of them: add {unit.label} <type>",
    )


# ---------------------------------------------------------------- reading what the command is given


def _fields(run: Run, unit: Unit) -> dict:
    text = run.stdin_text()
    if not text.strip():
        return {}
    try:
        value = json.loads(text)
    except (ValueError, RecursionError) as error:
        raise refusal(
            unit.label, f"stdin is not JSON ({error})", "pass the fields as one JSON object on stdin"
        ) from None
    if not isinstance(value, dict):
        raise refusal(
            unit.label, f"stdin is a JSON {schema._type_name(value)}, not an object", "pass one JSON object of fields"
        )
    return value


def _own_fields(fields: dict, unit: Unit, label: str, *, ids: bool = True) -> dict:
    """The fields without the ones the command sets. `type` may be given only if it equals `label` (D7)."""
    held = [name for name in STAMPED if name in fields]
    if held:
        raise refusal(
            unit.label,
            f"stdin holds {', '.join(repr(n) for n in held)}, which the command sets",
            "remove " + ("it" if len(held) == 1 else "them") + " from the fields",
        )
    if "type" in fields and fields["type"] != label:
        raise refusal(
            unit.label,
            f"stdin has type {fields['type']!r} but the command names type {label!r}",
            "give one type, the one on the command line",
        )
    return {k: v for k, v in fields.items() if k != "type"}


def _deadline(fields: dict, run: Run, unit: Unit) -> None:
    """`deadline` is `null` or `+<minutes>m`; the latter becomes that time from now."""
    if "deadline" not in fields or fields["deadline"] is None:
        return
    value = fields["deadline"]
    found = DEADLINE.match(value) if isinstance(value, str) else None
    if not found:
        raise refusal(
            unit.label,
            f"deadline {value!r} is neither null nor +<minutes>m",
            'give "+30m" for half an hour from now, or null',
        )
    try:
        fields["deadline"] = (run.now() + timedelta(minutes=int(found.group(1)))).strftime(TIME)
    except OverflowError:
        raise refusal(unit.label, f"deadline {value!r} is too far ahead", "give fewer minutes") from None


def _stamp(run: Run, label: str, by: str, fields: dict, ident: str | None = None) -> dict:
    record = {"type": label, "at": run.now().strftime(TIME), "by": by}
    if ident is not None:
        record["id"] = ident
    return {**record, **fields}


def _agent_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--by", help="who writes the record: your agent name")
    parser.add_argument("--for", dest="for_agent", metavar="AGENT", help="the agent a per-agent file belongs to")


# ---------------------------------------------------------------- reading and writing the target


def _shown(path: Path) -> str:
    relative = os.path.relpath(path)
    return relative if not relative.startswith("..") else str(path)


def _stat(unit: Unit, relative: str) -> tuple[int, int] | None:
    try:
        found = os.stat(unit.target(relative))
    except (FileNotFoundError, NotADirectoryError):
        return None
    return found.st_size, found.st_mtime_ns


def _read(unit: Unit, relative: str, lines: bool) -> tuple[str | None, tuple[int, int] | None]:
    """The text of a file of the unit (None if it is not there) and its size and modification time, read as `check`
    reads: a text that does not parse is read once more. The stat is taken before and after the read and must agree."""
    for _ in range(3):
        before = _stat(unit, relative)
        if before is None:
            return None, None
        try:
            data = paths.read_bytes(unit, relative)
        except FileNotFoundError:
            return None, None
        text = data.decode("utf-8", "surrogateescape")
        if not schema._parses(text, lines):
            time.sleep(schema.PAUSE)
            data = paths.read_bytes(unit, relative)
            text = data.decode("utf-8", "surrogateescape")
        if _stat(unit, relative) == before:
            return text, before
    raise Busy(BUSY)


def _before_write(unit: Unit, relative: str) -> None:
    """A seam for tests: it runs between the read and the check that nothing changed."""


def _still(unit: Unit, relative: str, stat: tuple[int, int] | None) -> None:
    _before_write(unit, relative)
    if _stat(unit, relative) != stat:
        raise Busy(BUSY)


def _encode(text: str) -> bytes:
    return text.encode("utf-8", "surrogateescape")


def _json_line(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False)


def _json_file(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, indent=2) + "\n"


UNKNOWN_FIELD = "not allowed (the schema does not list it)"


def _check(
    run: Run, unit: Unit, relative: str, text: str, line: int, form: Form | None = None
) -> tuple[list[schema.Error], list[schema.Error]]:
    """The errors of line `line` of a file's new text, and (as warnings) those of every other line. Old-format lines
    before the build's cutoff are not warnings. An unknown field on the new line names the fields of the type."""
    docs = schema.load_schemas(*resources.schema_sources(run.info.package))
    path = unit.target(relative)
    notices: list[schema.Error] = []
    found = schema.check_text(path, text, docs, {}, now=run.now(), cutoff=run.info.cutoff, notices=notices)
    shown = _shown(path)
    errors = [e._replace(file=shown) for e in found if e.line == line]
    if form is not None:
        given = [f for f in form.fields if f not in ("type", "at", "by", "id")]
        errors = [
            e._replace(message=f"{e.message}; the fields of {form.type} are {', '.join(given)}")
            if e.message.startswith(UNKNOWN_FIELD) and given
            else e
            for e in errors
        ]
    warnings = [e._replace(file=shown) for e in found if e.line != line]
    return errors, warnings


def _report(run: Run, errors: list[schema.Error], *, new: bool) -> int:
    for error in errors:
        run.out(f"{error.file}:{'new' if new else error.line}: {error.field}: {error.message}")
    return cli.EXIT_REFUSED


def _warn(run: Run, warnings: list[schema.Error]) -> None:
    for warning in warnings:
        run.err(f"warning: {warning}")


# ---------------------------------------------------------------- ids


def assign_id(spec: dict, fields: dict, agent: str | None, existing: list[str]) -> str | list[str]:
    """The next id for a record type whose `x-id` is `spec`, from the ids already there: the highest number for the
    prefix (and the agent, for `{"agent": true}`) plus one. A list of messages if the prefix cannot be known."""
    if "prefix_by" in spec:
        wanted = spec["prefix_by"]
        prefix = spec["map"].get(fields.get(wanted)) if isinstance(fields.get(wanted), str) else None
        if prefix is None:
            return [f"{wanted}: needs one of {', '.join(spec['map'])} for the id to be assigned"]
    else:
        prefix = spec["prefix"]
    stem = f"{prefix}-{agent}-" if spec.get("agent") else prefix
    pattern = re.compile(re.escape(stem) + r"(\d+)$")
    highest = max((int(m.group(1)) for i in existing if (m := pattern.match(i))), default=0)
    return f"{stem}{highest + 1}"


def _ids_of(text: str | None) -> tuple[list[str], int | None]:
    """The ids of a JSONL file's records, and the line number of the first line that does not parse (or None)."""
    ids: list[str] = []
    for number, piece in enumerate(schema._lines(text or ""), 1):
        if not piece.strip():
            continue
        try:
            record = json.loads(piece)
        except (ValueError, RecursionError):
            return ids, number
        if not isinstance(record, dict):
            return ids, number
        if isinstance(record.get("id"), str):
            ids.append(record["id"])
    return ids, None


# ---------------------------------------------------------------- create


def _create_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("unit", help="the new unit, such as .code/my-change")
    parser.add_argument("--by", required=True, help="your agent name")


@verb(
    "create",
    help="make a unit: its head record (fields on stdin), its folders and the git exclusion",
    arguments=_create_arguments,
)
def create(args: argparse.Namespace, run: Run) -> int:
    unit = paths.resolve_unit(args.unit, run.skill, creating=True)
    by = paths.check_by(args.by)
    kind = unit.kind
    if unit.path.exists() and not unit.path.is_dir():
        raise refusal(unit.label, "it exists and is not a folder", "choose another name")
    holds = [n for n in OWNER_BY_HEAD if (unit.path / n).exists() or os.path.islink(unit.path / n)]
    if holds:
        if unit.exists():
            ctx = CreateContext(run, unit, by, schema.load_schemas(*resources.schema_sources(run.info.package)))
            handled = [step(ctx) for step in EXISTING_STEPS.get(run.skill.name, [])]
            if any(handled):
                return cli.EXIT_DONE
        raise refusal(
            unit.label,
            f"it already holds a unit ({holds[0]})",
            f"use add or set on it, or choose another name: set {unit.label} {kind.head_type}",
        )
    fields = _own_fields(_fields(run, unit), unit, kind.head_type)
    _deadline(fields, run, unit)
    record = _stamp(run, kind.head_type, by, {k: v for k, v in fields.items() if k != "id"})
    docs = schema.load_schemas(*resources.schema_sources(run.info.package))
    errors, _ = _check(run, unit, kind.head, _json_file(record), 1, layout(unit, docs).forms.get(kind.head_type))
    if errors:
        return _report(run, errors, new=True)
    ctx = CreateContext(run, unit, by, docs, record)
    after = [done for step in CREATE_STEPS.get(run.skill.name, []) if (done := step(ctx))]
    paths.make_unit_folder(unit)
    for folder in kind.folders:
        paths.make_folder(unit, folder)
    try:
        paths.create_exclusive(unit, kind.head, _encode(_json_file(record)))
    except FileExistsError:
        raise Busy(BUSY) from None
    for done in after:
        done()
    if run.skill.exclude:
        result = paths.add_exclude(unit, run.skill.exclude)
        if result.startswith("skipped"):
            run.out(f"git exclusion {result}")
    run.out(f"created {unit.label}")
    return cli.EXIT_DONE


# ---------------------------------------------------------------- add


def _add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("unit", help="the unit, such as .code/my-change")
    parser.add_argument("type", help="the record type, such as decision")
    _agent_arguments(parser)
    parser.add_argument("--id", help="the record's name, for the types whose ids are chosen (a perspective)")


def _names(args: argparse.Namespace, unit: Unit, form: Form) -> tuple[str, str | None]:
    """`by` and `for` for an add, checked. `--by` defaults to `--for`."""
    for_agent = paths.check_agent(args.for_agent, "--for name") if args.for_agent is not None else None
    if args.by is None and for_agent is None:
        raise refusal(
            unit.label, "--by is missing", "add --by <your agent name>, or --for <agent> for a per-agent file"
        )
    by = paths.check_by(args.by if args.by is not None else for_agent)
    agent_ids = bool(form.id and form.id.get("agent"))
    if form.per_agent and for_agent is None:
        raise refusal(
            unit.label, f"{form.type} records are kept one file per agent, so --for is missing", "add --for <agent>"
        )
    if for_agent is not None and not (form.per_agent or agent_ids):
        raise refusal(unit.label, f"{form.type} records are not kept per agent, so --for is not used", "remove --for")
    return by, for_agent


def _chosen_id(args: argparse.Namespace, unit: Unit, form: Form, lay: Layout) -> str | None:
    caller = bool(form.id and form.id.get("from") == "caller")
    if args.id is None:
        if caller:
            raise refusal(unit.label, f"{form.type} records are named by you, so --id is missing", "add --id <name>")
        return None
    if not caller:
        raise refusal(
            unit.label,
            f"{form.type} ids are assigned by the command, so --id is not accepted",
            "remove --id",
        )
    paths.check_agent(args.id, "--id name")
    if args.id in lay.forms or args.id in lay.conversation:
        raise refusal(unit.label, f"--id {args.id!r} is a record type of this unit", "choose another name")
    return args.id


@verb(
    "add",
    help="write a new record of a type (fields on stdin) and print its id",
    arguments=_add_arguments,
)
def add(args: argparse.Namespace, run: Run) -> int:
    unit = paths.resolve_unit(args.unit, run.skill)
    docs = schema.load_schemas(*resources.schema_sources(run.info.package))
    lay = layout(unit, docs)
    form = _form(unit, lay, args.type)
    by, for_agent = _names(args, unit, form)
    chosen = _chosen_id(args, unit, form, lay)
    fields = _own_fields(_fields(run, unit), unit, form.type)
    _deadline(fields, run, unit)
    agent = for_agent or by
    if form.folder:
        return _add_entry(run, unit, form, by, for_agent, agent, fields)
    relative = form.pattern.replace("*", for_agent) if form.per_agent else form.pattern
    text, stat = _read(unit, relative, form.lines)
    if form.single:
        if text is not None:
            raise refusal(
                unit.label,
                f"{relative} already exists",
                f"use set {unit.label} {form.type}" + (f" --for {for_agent}" if for_agent else ""),
            )
        record = _stamp(run, form.type, by, fields, chosen)
        _guards(run, unit, form, record, relative, False, by, for_agent)
        errors, warnings = _check(run, unit, relative, _json_file(record), 1, form)
        if errors:
            return _report(run, errors, new=True)
        _make_parent(unit, relative)
        _still(unit, relative, stat)
        paths.write_atomic(unit, relative, _encode(_json_file(record)))
        return _done(run, relative, chosen)
    ident = chosen
    ids, bad = _ids_of(text)
    if chosen is not None and chosen in ids:
        raise refusal(unit.label, f"{chosen!r} already exists in {relative}", f"use set {unit.label} {chosen}")
    if form.id is not None and chosen is None:
        if bad is not None:
            raise refusal(
                unit.label,
                f"{relative} line {bad} does not parse, so the next id cannot be known",
                "fix or remove that line, then run the command again",
            )
        made = assign_id(form.id, fields, agent, ids)
        if isinstance(made, list):
            return _report(
                run, [schema.Error(_shown(unit.target(relative)), 0, *m.split(": ", 1)) for m in made], new=True
            )
        ident = made
    record = _stamp(run, form.type, by, fields, ident)
    _guards(run, unit, form, record, relative, text is not None, by, for_agent)
    prefix = text if not text or text.endswith("\n") else text + "\n"
    new_text = (prefix or "") + _json_line(record) + "\n"
    errors, warnings = _check(run, unit, relative, new_text, len(schema._lines(new_text)), form)
    if errors:
        return _report(run, errors, new=True)
    _make_parent(unit, relative)
    _still(unit, relative, stat)
    paths.append_line(unit, relative, _encode(("\n" if text and not text.endswith("\n") else "") + _json_line(record)))
    _warn(run, warnings)
    return _done(run, relative, ident)


def _make_parent(unit: Unit, relative: str) -> None:
    parent = os.path.dirname(relative)
    if parent:
        paths.make_folder(unit, parent)


def _guards(run, unit, form, record, relative, exists, by, for_agent) -> None:
    ctx = AddContext(run, unit, form.type, record, relative, exists, by, for_agent)
    for types, guard in ADD_GUARDS.get(run.skill.name, []):
        if not types or form.type in types:
            guard(ctx)


def _done(run: Run, relative: str, ident: str | None) -> int:
    run.out(ident if ident is not None else relative)
    return cli.EXIT_DONE


def _add_entry(run: Run, unit: Unit, form: Form, by: str, for_agent: str | None, agent: str, fields: dict) -> int:
    """A folder entry: `<folder>/<id>.json`, created exclusively, on the next number if the name is taken."""
    folder = form.pattern.rsplit("/", 1)[0]
    paths.check_agent(agent)
    names: list[str] = []
    directory = unit.target(folder)
    if directory.is_dir():
        names = [p.name.removesuffix(".json") for p in directory.iterdir() if p.name.endswith(".json")]
    made = assign_id(form.id, fields, agent, names)
    if isinstance(made, list):
        return _report(run, [schema.Error(folder, 0, *m.split(": ", 1)) for m in made], new=True)
    stem = made.rsplit("-", 1)[0] + "-"
    number = int(made.rsplit("-", 1)[1])
    for _ in range(TRIES):
        ident = f"{stem}{number}"
        paths.check_pattern(ident, r"[A-Za-z][A-Za-z0-9-]*-\d+", "generated id")
        relative = f"{folder}/{ident}.json"
        record = _stamp(run, form.type, by, fields, ident)
        _guards(run, unit, form, record, relative, False, by, for_agent)
        errors, warnings = _check(run, unit, relative, _json_file(record), 1, form)
        if errors:
            return _report(run, errors, new=True)
        _make_parent(unit, relative)
        _before_write(unit, relative)
        try:
            paths.create_exclusive(unit, relative, _encode(_json_file(record)))
        except FileExistsError:
            number += 1
            continue
        _warn(run, warnings)
        return _done(run, relative, ident)
    raise refusal(unit.label, f"no free number for {stem}n in {folder}", "remove files from that folder")


# ---------------------------------------------------------------- set


def _set_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("unit", help="the unit, such as .code/my-change")
    parser.add_argument("ref", help="the id of a record (D3), or the type of a single-record file (code)")
    parser.add_argument("--for", dest="for_agent", metavar="AGENT", help="the agent, for a per-agent file such as card")
    parser.add_argument("--unset", action="append", default=[], metavar="FIELD", help="remove a field (repeatable)")


@dataclass
class Found:
    relative: str
    text: str
    stat: tuple[int, int] | None
    index: int | None  # the line of a JSONL file; None for a single record file
    record: dict


def _locate(unit: Unit, lay: Layout, ref: str, for_agent: str | None) -> Found:
    if ref in lay.forms or ref in lay.conversation:
        form = _form(unit, lay, ref)
        if not form.single:
            raise refusal(
                unit.label, f"{ref} records are many in one place", f"name one by its id: set {unit.label} <id>"
            )
        if form.per_agent and for_agent is None:
            raise refusal(unit.label, f"{ref} records are kept one file per agent", "add --for <agent>")
        relative = form.pattern.replace("*", for_agent) if form.per_agent else form.pattern
        text, stat = _read(unit, relative, False)
        if text is None:
            raise refusal(unit.label, f"no {ref} record is written yet", f"use add {unit.label} {ref}")
        return Found(relative, text, stat, None, _loads_object(unit, relative, text))
    hits: list[Found] = []
    unparsable: list[str] = []
    seen: set[str] = set()
    for form in lay.forms.values():
        if form.id is None or form.pattern in seen:
            continue
        seen.add(form.pattern)
        for found in sorted(unit.path.glob(form.pattern)):
            relative = found.relative_to(unit.path).as_posix()
            text, stat = _read(unit, relative, form.lines)
            if text is None:
                continue
            if form.lines:
                records = schema._lines(text)
                matched = None
                for number, piece in enumerate(records):
                    try:
                        value = json.loads(piece) if piece.strip() else None
                    except (ValueError, RecursionError):
                        unparsable.append(f"{relative}:{number + 1}")
                        continue
                    if isinstance(value, dict) and value.get("id") == ref:
                        matched = (number, value)
                if matched:
                    hits.append(Found(relative, text, stat, matched[0], matched[1]))
            else:
                try:
                    value = json.loads(text)
                except (ValueError, RecursionError):
                    unparsable.append(relative)
                    continue
                if isinstance(value, dict) and value.get("id") == ref:
                    hits.append(Found(relative, text, stat, None, value))
    if len(hits) > 1:
        raise refusal(
            unit.label,
            f"{ref} is in more than one file ({', '.join(h.relative for h in hits)})",
            "fix the duplicate by hand",
        )
    if not hits:
        extra = f"; {unparsable[0]} does not parse and may hold it" if unparsable else ""
        raise refusal(
            unit.label,
            f"no record with id {ref!r} in this unit (set looks only in the unit's own files{extra})",
            f"check the id, or add it: add {unit.label} <type>",
        )
    return hits[0]


def _loads_object(unit: Unit, relative: str, text: str) -> dict:
    try:
        value = json.loads(text)
    except (ValueError, RecursionError):
        raise refusal(unit.label, f"{relative} does not parse", f"fix it by hand, then check {unit.label}") from None
    if not isinstance(value, dict):
        raise refusal(unit.label, f"{relative} is not a JSON object", f"fix it by hand, then check {unit.label}")
    return value


def _merged(record: dict, patch: dict, unsets: list[str], keep_null: bool) -> dict:
    new = dict(record)
    for key, value in patch.items():
        if value is None and not keep_null:
            new.pop(key, None)
        else:
            new[key] = value
    for key in unsets:
        new.pop(key, None)
    return new


@verb(
    "set",
    help="change fields of a record, by id or by type (fields on stdin); at, by and id stay",
    arguments=_set_arguments,
)
def set_(args: argparse.Namespace, run: Run) -> int:
    unit = paths.resolve_unit(args.unit, run.skill)
    docs = schema.load_schemas(*resources.schema_sources(run.info.package))
    lay = layout(unit, docs)
    for_agent = paths.check_agent(args.for_agent, "--for name") if args.for_agent is not None else None
    found = _locate(unit, lay, args.ref, for_agent)
    label = found.record.get("type")
    patch = _own_fields(_fields(run, unit), unit, label if isinstance(label, str) else "")
    _deadline(patch, run, unit)
    first = _merged(found.record, patch, args.unset, keep_null=True)
    candidates = [first]
    if any(v is None for v in patch.values()):
        candidates.append(_merged(found.record, patch, args.unset, keep_null=False))
    chosen = None
    for record in candidates:
        errors, warnings = _check_set(run, unit, found, record, lay.forms.get(found.record.get("type")))
        if chosen is None:
            chosen = (record, errors, warnings)
        if not errors:
            chosen = (record, errors, warnings)
            break
    record, errors, warnings = chosen
    if errors:
        return _report(run, errors, new=False)
    if record == found.record:
        run.out(args.ref)
        return cli.EXIT_DONE
    _still(unit, found.relative, found.stat)
    paths.write_atomic(unit, found.relative, _encode(_new_text(found, record)))
    _warn(run, warnings)
    run.out(args.ref)
    return cli.EXIT_DONE


def _new_text(found: Found, record: dict) -> str:
    if found.index is None:
        return _json_file(record)
    pieces = found.text.split("\n")
    carriage = "\r" if pieces[found.index].endswith("\r") else ""
    pieces[found.index] = _json_line(record) + carriage
    return "\n".join(pieces)


def _check_set(
    run: Run, unit: Unit, found: Found, record: dict, form: Form | None
) -> tuple[list[schema.Error], list[schema.Error]]:
    return _check(run, unit, found.relative, _new_text(found, record), (found.index or 0) + 1, form)
