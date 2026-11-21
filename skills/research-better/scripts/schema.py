#!/usr/bin/env python3
"""Checks the files a skill writes for agent bookkeeping against their JSON Schemas, in one place.

    python3 scripts/schema.py check <path>... [--schemas DIR]

A path is a file, or a folder whose files are all checked. Each error is one line, `<file>:<line>: <field>: <message>`,
and the exit code is 1 if there is any error and 0 if there is none. A JSONL file
is checked line by line, a JSON file as one record; `<line>` is 1 for a JSON file. The page's own scripts call
`check_paths` instead of keeping checks of their own; a script keeps only checks that need its own knowledge, such as
whether a slide can be drawn. A script that writes one record at a time, as page.py does for an event, calls
`check_record` with the names of the schemas the record must meet before it writes the record. A page that still shows a
record that failed its checks calls `strip_invalid`, which drops the fields the errors name.

Each skill carries an identical copy of this file in `scripts/`, with `schemas/base.schema.json` next to it in
`schemas/`, as it does page.py; the Scripts workflow fails if the copies differ. Standard library only.

The schemas live in `--schemas DIR`, by default the `schemas/` folder next to `scripts/`. A schema describes one
record: one line of a JSONL file, or one JSON file. These keywords of JSON Schema are supported, and any other keyword
in a schema is an error, so a rule is never silently ignored: type, const, enum, pattern, minLength, minItems, maxItems, minimum, maximum, required,
properties, additionalProperties, items, prefixItems, allOf, anyOf, not, if/then/else and $ref (to `#/...` in the same schema, or to
`<name>.schema.json#/...` in the schemas folder, such as the shared `base.schema.json`). `title`, `description`,
`$schema`, `$id`, `$comment`, `$defs`, `examples` and `default` are notes. The schemas are checked as a whole when
they load: an unsupported keyword, a `type` that is not a type name, a `pattern` that is not a regular expression, a
`required` that is not a list of names, an extension without what it needs, or an `x-check` no hook answers to is an
error even where no record reaches it.
A file that does not parse is read once more before the parse error is reported, in case it was caught mid-write.

An error under if/then/else names the rule: `reason: required when status is "blocked"`.

Extensions, which other JSON Schema tools ignore:

- `x-files` (schema root): the files the schema describes, as paths from the end of the file's path, with `*` as in a
  shell: `["tasks.jsonl"]`, `["logs/*.jsonl"]`, `["questions/*.json"]`. The most specific pattern wins. When several
  schemas share the most specific pattern, a record must meet each of them: a page's `conversation.jsonl` is checked
  against the shared `conversation.schema.json` and the page's own `<page>-events.schema.json`.
- `x-versioned` (schema root): true when a line may reuse an `id`, as in a page conversation, where the latest line is
  the item's current version. Otherwise an `id` repeated in a file is an error.
- `x-id-from-filename` (schema root): true when the file is one entry of a folder, named `<id>.json`.
- `x-points-to` (a string field): `{"file": "spec.jsonl", "type": "spec"}`. The value must be the `id` of a record
  of that type in that file. `file` is relative to the folder of the file being checked and may use `..`; a name that
  ends in `/` is a folder of `<id>.json` files; `type` may be a list. Otherwise the error says it is dangling.
  `file` may also be `{"from": "code.json", "field": "design.folder", "name": "spec.jsonl", "else": "spec.jsonl"}`:
  `name` in the repo-relative folder (the repo root is the nearest folder up with `.git`) that `field`, a dotted path
  into the JSON file `from`, holds, as when `code.json` points to an architect folder; `else` when it holds none.
- `x-mode-sets` (a string field): `{"file": "code.json", "field": "mode", "coordinate": [...], "other": [...]}`. The
  value must be in the set named by the `field` of the JSON file `file`: the key that equals that value, or `other`.
  `{stem}` in `file` stands for the checked file's name without its extension: `{stem}.card.json`.
- `x-differs-from` (a field): the name of a sibling field; the two values must differ.
- `x-check` (anywhere a schema applies to a record, usually in a `then`): the name of a hook, a function in this file
  for the rules across records that the keywords above cannot say.

To add a hook, write `def name(record, ctx) -> list[tuple[str, str]]` here, decorate it with `@hook("name")`, and
copy this file to every skill. `record` is the record the schema applies to; `ctx.directory` is the folder of the
file being checked, and `ctx.read_json(path)` and `ctx.read_jsonl(path)` read a file relative to it (None if it does
not exist). It returns `(field, message)` for each problem, or an empty list. A schema names a hook with `x-check`, and
a name no hook has is an error in the schema.
"""

from __future__ import annotations

import argparse
import copy
import fnmatch
import json
import os
import re
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

ANNOTATIONS = {"$schema", "$id", "$comment", "$defs", "title", "description", "examples", "default"}
KEYWORDS = {
    "type",
    "const",
    "enum",
    "pattern",
    "minLength",
    "minItems",
    "maxItems",
    "minimum",
    "maximum",
    "required",
    "properties",
    "additionalProperties",
    "items",
    "prefixItems",
    "allOf",
    "anyOf",
    "not",
    "if",
    "then",
    "else",
    "$ref",
}
EXTENSIONS = {
    "x-files",
    "x-versioned",
    "x-id-from-filename",
    "x-points-to",
    "x-mode-sets",
    "x-differs-from",
    "x-check",
}
TYPE_NAMES = {"string", "integer", "number", "boolean", "null", "object", "array"}
PAUSE = 0.05  # seconds before a file that failed to parse is read once more
ROOT = "(record)"
SKIPPED_FOLDERS = {"__pycache__", "node_modules"}


class SchemaError(Exception):
    """A schema that cannot be applied: an unsupported keyword, an unknown $ref or hook, a missing schemas folder."""


class Error(NamedTuple):
    file: str
    line: int
    field: str
    message: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: {self.field}: {self.message}"


class Problem(NamedTuple):
    """One problem in a record. `kind` is "required", "not allowed" or "cross" (it needs another file) or "" (a shape).
    `named` is true once an if/then/else has put its rule in the message, so an outer rule leaves it alone."""

    field: str
    message: str
    kind: str = ""
    named: bool = False


HOOKS: dict[str, Callable[[Any, Context], list[tuple[str, str]]]] = {}


def hook(name: str):
    def register(function):
        HOOKS[name] = function
        return function

    return register


# ---------------------------------------------------------------- reading files


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parses(text: str, lines: bool) -> bool:
    try:
        for piece in _lines(text) if lines else [text]:
            if piece.strip() or not lines:
                json.loads(piece)
    except ValueError:
        return False
    return True


def read_checked(path: Path, lines: bool) -> str:
    """The text of a JSON or JSONL file. If it does not parse, the file may have been caught mid-write: read it once
    more and use that read, so a parse error is reported only if the second read fails too."""
    try:
        text: str | None = read_text(path)
    except UnicodeDecodeError:  # a multi-byte character cut by the write in progress
        text = None
    if text is None or not _parses(text, lines):
        time.sleep(PAUSE)
        text = read_text(path)
    return text


class Context:
    """The files around the one being checked, read once each: what pointers, mode sets and hooks look at."""

    def __init__(self, directory: Path, name: str, cache: dict[str, Any]):
        self.directory = directory
        self.stem = name.removesuffix(".jsonl").removesuffix(".json")
        self._cache = cache

    def path(self, relative: str) -> Path:
        return Path(os.path.normpath(self.directory / relative.replace("{stem}", self.stem)))

    def repo_root(self) -> Path | None:
        for folder in (self.directory, *self.directory.parents):
            if (folder / ".git").exists():
                return folder
        return None

    def target(self, file: Any) -> tuple[str | None, str]:
        """The file a pointer looks in, and how to show it. A name is used as it is; an object
        `{"from": "code.json", "field": "design.folder", "name": "spec.jsonl", "else": "spec.jsonl"}` names `name`
        in the repo-relative folder that `field` of the JSON file `from` holds, or `else` if it holds none."""
        if isinstance(file, str):
            return file, file
        missing = {"from", "field", "name", "else"} - set(file)
        if missing:
            raise SchemaError(f"x-points-to file {file!r} lacks {', '.join(sorted(missing))}")
        value: Any = self.read_json(file["from"])
        for part in file["field"].split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if not isinstance(value, str) or not value:
            return file["else"], file["else"]
        shown = f"{value.rstrip('/')}/{file['name']}"
        root = self.repo_root()
        if root is None:
            return None, f"cannot find the repo root (a folder with .git) to find {shown}"
        return str(root / shown), shown

    def read_json(self, relative: str) -> Any:
        path = self.path(relative)
        key = f"json:{path}"
        if key not in self._cache:
            try:
                self._cache[key] = json.loads(read_checked(path, False))
            except (OSError, ValueError):
                self._cache[key] = None
        return self._cache[key]

    def read_jsonl(self, relative: str) -> list[Any] | None:
        path = self.path(relative)
        key = f"jsonl:{path}"
        if key not in self._cache:
            try:
                text = read_checked(path, True)
            except (OSError, UnicodeDecodeError):
                self._cache[key] = None
            else:
                self._cache[key] = [_loads(line) for line in _lines(text) if line.strip()]
        return self._cache[key]

    def ids(self, relative: str) -> dict[str, set[str]] | None:
        """The records a pointer can name, as id -> record types; None if the file or folder does not exist."""
        path = self.path(relative)
        key = f"ids:{path}"
        if key not in self._cache:
            if relative.endswith("/"):
                records = None
                if path.is_dir():
                    records = [self.read_json(f"{relative}{p.name}") for p in sorted(path.glob("*.json"))]
            elif relative.endswith(".jsonl"):
                records = self.read_jsonl(relative)
            else:
                records = [self.read_json(relative)] if path.exists() else None
            found: dict[str, set[str]] | None = None
            if records is not None:
                found = {}
                for record in records:
                    if isinstance(record, dict) and isinstance(record.get("id"), str):
                        found.setdefault(record["id"], set()).add(str(record.get("type")))
            self._cache[key] = found
        return self._cache[key]


def _lines(text: str) -> list[str]:
    """The lines of a JSONL file: split on \\n only (U+2028 and the like may sit inside a string), without a final \\r
    and without the empty piece after the last newline."""
    pieces = [piece.removesuffix("\r") for piece in text.split("\n")]
    if pieces and pieces[-1] == "":
        pieces.pop()
    return pieces


def _loads(text: str) -> Any:
    try:
        return json.loads(text)
    except ValueError:
        return None


# ---------------------------------------------------------------- the validator


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def _is_type(value: Any, name: str) -> bool:
    actual = _type_name(value)
    return actual == name or (name == "number" and actual == "integer")


def _equal(a: Any, b: Any) -> bool:
    return _type_name(a) == _type_name(b) and a == b


def _show(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _join(path: tuple, part: str | int) -> tuple:
    return (*path, part)


def _render(path: tuple) -> str:
    out = ""
    for part in path:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}" if out else part
    return out or ROOT


def _structural(problems: list[Problem]) -> list[Problem]:
    return [p for p in problems if p.kind != "cross"]


def _condition(schema: dict) -> str:
    """The `if` of a rule in words, for the message: `status is "blocked"`."""
    parts = []
    described = set()
    for name, sub in schema.get("properties", {}).items():
        if isinstance(sub, dict) and "const" in sub:
            parts.append(f"{name} is {_show(sub['const'])}")
        elif isinstance(sub, dict) and "enum" in sub:
            parts.append(f"{name} is one of {', '.join(_show(v) for v in sub['enum'])}")
        else:
            continue
        described.add(name)
    parts += [f"{name} is present" for name in schema.get("required", []) if name not in described]
    absent = _required_only(schema["not"]) if isinstance(schema.get("not"), dict) else None
    parts += [f"{name} is absent" for name in absent or []]
    return " and ".join(parts) or "its condition holds"


def _required_only(schema: Any) -> list[str] | None:
    if isinstance(schema, dict) and set(schema) == {"required"}:
        return list(schema["required"])
    return None


class Validator:
    """`hooks` says what `x-check` does: "on" runs the hooks with the other cross-record rules, "off" skips them, and
    "only" runs nothing but them. `validate_instance` and `check_file` run "off", then "only" on a record that has no
    shape errors, so a hook never sees a wrongly typed value."""

    def __init__(self, docs: dict[str, dict], context: Context | None = None, hooks: str = "on"):
        self.docs = docs
        self.context = context
        self.hooks = hooks

    def resolve(self, ref: str, doc: dict) -> tuple[Any, dict]:
        name, _, fragment = ref.partition("#")
        target = doc if not name else self.docs.get(name)
        if target is None:
            raise SchemaError(f"$ref {ref!r}: no schema named {name!r} in the schemas folder")
        node = target
        for part in [p for p in fragment.split("/") if p]:
            part = part.replace("~1", "/").replace("~0", "~")
            try:
                node = node[part]
            except (KeyError, TypeError, IndexError):
                raise SchemaError(f"$ref {ref!r}: nothing at {part!r}") from None
        return node, target

    def validate(self, value: Any, schema: Any, path: tuple, doc: dict, parent: Any = None) -> list[Problem]:
        if not isinstance(schema, dict):
            raise SchemaError(f"a schema must be an object, got {_show(schema)}")
        for keyword in schema:
            if keyword not in KEYWORDS | ANNOTATIONS | EXTENSIONS:
                raise SchemaError(f"unsupported keyword {keyword!r} in a schema")
        problems: list[Problem] = []
        at = _render(path)

        if "$ref" in schema:
            target, target_doc = self.resolve(schema["$ref"], doc)
            problems += self.validate(value, target, path, target_doc, parent)

        if "type" in schema:
            names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
            if not any(_is_type(value, n) for n in names):
                problems.append(Problem(at, f"expected {' or '.join(names)}, got {_type_name(value)}"))
        if "const" in schema and not _equal(value, schema["const"]):
            problems.append(Problem(at, f"must be {_show(schema['const'])}"))
        if "enum" in schema and not any(_equal(value, v) for v in schema["enum"]):
            problems.append(Problem(at, f"must be one of {', '.join(_show(v) for v in schema['enum'])}"))
        if isinstance(value, str):
            if "pattern" in schema and not re.search(schema["pattern"], value):
                problems.append(Problem(at, f"must match {schema['pattern']}"))
            if "minLength" in schema and len(value) < schema["minLength"]:
                n = schema["minLength"]
                problems.append(Problem(at, f"must have at least {n} character{'' if n == 1 else 's'}"))
        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                n = schema["minItems"]
                problems.append(Problem(at, f"must have at least {n} item{'' if n == 1 else 's'}"))
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                n = schema["maxItems"]
                problems.append(Problem(at, f"must have at most {n} item{'' if n == 1 else 's'}"))
            prefix = schema.get("prefixItems", [])
            for i, sub in enumerate(prefix[: len(value)]):
                problems += self.validate(value[i], sub, _join(path, i), doc)
            if "items" in schema:
                for i in range(len(prefix), len(value)):
                    problems += self.validate(value[i], schema["items"], _join(path, i), doc)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                problems.append(Problem(at, f"must be at least {_show(schema['minimum'])}"))
            if "maximum" in schema and value > schema["maximum"]:
                problems.append(Problem(at, f"must be at most {_show(schema['maximum'])}"))
        if isinstance(value, dict):
            problems += self._object(value, schema, path, doc)

        for sub in schema.get("allOf", []):
            problems += self.validate(value, sub, path, doc, parent)
        if "anyOf" in schema:
            problems += self._any_of(value, schema["anyOf"], path, doc, parent)
        if "not" in schema:
            problems += self._not(value, schema["not"], path, doc, parent)
        if "if" in schema:
            problems += self._conditional(value, schema, path, doc, parent)

        if self.context is not None:
            problems += self._cross(value, schema, path, parent)
        return problems

    def _object(self, value: dict, schema: dict, path: tuple, doc: dict) -> list[Problem]:
        problems = []
        for name in schema.get("required", []):
            if name not in value:
                problems.append(Problem(_render(_join(path, name)), "required", "required"))
        properties = schema.get("properties", {})
        for name, sub in properties.items():
            if name in value:
                problems += self.validate(value[name], sub, _join(path, name), doc, value)
        extra = schema.get("additionalProperties", True)
        for name in value:
            if name in properties:
                continue
            if extra is False:
                where = _render(_join(path, name))
                problems.append(Problem(where, "not allowed (the schema does not list it)", "not allowed"))
            elif extra is not True:
                problems += self.validate(value[name], extra, _join(path, name), doc, value)
        return problems

    def _any_of(self, value: Any, branches: list, path: tuple, doc: dict, parent: Any) -> list[Problem]:
        results = [self.validate(value, branch, path, doc, parent) for branch in branches]
        for result in results:
            if not _structural(result):
                return result
        reasons = "; ".join(f"{r[0].field}: {r[0].message}" if r else "no reason" for r in map(_structural, results))
        return [Problem(_render(path), f"matches none of the allowed shapes ({reasons})")]

    def _not(self, value: Any, sub: Any, path: tuple, doc: dict, parent: Any) -> list[Problem]:
        if not isinstance(sub, dict):
            raise SchemaError(f"a schema must be an object, got {_show(sub)}")
        if isinstance(value, dict):
            shapes = [sub] if "required" in sub else sub.get("anyOf") if set(sub) == {"anyOf"} else None
            names = [_required_only(s) for s in shapes] if shapes else [None]
            if all(n is not None for n in names):
                present = [n for group in names for n in group if all(m in value for m in group)]
                return [Problem(_render(_join(path, n)), "not allowed", "not allowed") for n in dict.fromkeys(present)]
        if not _structural(self.validate(value, sub, path, doc, parent)):
            return [Problem(_render(path), "must not match the excluded shape")]
        return []

    def _conditional(self, value: Any, schema: dict, path: tuple, doc: dict, parent: Any) -> list[Problem]:
        condition = _condition(schema["if"]) if isinstance(schema["if"], dict) else "its condition holds"
        if not _structural(self.validate(value, schema["if"], path, doc, parent)):
            branch, word = schema.get("then"), "when"
        else:
            branch, word = schema.get("else"), "unless"
        if branch is None:
            return []
        problems = []
        for problem in self.validate(value, branch, path, doc, parent):
            if problem.named or problem.kind == "cross":
                problems.append(problem)
                continue
            if problem.kind == "required":
                message = f"required {word} {condition}"
            elif problem.kind == "not allowed" and problem.message == "not allowed":
                message = f"not allowed {word} {condition}"
            else:
                message = f"{problem.message} ({word} {condition})"
            problems.append(Problem(problem.field, message, problem.kind, True))
        return problems

    def _cross(self, value: Any, schema: dict, path: tuple, parent: Any) -> list[Problem]:
        context = self.context
        at = _render(path)
        problems = []
        if self.hooks != "only":
            if "x-points-to" in schema and isinstance(value, str):
                problems += self._points_to(value, schema["x-points-to"], at)
            if (
                "x-mode-sets" in schema
                and isinstance(value, str)
                and not ("enum" in schema and value not in schema["enum"])
            ):
                problems += self._mode_sets(value, schema["x-mode-sets"], at)
            if "x-differs-from" in schema and isinstance(parent, dict):
                other = schema["x-differs-from"]
                if other in parent and _equal(parent[other], value):
                    problems.append(Problem(at, f"must differ from {other} ({_show(value)})", "cross"))
        if "x-check" in schema and isinstance(value, dict) and self.hooks != "off":
            name = schema["x-check"]
            if name not in HOOKS:
                raise SchemaError(f"x-check {name!r}: schema.py has no hook of that name")
            try:
                found = HOOKS[name](value, context)
            except Exception:  # a hook is code: whatever it meets, the answer is an error, not a traceback
                return [*problems, Problem(ROOT, f"check failed: {name}", "cross")]
            for field, message in found:
                problems.append(Problem(_render(_join(path, field)) if path else field, message, "cross"))
        return problems

    def _points_to(self, value: str, rule: dict, at: str) -> list[Problem]:
        relative, shown = self.context.target(rule["file"])
        wanted = rule["type"] if isinstance(rule["type"], list) else [rule["type"]]
        if relative is None:
            return [Problem(at, shown, "cross")]
        known = self.context.ids(relative)
        if known is None:
            return [Problem(at, f"dangling: {shown} does not exist", "cross")]
        if not known.get(value, set()) & set(wanted):
            kinds = " or ".join(wanted)
            return [Problem(at, f"dangling: {_show(value)} is not a {kinds} record in {shown}", "cross")]
        return []

    def _mode_sets(self, value: str, rule: dict, at: str) -> list[Problem]:
        relative = rule["file"].replace("{stem}", self.context.stem)
        field = rule["field"]
        record = self.context.read_json(relative)
        if not isinstance(record, dict):
            return [Problem(at, f"cannot be checked: {relative} does not exist or is not valid JSON", "cross")]
        mode = record.get(field)
        sets = {k: v for k, v in rule.items() if k not in ("file", "field")}
        allowed = sets.get(mode) if isinstance(mode, str) and mode in sets else sets.get("other")
        if allowed is None or not isinstance(mode, str):
            return [Problem(at, f"cannot be checked: {relative} has no usable {field}", "cross")]
        if value not in allowed:
            return [
                Problem(
                    at,
                    f"{_show(value)} is not allowed when {field} is {_show(mode)} in {relative} "
                    f"(allowed: {', '.join(allowed)})",
                    "cross",
                )
            ]
        return []


def validate_instance(value: Any, schema: dict, docs: dict[str, dict], context: Context | None = None) -> list[Problem]:
    """The problems of one value against one schema; `docs` holds the schemas a $ref can name, by file name. The hooks
    run only when the value has no shape error."""
    return validate_record(value, [schema], docs, context)


def validate_record(value: Any, schemas: list[dict], docs: dict[str, dict], context: Context | None) -> list[Problem]:
    """The problems of one record against each of its schemas: first everything but the hooks, then, if the record has
    no shape error, the hooks, whose findings come last."""
    first = [p for schema in schemas for p in Validator(docs, context, "off").validate(value, schema, (), schema)]
    if context is None or any(p.kind != "cross" for p in first):
        return first
    hooked = [p for schema in schemas for p in Validator(docs, context, "only").validate(value, schema, (), schema)]
    return first + [p for p in hooked if p.kind == "cross"]


# ---------------------------------------------------------------- hooks


@hook("verified-needs-passing-verifier")
def _verified_needs_passing_verifier(record: dict, context: Context) -> list[tuple[str, str]]:
    """A task is `verified` only when its latest verifier (a `logs/<agent>.card.json` with role verifier and this
    task) ended its `logs/<agent>.jsonl` with a handed_back line whose result is passes."""
    task = record.get("id")
    cards = []
    for card_path in sorted(context.path("logs").glob("*.card.json")):
        card = context.read_json(f"logs/{card_path.name}")
        if isinstance(card, dict) and card.get("role") == "verifier" and card.get("task") == task:
            cards.append((str(card.get("at")), card_path.name.removesuffix(".card.json")))
    if not cards:
        return [("status", f'"verified" needs a verifier card for {task} in logs/')]
    agent = max(cards)[1]
    lines = context.read_jsonl(f"logs/{agent}.jsonl") or []
    last = lines[-1] if lines else None
    need = f'"verified" needs the latest verifier of {task} ({agent}) to hand back "passes"'
    if not isinstance(last, dict) or last.get("type") != "handed_back":
        return [("status", f"{need}; it has not handed back")]
    if last.get("result") != "passes":
        return [("status", f"{need}; it handed back {_show(last.get('result'))}")]
    return []


def _is_num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _show_overview_labels(panel: dict) -> list:
    """The labels a later panel's `focus` may name: those of the overview panel's steps, events, nodes or groups."""

    def listed(key: str) -> list:
        found = panel.get(key)
        return found if isinstance(found, list) else []

    def labels(key: str) -> list:
        return [x.get("label") for x in listed(key) if isinstance(x, dict)]

    kind = panel.get("kind")
    if kind == "flow":
        return labels("steps")
    if kind == "timeline":
        return labels("events")
    if kind == "concept":
        return labels("nodes")
    found = []
    for group in listed("groups"):
        if isinstance(group, dict):
            inside = group.get("items")
            found += [group.get("label"), *map(str, inside if isinstance(inside, list) else [])]
    return found


def _show_visual(v: dict, where: str, document_sections: Any) -> list[tuple[str, str]]:
    """What one visual refers to inside itself: the node an edge names, the set a region names, the cells of a row."""
    problems: list[tuple[str, str]] = []
    kind = v.get("kind")

    def items(key: str) -> list:
        found = v.get(key)
        return found if isinstance(found, list) else []

    if kind == "map" and not (v.get("sections") or document_sections):
        problems.append((f"{where}.sections", "a map needs 'sections', or a top-level 'document' with 'sections'"))
    if kind == "concept":
        ids = {n["id"] for n in items("nodes") if isinstance(n, dict) and isinstance(n.get("id"), str)}
        for j, edge in enumerate(items("edges")):
            for end in ("from", "to"):
                if isinstance(edge, dict) and isinstance(edge.get(end), str) and edge[end] not in ids:
                    problems.append((f"{where}.edges[{j}].{end}", "names no node id of 'nodes'"))
    if kind == "sets":
        names = {n for n in items("sets") if isinstance(n, str)}
        for j, region in enumerate(items("regions")):
            ins = region.get("in") if isinstance(region, dict) else None
            if isinstance(ins, list) and not all(n in names for n in ins if isinstance(n, str)):
                problems.append((f"{where}.regions[{j}].in", "names a set that 'sets' does not list"))
    if kind == "lanes":
        actors = {a for a in items("actors") if isinstance(a, str)}
        for j, step in enumerate(items("steps")):
            if isinstance(step, dict) and isinstance(step.get("actor"), str) and step["actor"] not in actors:
                problems.append((f"{where}.steps[{j}].actor", "is not one of 'actors'"))
    if kind in ("matrix", "table"):
        columns = items("columns")
        for j, row in enumerate(items("rows")):
            cells = row if kind == "table" else row.get("cells") if isinstance(row, dict) else None
            if isinstance(cells, list) and len(cells) != len(columns):
                field = f"{where}.rows[{j}]" + (".cells" if kind == "matrix" else "")
                problems.append((field, f"has {len(cells)} cells for {len(columns)} columns"))
    if kind == "tree" and isinstance(v.get("root"), dict):

        def walk(node: dict, path: str) -> None:
            children = node.get("children") if isinstance(node.get("children"), list) else []
            kids = [k for k in children if isinstance(k, dict)]
            if kids and _is_num(node.get("value")) and all(_is_num(k.get("value")) for k in kids):
                total = sum(k["value"] for k in kids)
                if abs(total - node["value"]) > 1e-9 * max(1, abs(node["value"])) and total > node["value"]:
                    problems.append((path, f"its children sum to {total:g}, more than its value {node['value']:g}"))
            for j, kid in enumerate(children):
                if isinstance(kid, dict):
                    walk(kid, f"{path}.children[{j}]")

        walk(v["root"], f"{where}.root")
    return problems


@hook("show_spec")
def _show_spec(record: dict, context: Context) -> list[tuple[str, str]]:
    """What a show-better spec's panels say about each other and about themselves: a visual's references, an
    action's target panel, one overview, and the focus labels it holds."""
    panels = record.get("panels")
    if not isinstance(panels, list):
        return []
    document = record.get("document")
    sections = document.get("sections") if isinstance(document, dict) else None
    problems: list[tuple[str, str]] = []
    overview: tuple[int, list] | None = None  # the panel number and its labels, once a panel sets overview
    for i, panel in enumerate(panels):
        if not isinstance(panel, dict):
            continue
        at = f"panels[{i}]"
        template = panel.get("template") or "visual"
        if template == "visual":
            problems += _show_visual(panel, at, sections)
        elif template == "compare":
            for side in ("a", "b"):
                if isinstance(panel.get(side), dict):
                    problems += _show_visual(panel[side], f"{at}.{side}", sections)
        elif template == "title" and isinstance(panel.get("actions"), list):
            for j, action in enumerate(panel["actions"]):
                target = action.get("panel") if isinstance(action, dict) else None
                if isinstance(target, int) and not isinstance(target, bool) and not 1 <= target <= len(panels):
                    problems.append(
                        (f"{at}.actions[{j}].panel", f"points to panel {target}; there are {len(panels)} panels")
                    )
        if panel.get("overview") is True:
            if overview:
                problems.append(
                    (f"{at}.overview", f"only one panel may set 'overview'; panel {overview[0]} already does")
                )
            elif template == "visual" and panel.get("kind") in ("flow", "timeline", "concept", "groups"):
                overview = (i + 1, _show_overview_labels(panel))
        focus = panel.get("focus")
        if focus is not None:
            wanted = [focus] if isinstance(focus, str) else focus if isinstance(focus, list) else []
            if overview is None:
                problems.append((f"{at}.focus", 'needs an earlier panel with "overview": true'))
            else:
                for label in wanted:
                    if label not in overview[1]:
                        shown = ", ".join(map(str, overview[1]))
                        problems.append(
                            (
                                f"{at}.focus",
                                f"{_show(label)} is not a label in the overview (panel {overview[0]}): {shown}",
                            )
                        )
    return problems


# ---------------------------------------------------------------- checking files


def _audit_extensions(node: dict, where: str) -> None:
    """Refuse an extension that lacks what it needs, so a mistake in a schema is an error where it is written."""
    if "x-points-to" in node:
        rule = node["x-points-to"]
        wanted = rule.get("type") if isinstance(rule, dict) else None
        types_ok = isinstance(wanted, str) or (
            isinstance(wanted, list) and bool(wanted) and all(isinstance(t, str) for t in wanted)
        )
        file_ok = isinstance(rule, dict) and isinstance(rule.get("file"), (str, dict)) and bool(rule.get("file"))
        if not (file_ok and types_ok):
            raise SchemaError(f'{where}: x-points-to needs a "file" and a "type" (a name or a list of names)')
    if "x-mode-sets" in node:
        rule = node["x-mode-sets"]
        if not (isinstance(rule, dict) and isinstance(rule.get("file"), str) and isinstance(rule.get("field"), str)):
            raise SchemaError(f'{where}: x-mode-sets needs a "file" and a "field"')
    if "x-check" in node and (not isinstance(node["x-check"], str) or node["x-check"] not in HOOKS):
        raise SchemaError(f"{where}: x-check {_show(node['x-check'])}: schema.py has no hook of that name")


def _audit(node: Any, where: str, boolean_ok: bool = False) -> None:
    """Refuse an unsupported keyword or a bad `type` anywhere in a schema, whether or not a record reaches it."""
    if boolean_ok and isinstance(node, bool):
        return
    if not isinstance(node, dict):
        raise SchemaError(f"{where}: a schema must be an object, got {_show(node)}")
    for keyword in node:
        if keyword not in KEYWORDS | ANNOTATIONS | EXTENSIONS:
            raise SchemaError(f"{where}: unsupported keyword {keyword!r}")
    if "type" in node:
        names = node["type"] if isinstance(node["type"], list) else [node["type"]]
        if not names or any(not isinstance(n, str) or n not in TYPE_NAMES for n in names):
            raise SchemaError(f"{where}: type must be one of {', '.join(sorted(TYPE_NAMES))} or a list of them")
    if "pattern" in node:
        try:
            re.compile(node["pattern"])
        except (re.error, TypeError):
            raise SchemaError(f"{where}: pattern {_show(node['pattern'])} is not a regular expression") from None
    if "required" in node and not (
        isinstance(node["required"], list) and all(isinstance(n, str) for n in node["required"])
    ):
        raise SchemaError(f"{where}: required must be a list of field names")
    for keyword in ("minimum", "maximum"):
        if keyword in node and (not isinstance(node[keyword], (int, float)) or isinstance(node[keyword], bool)):
            raise SchemaError(f"{where}: {keyword} must be a number")
    for keyword in ("minItems", "maxItems", "minLength"):
        if keyword in node and (
            not isinstance(node[keyword], int) or isinstance(node[keyword], bool) or node[keyword] < 0
        ):
            raise SchemaError(f"{where}: {keyword} must be a whole number, 0 or more")
    if "prefixItems" in node and not isinstance(node["prefixItems"], list):
        raise SchemaError(f"{where}: prefixItems must be a list of schemas")
    _audit_extensions(node, where)
    for keyword in ("properties", "$defs"):
        if keyword in node and not isinstance(node[keyword], dict):
            raise SchemaError(f"{where}: {keyword} must be an object")
    for keyword in ("allOf", "anyOf"):
        if keyword in node and not isinstance(node[keyword], list):
            raise SchemaError(f"{where}: {keyword} must be a list")
    for name, sub in node.get("properties", {}).items():
        _audit(sub, f"{where}/properties/{name}")
    for name, sub in node.get("$defs", {}).items():
        _audit(sub, f"{where}/$defs/{name}")
    for keyword in ("allOf", "anyOf", "prefixItems"):
        for i, sub in enumerate(node.get(keyword, [])):
            _audit(sub, f"{where}/{keyword}/{i}")
    for keyword in ("items", "not", "if", "then", "else"):
        if keyword in node:
            _audit(node[keyword], f"{where}/{keyword}")
    if "additionalProperties" in node:
        _audit(node["additionalProperties"], f"{where}/additionalProperties", boolean_ok=True)


def load_schemas(directory: Path) -> dict[str, dict]:
    if not directory.is_dir():
        raise SchemaError(f"no schemas folder at {directory}")
    docs = {}
    for path in sorted(directory.glob("*.json")):
        try:
            docs[path.name] = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as error:
            raise SchemaError(f"{path}: not valid JSON: {error}") from None
        _audit(docs[path.name], path.name)
        files = docs[path.name].get("x-files", []) if isinstance(docs[path.name], dict) else []
        if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
            raise SchemaError(f"{path.name}: x-files must be a list of file patterns")
    return docs


def _match(path: Path, docs: dict[str, dict]) -> list[tuple[str, dict]]:
    """The schemas that describe a file: those with the most specific pattern that matches it (several may tie)."""
    path = path.resolve()
    best: list[tuple[str, dict]] = []
    best_rank = (0, 0)
    for name, doc in docs.items():
        patterns = doc.get("x-files", []) if isinstance(doc, dict) else []
        for pattern in patterns:
            parts = pattern.split("/")
            if len(path.parts) >= len(parts) and all(
                fnmatch.fnmatchcase(a, b) for a, b in zip(path.parts[-len(parts) :], parts, strict=True)
            ):
                rank = (len(parts), len(pattern.replace("*", "")))
                if rank > best_rank:
                    best, best_rank = [(name, doc)], rank
                elif rank == best_rank and (name, doc) not in best:
                    best.append((name, doc))
    return best


def check_file(path: Path, docs: dict[str, dict], cache: dict[str, Any] | None = None) -> list[Error]:
    """The errors of one file, in line order. The file's schema is found from the `x-files` of the schemas."""
    found = _match(path, docs)
    where = str(path)
    if not found:
        return [Error(where, 1, "(file)", "no schema describes this file")]
    try:
        text = read_checked(path, path.suffix == ".jsonl")
    except (OSError, UnicodeDecodeError) as error:
        return [Error(where, 1, "(file)", f"cannot be read: {error}")]
    return check_text(path, text, docs, cache)


def check_text(path: Path, text: str, docs: dict[str, dict], cache: dict[str, Any] | None = None) -> list[Error]:
    """The errors of a file's text, which the caller has read once: it validates that text and shows the same lines."""
    found = _match(path, docs)
    where = str(path)
    if not found:
        return [Error(where, 1, "(file)", "no schema describes this file")]
    context = Context(path.resolve().parent, path.name, {} if cache is None else cache)
    errors: list[Error] = []
    seen: dict[str, int] = {}
    versioned = all(doc.get("x-versioned") for _, doc in found)
    lines = _lines(text) if path.suffix == ".jsonl" else [text]
    records = list(enumerate(lines, 1))
    for number, line in records:
        if path.suffix == ".jsonl" and not line.strip():
            errors.append(Error(where, number, ROOT, "empty line"))
            continue
        try:
            record = json.loads(line)
        except ValueError as error:
            errors.append(Error(where, number, ROOT, f"not valid JSON: {error}"))
            continue
        if not isinstance(record, dict):
            errors.append(Error(where, number, ROOT, f"expected object, got {_type_name(record)}"))
            continue
        for problem in validate_record(record, [schema for _, schema in found], docs, context):
            errors.append(Error(where, number, problem.field, problem.message))
        identity = record.get("id")
        if isinstance(identity, str):
            if not versioned and identity in seen:
                errors.append(Error(where, number, "id", f"duplicate of line {seen[identity]}"))
            seen.setdefault(identity, number)
            if any(doc.get("x-id-from-filename") for _, doc in found) and identity != path.name.removesuffix(".json"):
                errors.append(
                    Error(where, number, "id", f'must equal the file name "{path.name.removesuffix(".json")}"')
                )
    return errors


def strip_invalid(record: dict, errors: list[Error]) -> dict:
    """A copy of a record that failed its checks, for a page that still shows it: without each top-level field the
    errors name (`answer.event` and `requirements[0]` name `answer` and `requirements`), so what is left is well typed
    or missing. `errors` are the record's own; the copy lists them in `_errors` as `field: message`."""
    names = {re.match(r"[^.\[]*", error.field).group(0) for error in errors}
    stripped = {key: copy.deepcopy(value) for key, value in record.items() if key not in names}
    if errors:
        stripped["_errors"] = [f"{error.field}: {error.message}" for error in errors]
    return stripped


def check_record(
    record: Any, names: list[str], schemas: Path | None = None, cross: bool = False
) -> list[tuple[str, str]]:
    """The problems of one record against each named schema (file names in the schemas folder), as (field, message):
    the check a script makes before it writes a record. Pointers and other checks that need the files around the
    record are not made: `check_paths` makes them on the file. With `cross`, the hooks (`x-check`) of the schemas
    run too, for a record whose rules look only at the record itself, such as a presentation spec."""
    docs = load_schemas(schemas or Path(__file__).resolve().parent.parent / "schemas")
    problems: list[tuple[str, str]] = []
    context = Context(Path.cwd(), "record", {}) if cross else None
    for name in names:
        if name not in docs:
            raise SchemaError(f"no schema named {name!r} in the schemas folder")
        problems += [(p.field, p.message) for p in validate_instance(record, docs[name], docs, context)]
    return list(dict.fromkeys(problems))


def check_paths(paths: list[Path], schemas: Path | None = None) -> list[Error]:
    """The errors of each file, and of each file in each folder that a schema describes."""
    docs = load_schemas(schemas or Path(__file__).resolve().parent.parent / "schemas")
    cache: dict[str, Any] = {}
    errors: list[Error] = []
    for path in paths:
        if path.is_dir():
            matched = False
            for folder, names, files in os.walk(path):
                names[:] = sorted(n for n in names if n not in SKIPPED_FOLDERS and not n.startswith("."))
                for name in sorted(files):
                    file = Path(folder) / name
                    if _match(file, docs):
                        matched = True
                        errors += check_file(file, docs, cache)
            if not matched:
                errors.append(Error(str(path), 1, "(folder)", "no file here has a schema"))
        elif path.exists():
            errors += check_file(path, docs, cache)
        else:
            errors.append(Error(str(path), 1, "(file)", "does not exist"))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check agent files against their JSON Schemas.")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="print one line per error and exit 1 if there is any")
    check.add_argument("paths", nargs="+", type=Path, help="files, or folders whose files are all checked")
    check.add_argument("--schemas", type=Path, help="the schemas folder (default: schemas/ next to scripts/)")
    args = parser.parse_args(argv)
    try:
        errors = check_paths(args.paths, args.schemas)
    except SchemaError as error:
        print(f"schema.py: {error}", file=sys.stderr)
        return 1
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
