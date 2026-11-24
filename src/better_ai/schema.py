"""Checks the files a skill writes for agent bookkeeping against their JSON Schemas, in one place.

This is the validator behind `better.pyz check`, `add` and `set`. What only one skill knows (a presentation's panels, a
design's boxes, a task's verifier) lives in that skill's package as a named hook. `check_paths` checks the files of a
folder, `check_record` the one record a command is about to write. Each error is one line,
`<file>:<line>: <field>: <message>`; a JSONL file is checked line by line, a JSON file as one record, and `<line>` is 1
for a JSON file. A page that still shows a record that failed its checks calls `strip_invalid`, which drops the fields
the errors name. Standard library only; Python 3.10 or later.

The schemas are loaded from one or more sources, each a folder on disk or a folder inside the zip
(`resources.schema_sources`): the shared ones, then the running skill's own. A schema of the skill replaces a shared one
of the same file name, so architect-better's decisions replace the shared `decisions.schema.json`. A schema describes one
record: one line of a JSONL file, or one JSON file. These keywords of JSON Schema are supported, and any other keyword
in a schema is an error, so a rule is never silently ignored: type, const, enum, pattern, minLength, maxLength, minItems,
maxItems, minimum, maximum, required, properties, additionalProperties, items, prefixItems, allOf, anyOf, not,
if/then/else and $ref (to `#/...` in the same schema, or to `<name>.schema.json#/...` among the loaded schemas, such as
the shared `base.schema.json`). `title`, `description`, `$schema`, `$id`, `$comment`, `$defs`, `examples` and `default`
are notes. The schemas are checked as a whole when they load: an unsupported keyword, a `type` that is not a type name,
a `pattern` that is not a regular expression, a `required` that is not a list of names, an extension without what it
needs, or an `x-check` no hook answers to is an error even where no record reaches it.
A file that does not parse is read once more before the parse error is reported, in case it was caught mid-write.

An error under if/then/else names the rule: `reason: required when status is "blocked"`.

Extensions, which other JSON Schema tools ignore:

- `x-files` (schema root): the files the schema describes, as paths from the end of the file's path, with `*` as in a
  shell: `["tasks.jsonl"]`, `["logs/*.jsonl"]`, `["questions/*.json"]`. The most specific pattern wins. When several
  schemas share the most specific pattern, a record must meet each of them: a page's `conversation.jsonl` is checked
  against the shared `conversation.schema.json` and the page's own `<page>-events.schema.json`.
- `x-required-files` (schema root): files a folder must hold when it holds a file this schema describes, as names
  in that folder: `["architect.json", "design.json"]`. `check <folder>` reports `<name>:1: (file): missing file` for
  each one that is not there, once per folder, so a folder missing a file its other files need fails the check.
- `x-versioned` (schema root): true when a line may reuse an `id`, as in a page conversation, where the latest line is
  the item's current version. Otherwise an `id` repeated in a file is an error.
- `x-id-from-filename` (schema root): true when the file is one entry of a folder, named `<id>.json`.
- `x-points-to` (a string field): `{"file": "spec.jsonl", "type": "spec"}`. The value must be the `id` of a record
  of that type in that file. `file` is relative to the folder of the file being checked and may use `..`; a name that
  ends in `/` is a folder of `<id>.json` files; `type` may be a list. Otherwise the error says it is dangling.
  `file` may also be `{"from": "code.json", "field": "design.folder", "name": "spec.jsonl", "else": "spec.jsonl"}`:
  `name` in the repo-relative folder (the repo root is the unit's, `Unit.root`) that `field`, a dotted path
  into the JSON file `from`, holds, as when `code.json` points to an architect folder; `else` when it holds none.
- `x-mode-sets` (a string field): `{"file": "code.json", "field": "mode", "coordinate": [...], "other": [...]}`. The
  value must be in the set named by the `field` of the JSON file `file`: the key that equals that value, or `other`.
  `{stem}` in `file` stands for the checked file's name without its extension: `{stem}.card.json`.
- `x-differs-from` (a field): the name of a sibling field; the two values must differ.
- `x-check` (anywhere a schema applies to a record, usually in a `then`): the name of a hook, a function registered
  with `@hook` for the rules across records that the keywords above cannot say.
- `x-id` (the `id` property of a record type): how `add` assigns the id: `{"prefix": "D"}`,
  `{"prefix_by": "<field>", "map": {...}}`, `{"prefix": "Q", "agent": true}` or `{"from": "caller"}`. The validator
  only checks its shape; `records.py` uses it.
- `x-public-url` (a string field): true when the value must be the http or https address of a public host: not
  `file:` or another scheme, not localhost, and not a loopback, private, link-local or otherwise non-public IP literal
  (`url_problem`). The check makes no network call: a name that resolves to a private address is not caught.
- `x-written-by` (schema root): `"coordinator"` when only the coordinator writes the record type. `add` and `set`
  (and `set --unset`) refuse any other `--by`, naming the coordinator: the `coordinator` field of the unit's head
  where the skill's head has one, else the literal name. The validator only checks its shape; `records.py` uses it.
- `x-old-format` (schema root): a list of schemas, the shapes a record had before this change. A record that fails the
  schema but meets one of them, and whose `at` is earlier than the cutoff the caller passes, is not an error: it is
  reported as written in the format before this change, kept as is, not converted.

To add a hook, write `def name(record, ctx) -> list[tuple[str, str]]` in a skill package's `checks.py` (or here, for a
rule every skill shares), decorate it with `@hook("name")`, and make sure the package imports it. `record` is the
record the schema applies to; `ctx.directory` is the folder of the file being checked, and `ctx.read_json(path)` and
`ctx.read_jsonl(path)` read a file relative to it (None if it does not exist). It returns `(field, message)` for each
problem, or an empty list. A schema names a hook with `x-check`, and a name no hook has is an error in the schema.
"""

from __future__ import annotations

import copy
import fnmatch
import functools
import hashlib
import ipaddress
import json
import math
import os
import re
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import unquote, urlsplit

ANNOTATIONS = {"$schema", "$id", "$comment", "$defs", "title", "description", "examples", "default"}
KEYWORDS = {
    "type",
    "const",
    "enum",
    "pattern",
    "minLength",
    "maxLength",
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
    "x-required-files",
    "x-versioned",
    "x-id-from-filename",
    "x-points-to",
    "x-mode-sets",
    "x-differs-from",
    "x-check",
    "x-id",
    "x-old-format",
    "x-public-url",
    "x-written-by",
}
TYPE_NAMES = {"string", "integer", "number", "boolean", "null", "object", "array"}
PAUSE = 0.05  # seconds before a file that failed to parse is read once more
ROOT = "(record)"
SKIPPED_FOLDERS = {"__pycache__", "node_modules"}
CLOCK_SLACK = timedelta(minutes=5)  # how far ahead of this machine's clock an `at` may be (a typed time is a guess)
TIME = "%Y-%m-%dT%H:%M:%SZ"  # the form of every `at`
OLD_FORMAT = "written in the format before this change: kept as is, not converted"


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
    except (ValueError, RecursionError):
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

    def __init__(self, directory: Path, name: str, cache: dict[str, Any], root: Path | None = None):
        self.directory = directory
        self.root = root
        self.stem = name.removesuffix(".jsonl").removesuffix(".json")
        self.cache = cache
        self.line = 0  # the line being checked, for `pointers`
        self.pointers: list[tuple[int, Path, str]] | None = (
            None  # (line, file or folder, id) of each pointer that resolved
        )

    def path(self, relative: str) -> Path:
        return Path(os.path.normpath(self.directory / relative.replace("{stem}", self.stem)))

    def repo_root(self) -> Path | None:
        """The repository root the caller gave (`Unit.root`), else what `paths.repo_root` finds from the folder."""
        from . import paths

        return self.root or paths.repo_root(self.directory)

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
        if key not in self.cache:
            try:
                self.cache[key] = json.loads(read_checked(path, False))
            except (OSError, ValueError, RecursionError):
                self.cache[key] = None
        return self.cache[key]

    def read_jsonl(self, relative: str) -> list[Any] | None:
        path = self.path(relative)
        key = f"jsonl:{path}"
        if key not in self.cache:
            try:
                text = read_checked(path, True)
            except (OSError, UnicodeDecodeError):
                self.cache[key] = None
            else:
                self.cache[key] = [_loads(line) for line in _lines(text) if line.strip()]
        return self.cache[key]

    def ids(self, relative: str) -> dict[str, set[str]] | None:
        """The records a pointer can name, as id -> record types; None if the file or folder does not exist."""
        path = self.path(relative)
        key = f"ids:{path}"
        if key not in self.cache:
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
            self.cache[key] = found
        return self.cache[key]


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
    except (ValueError, RecursionError):
        return None


# ---------------------------------------------------------------- the validator


def _is_text(value: str) -> bool:
    """False for a string holding a lone surrogate (JSON `\\ud800`): it cannot be written as UTF-8, so no file, page
    or terminal can show it."""
    if value.isascii():
        return True
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def plain(text: str) -> str:
    """Text that can be written as UTF-8: a lone surrogate in it is shown escaped (`\\ud800`). Whatever a message or
    an error entry copies out of a file goes through this, so nothing a loader answers can fail to print or encode."""
    return text if _is_text(text) else text.encode("utf-8", "backslashreplace").decode("ascii", "backslashreplace")


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, float) and not math.isfinite(value):
        return "non-finite number"  # NaN and Infinity are not JSON numbers
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string" if _is_text(value) else "non-text string"
    if isinstance(value, list):
        return "array"
    return "object"


def _is_type(value: Any, name: str) -> bool:
    actual = _type_name(value)
    return actual == name or (name == "number" and actual == "integer")


def _equal(a: Any, b: Any) -> bool:
    """Equal as JSON values: `true` is not 1 and `[true]` is not `[1]`, at any depth of what the schema holds."""
    names = {_type_name(a), _type_name(b)}
    if names == {"integer", "number"}:  # 1 and 1.0 are the same JSON number
        return bool(a == b)
    if len(names) != 1:
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(_equal(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_equal(a[k], b[k]) for k in a)
    return a == b


def show(value: Any) -> str:
    shown = json.dumps(value, ensure_ascii=False)
    return shown if shown.isascii() or _is_text(shown) else json.dumps(value)


def _join(path: tuple, part: str | int) -> tuple:
    return (*path, part)


def _render(path: tuple) -> str:
    out = ""
    for part in path:
        if isinstance(part, str) and not _is_text(part):
            part = part.encode("utf-8", "backslashreplace").decode("ascii")  # a key that is not text, shown escaped
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
            parts.append(f"{name} is {show(sub['const'])}")
        elif isinstance(sub, dict) and "enum" in sub:
            parts.append(f"{name} is one of {', '.join(show(v) for v in sub['enum'])}")
        else:
            continue
        described.add(name)
    parts += [f"{name} is present" for name in schema.get("required", []) if name not in described]
    excluded = schema.get("not")
    if (
        isinstance(excluded, dict)
        and isinstance(excluded.get("required"), list)
        and set(excluded) <= {"required", "properties"}
    ):
        for name in excluded["required"]:
            empty = (
                isinstance(excluded.get("properties", {}).get(name), dict)
                and "minItems" in excluded["properties"][name]
            )
            parts.append(f"{name} is absent or empty" if empty else f"{name} is absent")
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
            raise SchemaError(f"a schema must be an object, got {show(schema)}")
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
            problems.append(Problem(at, f"must be {show(schema['const'])}"))
        if "enum" in schema and not any(_equal(value, v) for v in schema["enum"]):
            problems.append(Problem(at, f"must be one of {', '.join(show(v) for v in schema['enum'])}"))
        if isinstance(value, str):
            if "pattern" in schema and not _search(schema["pattern"], value):
                problems.append(Problem(at, f"must match {schema['pattern']}"))
            if schema.get("x-public-url") is True and (problem := url_problem(value)):
                problems.append(Problem(at, problem))
            if "minLength" in schema and len(value) < schema["minLength"]:
                n = schema["minLength"]
                problems.append(Problem(at, f"must have at least {n} character{'' if n == 1 else 's'}"))
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                n = schema["maxLength"]
                problems.append(Problem(at, f"must have at most {n} character{'' if n == 1 else 's'}"))
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
                problems.append(Problem(at, f"must be at least {show(schema['minimum'])}"))
            if "maximum" in schema and value > schema["maximum"]:
                problems.append(Problem(at, f"must be at most {show(schema['maximum'])}"))
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
            raise SchemaError(f"a schema must be an object, got {show(sub)}")
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
                    problems.append(Problem(at, f"must differ from {other} ({show(value)})", "cross"))
        if "x-check" in schema and isinstance(value, dict) and self.hooks != "off":
            name = schema["x-check"]
            if name not in HOOKS:
                raise SchemaError(f"x-check {name!r}: no hook of that name is registered")
            try:
                found = HOOKS[name](value, context)
            except Exception:  # a hook is code: whatever it meets, the answer is an error, not a traceback
                return [*problems, Problem(ROOT, f"check failed: {name}", "cross")]
            for field, message in found:
                problems.append(Problem(_render(_join(path, field)) if path else field, plain(message), "cross"))
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
            return [Problem(at, f"dangling: {show(value)} is not a {kinds} record in {shown}", "cross")]
        if self.context.pointers is not None:
            self.context.pointers.append((self.context.line, self.context.path(relative), value))
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
                    f"{show(value)} is not allowed when {field} is {show(mode)} in {relative} "
                    f"(allowed: {', '.join(allowed)})",
                    "cross",
                )
            ]
        return []


def validate_instance(value: Any, schema: dict, docs: dict[str, dict], context: Context | None = None) -> list[Problem]:
    """The problems of one value against one schema; `docs` holds the schemas a $ref can name, by file name. The hooks
    run only when the value has no shape error."""
    return validate_record(value, [schema], docs, context)


def _not_text(value: Any) -> list[Problem]:
    """A problem for each string and each object key, at any depth, that holds a lone surrogate. It walks the value
    without recursion, so any nesting is read."""
    found: list[Problem] = []
    pending: list[tuple[Any, Any]] = [(value, None)]  # a value, and the chain (parent chain, part) leading to it

    def where(chain: Any) -> tuple:
        parts = []
        while chain is not None:
            chain, part = chain
            parts.append(part)
        return tuple(reversed(parts))

    while pending:
        item, chain = pending.pop()
        if isinstance(item, str):
            if not _is_text(item):
                found.append(Problem(_render(where(chain)), "is not text (it holds a lone surrogate)"))
        elif isinstance(item, dict):
            for key, child in item.items():
                if not _is_text(key):
                    found.append(Problem(_render(where((chain, key))), "key is not text (it holds a lone surrogate)"))
                pending.append((child, (chain, key)))
        elif isinstance(item, list):
            pending.extend((child, (chain, i)) for i, child in enumerate(item))
    return found


def validate_record(value: Any, schemas: list[dict], docs: dict[str, dict], context: Context | None) -> list[Problem]:
    """The problems of one record against each of its schemas: first everything but the hooks, then, if the record has
    no shape error, the hooks, whose findings come last."""
    try:
        first = [p for schema in schemas for p in Validator(docs, context, "off").validate(value, schema, (), schema)]
        named = {p.field for p in first}
        first += [p for p in _not_text(value) if p.field not in named]
        if context is None or any(p.kind != "cross" for p in first):
            return first
        hooked = [p for schema in schemas for p in Validator(docs, context, "only").validate(value, schema, (), schema)]
    except SchemaError:
        raise  # the schema is wrong, which is not a problem of the record
    except RecursionError:
        return [Problem(ROOT, "is nested too deeply to check")]
    except Exception as error:  # whatever one record makes the validator raise is that record's error, not a traceback
        return [Problem(ROOT, f"could not be checked: {type(error).__name__}")]
    return first + [p for p in hooked if p.kind == "cross"]


# ---------------------------------------------------------------- hooks every skill shares


@hook("decision-answer-event")
def _decision_answer_event(record: dict, context: Context) -> list[tuple[str, str]]:
    """An answered decision whose answer is of type `page` points to an `answer` event of the user in this unit's
    conversation.jsonl whose `decision` is this decision's id. That the event exists is x-points-to's to say."""
    answer = record.get("answer")
    event = answer.get("event") if isinstance(answer, dict) and answer.get("type") == "page" else None
    if not isinstance(event, str):
        return []
    lines = context.read_jsonl("conversation.jsonl") or []
    found = [line for line in lines if isinstance(line, dict) and line.get("id") == event]
    if not found:
        return []  # dangling: reported by the pointer
    problems = []
    last = found[-1]
    if last.get("type") != "answer":
        problems.append(("answer.event", f"{event!r} is a {show(last.get('type'))} event, not an answer event"))
    else:
        if last.get("by") != "user":
            problems.append(("answer.event", f"{event!r} was not written by the user (by is {show(last.get('by'))})"))
        if last.get("decision") != record.get("id"):
            problems.append(
                ("answer.event", f"{event!r} answers {show(last.get('decision'))}, not {show(record.get('id'))}")
            )
    return problems


# ---------------------------------------------------------------- shared rules on values


def fingerprint(value: Any, drop: tuple[str, ...] = ("at", "by")) -> str:
    """The sha256 of a value's canonical JSON (keys sorted, no spaces, text as is), without the top-level fields in
    `drop` when it is an object: when and by whom a record was written does not change what it says."""
    if isinstance(value, dict):
        value = {k: v for k, v in value.items() if k not in drop}
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()


NAT64 = ipaddress.ip_network("64:ff9b::/96")
PLAIN_HOST = re.compile(r"[a-z0-9_.-]+")


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
    if ip.version == 6 and (int(ip) >> 32 == 0 or ip in NAT64):  # ::/96 and 64:ff9b::/96 hold an IPv4 address
        return ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
    return ip


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _host(host: str) -> str | None:
    """A host as a client reads it: an IP literal as it is, a name through IDNA (full-width digits and dots, other
    scripts) in lower case. None if it is not a valid host."""
    if _is_ip(host):
        return host.lower()
    try:
        return host.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return None


def url_problem(url: str) -> str | None:
    """Why an address is refused as a public page's, or None (`x-public-url`): an http or https address of a public
    host only: not localhost, and not a loopback, private, link-local or otherwise non-public IP literal. Offline: a
    name that resolves to a private address is not caught here."""
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
    host = unquote(host)  # as a client reads it: the percent-encoded bytes first
    if "%" in host:
        return "has a percent sign in its host: write the host name or address plainly"
    host = _host(host.rstrip("."))
    numeric_end = bool(host) and re.fullmatch(r"[0-9]+|0[xX][0-9a-fA-F]*", host.rsplit(".", 1)[-1])
    if numeric_end and not _is_ip(host) and _short_form(host) is None:  # a number a client would wrap or refuse
        return "is not a plain host name or address: give the page's http or https address"
    if not host or not (PLAIN_HOST.fullmatch(host) or _is_ip(host)):
        return "is not a plain host name or address: give the page's http or https address"
    if host == "localhost" or host.endswith(".localhost"):
        return "is localhost: give the address of a public page"
    ip = _literal(host)
    if ip is not None and not ip.is_global:
        return f"is {host}, a loopback, private or link-local address: use the page's public address"
    return None


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
    if "x-id" in node:
        rule = node["x-id"]
        by_field = (
            isinstance(rule, dict) and isinstance(rule.get("prefix_by"), str) and isinstance(rule.get("map"), dict)
        )
        fixed = isinstance(rule, dict) and isinstance(rule.get("prefix"), str) and bool(rule.get("prefix"))
        caller = isinstance(rule, dict) and rule.get("from") == "caller"
        if not (by_field or fixed or caller):
            raise SchemaError(f'{where}: x-id needs a "prefix", a "prefix_by" with a "map", or "from": "caller"')
    if "x-public-url" in node and node["x-public-url"] is not True:
        raise SchemaError(f"{where}: x-public-url must be true")
    if "x-written-by" in node and node["x-written-by"] != "coordinator":
        raise SchemaError(f'{where}: x-written-by must be "coordinator"')
    if "x-old-format" in node and not (
        isinstance(node["x-old-format"], list) and all(isinstance(s, dict) for s in node["x-old-format"])
    ):
        raise SchemaError(f"{where}: x-old-format must be a list of schemas")
    if "x-check" in node and (not isinstance(node["x-check"], str) or node["x-check"] not in HOOKS):
        raise SchemaError(f"{where}: x-check {show(node['x-check'])}: no hook of that name is registered")


def _audit(node: Any, where: str, boolean_ok: bool = False) -> None:
    """Refuse an unsupported keyword or a bad `type` anywhere in a schema, whether or not a record reaches it."""
    if boolean_ok and isinstance(node, bool):
        return
    if not isinstance(node, dict):
        raise SchemaError(f"{where}: a schema must be an object, got {show(node)}")
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
            raise SchemaError(f"{where}: pattern {show(node['pattern'])} is not a regular expression") from None
    if "required" in node and not (
        isinstance(node["required"], list) and all(isinstance(n, str) for n in node["required"])
    ):
        raise SchemaError(f"{where}: required must be a list of field names")
    for keyword in ("minimum", "maximum"):
        if keyword in node and (not isinstance(node[keyword], (int, float)) or isinstance(node[keyword], bool)):
            raise SchemaError(f"{where}: {keyword} must be a number")
    for keyword in ("minItems", "maxItems", "minLength", "maxLength"):
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
    for keyword in ("allOf", "anyOf", "prefixItems", "x-old-format"):
        for i, sub in enumerate(node.get(keyword, [])):
            _audit(sub, f"{where}/{keyword}/{i}")
    for keyword in ("items", "not", "if", "then", "else"):
        if keyword in node:
            _audit(node[keyword], f"{where}/{keyword}")
    if "additionalProperties" in node:
        _audit(node["additionalProperties"], f"{where}/additionalProperties", boolean_ok=True)


@functools.cache
def _strict(pattern: str) -> str:
    """The pattern with each `$` outside a character class turned into `\\Z`. In Python `$` also matches just before a
    final newline, so `^[a-z]+$` would accept "abc\\n"; JSON Schema's `$` is the end of the string."""
    out, i, inside = [], 0, False
    while i < len(pattern):
        c = pattern[i]
        if c == "\\" and i + 1 < len(pattern):
            out.append(pattern[i : i + 2])
            i += 2
            continue
        if c == "[" and not inside:
            inside = True
        elif c == "]" and inside:
            inside = False
        out.append("\\Z" if c == "$" and not inside else c)
        i += 1
    return "".join(out)


def _search(pattern: str, value: str) -> bool:
    """JSON Schema `pattern`: found anywhere in the value, with `$` meaning the very end."""
    return re.search(_strict(pattern), value) is not None


def load_schemas(*sources: Any) -> dict[str, dict]:
    """The schemas of one or more folders, by file name, each a Path or a folder inside the zip (anything with
    `iterdir`, `is_dir`, `name` and `read_text`). A later source replaces a schema of the same name from an earlier one."""
    docs: dict[str, dict] = {}
    for directory in sources:
        if not directory.is_dir():
            raise SchemaError(f"no schemas folder at {directory}")
        for path in sorted((p for p in directory.iterdir() if p.name.endswith(".json")), key=lambda p: p.name):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except ValueError as error:
                raise SchemaError(f"{path}: not valid JSON: {error}") from None
            _audit(doc, path.name)
            files = doc.get("x-files", []) if isinstance(doc, dict) else []
            if not isinstance(files, list) or not all(isinstance(f, str) for f in files):
                raise SchemaError(f"{path.name}: x-files must be a list of file patterns")
            needed = doc.get("x-required-files", []) if isinstance(doc, dict) else []
            if not isinstance(needed, list) or not all(isinstance(f, str) and f for f in needed):
                raise SchemaError(f"{path.name}: x-required-files must be a list of file names")
            docs[path.name] = doc
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


def check_file(
    path: Path,
    docs: dict[str, dict],
    cache: dict[str, Any] | None = None,
    *,
    now: datetime | None = None,
    cutoff: str | None = None,
    notices: list[Error] | None = None,
    root: Path | None = None,
) -> list[Error]:
    """The errors of one file, in line order. The file's schema is found from the `x-files` of the schemas. See
    `check_text` for `now`, `cutoff`, `notices` and `root`."""
    found = _match(path, docs)
    where = str(path)
    if not found:
        return [Error(where, 1, "(file)", "no schema describes this file")]
    try:
        text = read_checked(path, path.suffix == ".jsonl")
    except (OSError, UnicodeDecodeError) as error:
        return [Error(where, 1, "(file)", f"cannot be read: {error}")]
    return check_text(path, text, docs, cache, now=now, cutoff=cutoff, notices=notices, root=root)


def _clock_skew(record: dict, now: datetime) -> str | None:
    """The message for a record whose `at` is more than CLOCK_SLACK after `now` (UTC), else None. An `at` that is not a
    time is the schema's to report."""
    at = record.get("at")
    if not isinstance(at, str):
        return None
    try:
        written = datetime.strptime(at, TIME).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    ahead = written - now
    if ahead <= CLOCK_SLACK:
        return None
    minutes = round(ahead.total_seconds() / 60)
    return f"{minutes} min ahead of this machine's clock ({now:%H:%M}Z): clock skew or a typed time"


def _meets_old_format(record: dict, found: list[tuple[str, dict]], docs: dict, context: Context, cutoff: str) -> bool:
    """True when the record is from before the cutoff and has the shape the schemas kept as `x-old-format`: every
    schema it fails lists an old shape it meets in full."""
    at = record.get("at")
    # Times in UTC with Z sort as text. A record with no `at`, or a null one, was written before records had one.
    if at is not None and (not isinstance(at, str) or not at < cutoff):
        return False
    for _, schema in found:
        if not validate_record(record, [schema], docs, context):
            continue
        olds = schema.get("x-old-format")
        if not isinstance(olds, list):
            return False
        try:
            if not any(not Validator(docs, context, "off").validate(record, old, (), schema) for old in olds):
                return False
        except RecursionError:  # too deeply nested to meet any shape: the record's own error stands
            return False
    return True


def check_text(
    path: Path,
    text: str,
    docs: dict[str, dict],
    cache: dict[str, Any] | None = None,
    *,
    now: datetime | None = None,
    cutoff: str | None = None,
    notices: list[Error] | None = None,
    pointers: list[tuple[int, Path, str]] | None = None,
    root: Path | None = None,
) -> list[Error]:
    """The errors of a file's text, which the caller has read once: it validates that text and shows the same lines.
    With `pointers`, each pointer that resolves is added to it as (line, file or folder it names, id). `root` is the
    repository's root (`Unit.root`), which a pointer into another folder of the repository starts from.

    With `now`, a record whose `at` is more than five minutes ahead of it is an error (a typed time, or a skewed
    clock). With `cutoff` (a UTC time like the `at`s) and `notices`, a record that fails its schema but has a shape the
    schema keeps in `x-old-format` and was written before the cutoff is not an error: it is added to `notices`, one
    `(format)` entry per line, as written in the format before this change."""
    found = _match(path, docs)
    where = str(path)
    if not found:
        return [Error(where, 1, "(file)", "no schema describes this file")]
    context = Context(path.resolve().parent, path.name, {} if cache is None else cache, root)
    context.pointers = pointers
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
        except RecursionError:
            errors.append(Error(where, number, ROOT, "is nested too deeply to read"))
            continue
        if not isinstance(record, dict):
            errors.append(Error(where, number, ROOT, f"expected object, got {_type_name(record)}"))
            continue
        context.line = number
        problems = validate_record(record, [schema for _, schema in found], docs, context)
        if (
            problems
            and cutoff is not None
            and notices is not None
            and _meets_old_format(record, found, docs, context, cutoff)
        ):
            notices.append(Error(where, number, "(format)", OLD_FORMAT))
            problems = []
        for problem in problems:
            errors.append(Error(where, number, problem.field, problem.message))
        skew = _clock_skew(record, now) if now is not None else None
        if skew:
            errors.append(Error(where, number, "at", skew))
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
    try:
        stripped = {
            key: copy.deepcopy(value)
            for key, value in record.items()
            if key not in names and (not isinstance(key, str) or _is_text(key))
        }
    except RecursionError:  # too deeply nested to copy: the page shows it marked, with its errors and a plain id
        stripped = {"id": record["id"]} if isinstance(record.get("id"), str) else {}
    if errors:
        stripped["_errors"] = [f"{error.field}: {error.message}" for error in errors]
    return stripped


MAX_DEPTH = 50  # no record of a unit's files nests deeper than a design.json step


def page_value(piece: str) -> Any:
    """One JSON value as a page can show it: no NaN or Infinity (a browser cannot read them), and nothing nested so
    deep that Python gives up. ValueError says why not."""

    def refuse(word: str) -> Any:
        raise ValueError(f"{word} is not a JSON value")

    def finite(word: str) -> float:
        value = float(word)
        if math.isinf(value):
            raise ValueError(f"{word} is too large")
        return value

    try:
        value = json.loads(piece, parse_constant=refuse, parse_float=finite)
    except RecursionError:
        raise ValueError("nested too deeply") from None
    pending = [(value, 1)]
    while pending:  # no recursion: a line may be as deep as it likes
        item, depth = pending.pop()
        if isinstance(item, (dict, list)):
            if depth > MAX_DEPTH:
                raise ValueError(f"nested more than {MAX_DEPTH} levels deep")
            pending.extend((inner, depth + 1) for inner in (item.values() if isinstance(item, dict) else item))
    return value


class Read(NamedTuple):
    """What `read_records` found in one file."""

    records: list[dict]  # in line order; a record with errors only with keep_invalid, marked by `_errors`
    lines: list[int]  # the line of each record, in step with `records`
    errors: list[dict]  # {file, line, field, message, by}: the first error of each field of a line; `by` if readable
    old: set[int]  # the lines written in the format before this change (not errors)


def read_records(
    unit: Any, relative: str, docs: dict, cache: dict, now: datetime, cutoff: str, keep_invalid: bool = False
) -> Read:
    """The records of one file of a unit for a page, checked on the text that is shown, so a write in between is in
    neither. A file that does not exist has none. A record with errors is left out, unless `keep_invalid`: then it
    stays without the fields that failed, its messages in `_errors`, its `status` as written and an `id` of `(line n)`
    if it has none. A line that is not JSON a page can show (NaN, too deep) is an error, never a record. A file that no
    schema describes, or that cannot be read or checked, has only its error."""
    from . import paths

    def failed(message: str, line: int = 1, field: str = "(file)") -> Read:
        return Read([], [], [{"file": relative, "line": line, "field": field, "message": message}], set())

    try:
        path = unit.target(relative)
        if not path.is_file():
            return Read([], [], [], set())
        jsonl = path.suffix == ".jsonl"
        text = read_checked(path, jsonl)
    except (OSError, UnicodeDecodeError, paths.Refused) as error:
        return failed(f"cannot be read: {error}")
    notices: list[Error] = []
    try:
        found = check_text(path, text, docs, cache, now=now, cutoff=cutoff, notices=notices, root=unit.root)
    except RecursionError:
        return failed("cannot be checked: nested too deeply")
    if [(e.field, e.message) for e in found] == [("(file)", "no schema describes this file")]:
        return failed(found[0].message)
    flagged = {e.line for e in found}
    parsed: dict[int, dict | None] = {}
    errors: list[dict] = []
    for number, piece in enumerate(_lines(text) if jsonl else [text], 1):
        try:
            value = page_value(piece)
        except ValueError as error:
            if number not in flagged:  # valid for the schema, but not for a page
                errors.append({"file": relative, "line": number, "field": ROOT, "message": f"not valid JSON: {error}"})
            continue
        parsed[number] = value if isinstance(value, dict) else None
    by_line: dict[int, list[Error]] = {}
    for error in found:
        if any(e.field == error.field for e in by_line.get(error.line, [])):
            continue
        record = parsed.get(error.line)
        by = record.get("by") if record else None
        entry = {"file": relative, "line": error.line, "field": error.field, "message": error.message}
        errors.append({**entry, "by": plain(by)} if isinstance(by, str) and by else entry)
        by_line.setdefault(error.line, []).append(error)
    records: list[dict] = []
    lines: list[int] = []
    for number, record in parsed.items():
        if record is None or (number in by_line and not keep_invalid):
            continue
        if number in by_line:
            status = record.get("status")
            record = strip_invalid(record, by_line[number])
            if isinstance(status, str):
                record["status"] = plain(status)  # a page shows only text, so a status that failed shows as written
            if not isinstance(record.get("id"), str) or not record["id"]:
                record["id"] = f"(line {number})"
        records.append(record)
        lines.append(number)
    return Read(records, lines, errors, {e.line for e in notices})


def docs_for(package: str | None = None) -> dict[str, dict]:
    """The schemas of a skill package (the running skill's if none is named): the shared ones, then the package's own.
    Loaded once per package; callers do not change what it returns."""
    from . import resources

    return _loaded(package or resources.build_info().package)


@functools.cache
def _loaded(package: str) -> dict[str, dict]:
    from . import resources

    return load_schemas(*resources.schema_sources(package))


def check_record(
    record: Any, names: list[str], schemas: Path | None = None, cross: bool = False
) -> list[tuple[str, str]]:
    """The problems of one record against each named schema (file names among the loaded schemas), as (field,
    message): the check a command makes before it writes a record. Pointers and other checks that need the files
    around the record are not made: `check_paths` makes them on the file. With `cross`, the hooks (`x-check`) of the
    schemas run too, for a record whose rules look only at the record itself, such as a presentation spec. `schemas`
    is a folder; by default the shared schemas and the running skill's own."""
    docs = load_schemas(schemas) if schemas else docs_for()
    problems: list[tuple[str, str]] = []
    context = Context(Path.cwd(), "record", {}) if cross else None
    for name in names:
        if name not in docs:
            raise SchemaError(f"no schema named {name!r} among the loaded schemas")
        problems += [(p.field, p.message) for p in validate_instance(record, docs[name], docs, context)]
    return list(dict.fromkeys(problems))


def check_paths(
    paths: list[Path],
    schemas: Path | None = None,
    *,
    docs: dict[str, dict] | None = None,
    now: datetime | None = None,
    cutoff: str | None = None,
    notices: list[Error] | None = None,
    root: Path | None = None,
) -> list[Error]:
    """The errors of each file, and of each file in each folder that a schema describes. `docs` (already loaded) or
    `schemas` (a folder) say which schemas apply; by default the shared ones and the running skill's. `now`, `cutoff`,
    `notices` and `root` are as for `check_text`."""
    if docs is None:
        docs = load_schemas(schemas) if schemas else docs_for()
    cache: dict[str, Any] = {}
    errors: list[Error] = []
    for path in paths:
        if path.is_dir():
            matched = False
            for folder, names, files in os.walk(path):
                names[:] = sorted(n for n in names if n not in SKIPPED_FOLDERS and not n.startswith("."))
                needed: list[str] = []
                for name in sorted(files):
                    file = Path(folder) / name
                    if file.is_symlink():  # add, set and the pages refuse a symlink: check does not read through one
                        matched = True
                        errors.append(Error(str(file), 1, "(file)", "is a symlink: copy the file into the unit"))
                        continue
                    found = _match(file, docs)
                    if found:
                        matched = True
                        errors += check_file(file, docs, cache, now=now, cutoff=cutoff, notices=notices, root=root)
                        needed += [n for _, doc in found for n in doc.get("x-required-files", []) if n not in needed]
                errors += [
                    Error(str(Path(folder) / n), 1, "(file)", "missing file")
                    for n in needed
                    if not (Path(folder) / n).exists()
                ]
            if not matched:
                errors.append(Error(str(path), 1, "(folder)", "no file here has a schema"))
        elif path.exists():
            errors += check_file(path, docs, cache, now=now, cutoff=cutoff, notices=notices, root=root)
        else:
            errors.append(Error(str(path), 1, "(file)", "does not exist"))
    return errors
