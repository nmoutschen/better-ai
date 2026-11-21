#!/usr/bin/env python3
"""Checks the files a skill writes for agent bookkeeping against their JSON Schemas, in one place.

    python3 scripts/schema.py check <path>... [--schemas DIR]

A path is a file, or a folder whose files are all checked. Each error is one line, `<file>:<line>: <field>: <message>`,
and the exit code is 1 if there is any error and 0 if there is none. A JSONL file
is checked line by line, a JSON file as one record; `<line>` is 1 for a JSON file. The page's own scripts call
`check_paths` instead of keeping checks of their own; a script keeps only checks that need its own knowledge, such as
whether a slide can be drawn.

Each skill carries an identical copy of this file in `scripts/`, with `schemas/base.schema.json` next to it in
`schemas/`, as it does page.py; the Scripts workflow fails if the copies differ. Standard library only.

The schemas live in `--schemas DIR`, by default the `schemas/` folder next to `scripts/`. A schema describes one
record: one line of a JSONL file, or one JSON file. These keywords of JSON Schema are supported, and any other keyword
in a schema is an error, so a rule is never silently ignored: type, const, enum, pattern, minLength, minItems, required,
properties, additionalProperties, items, allOf, anyOf, not, if/then/else and $ref (to `#/...` in the same schema, or to
`<name>.schema.json#/...` in the schemas folder, such as the shared `base.schema.json`). `title`, `description`,
`$schema`, `$id`, `$comment`, `$defs`, `examples` and `default` are notes.

An error under if/then/else names the rule: `reason: required when status is "blocked"`.

Extensions, which other JSON Schema tools ignore:

- `x-files` (schema root): the files the schema describes, as paths from the end of the file's path, with `*` as in a
  shell: `["tasks.jsonl"]`, `["logs/*.jsonl"]`, `["questions/*.json"]`. The most specific pattern wins.
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
import fnmatch
import json
import os
import re
import sys
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
    "required",
    "properties",
    "additionalProperties",
    "items",
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
                self._cache[key] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self._cache[key] = None
        return self._cache[key]

    def read_jsonl(self, relative: str) -> list[Any] | None:
        path = self.path(relative)
        key = f"jsonl:{path}"
        if key not in self._cache:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
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
    return " and ".join(parts) or "its condition holds"


def _required_only(schema: Any) -> list[str] | None:
    if isinstance(schema, dict) and set(schema) == {"required"}:
        return list(schema["required"])
    return None


class Validator:
    def __init__(self, docs: dict[str, dict], context: Context | None = None):
        self.docs = docs
        self.context = context

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
            if "items" in schema:
                for i, item in enumerate(value):
                    problems += self.validate(item, schema["items"], _join(path, i), doc)
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
        if "x-points-to" in schema and isinstance(value, str):
            problems += self._points_to(value, schema["x-points-to"], at)
        if "x-mode-sets" in schema and isinstance(value, str):
            problems += self._mode_sets(value, schema["x-mode-sets"], at)
        if "x-differs-from" in schema and isinstance(parent, dict):
            other = schema["x-differs-from"]
            if other in parent and _equal(parent[other], value):
                problems.append(Problem(at, f"must differ from {other} ({_show(value)})", "cross"))
        if "x-check" in schema and isinstance(value, dict):
            name = schema["x-check"]
            if name not in HOOKS:
                raise SchemaError(f"x-check {name!r}: schema.py has no hook of that name")
            for field, message in HOOKS[name](value, context):
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
            return [Problem(at, f"cannot be checked: {relative} does not exist", "cross")]
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
    """The problems of one value against one schema; `docs` holds the schemas a $ref can name, by file name."""
    return Validator(docs, context).validate(value, schema, (), schema)


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


# ---------------------------------------------------------------- checking files


def load_schemas(directory: Path) -> dict[str, dict]:
    if not directory.is_dir():
        raise SchemaError(f"no schemas folder at {directory}")
    docs = {}
    for path in sorted(directory.glob("*.json")):
        try:
            docs[path.name] = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as error:
            raise SchemaError(f"{path}: not valid JSON: {error}") from None
    return docs


def _match(path: Path, docs: dict[str, dict]) -> tuple[str, dict] | None:
    path = path.resolve()
    best, best_rank = None, (0, 0)
    for name, doc in docs.items():
        patterns = doc.get("x-files", []) if isinstance(doc, dict) else []
        for pattern in patterns:
            parts = pattern.split("/")
            if len(path.parts) >= len(parts) and all(
                fnmatch.fnmatchcase(a, b) for a, b in zip(path.parts[-len(parts) :], parts, strict=True)
            ):
                rank = (len(parts), len(pattern.replace("*", "")))
                if rank > best_rank:
                    best, best_rank = (name, doc), rank
    return best


def check_file(path: Path, docs: dict[str, dict], cache: dict[str, Any] | None = None) -> list[Error]:
    """The errors of one file, in line order. The file's schema is found from the `x-files` of the schemas."""
    found = _match(path, docs)
    where = str(path)
    if found is None:
        return [Error(where, 1, "(file)", "no schema describes this file")]
    _, schema = found
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return [Error(where, 1, "(file)", f"cannot be read: {error}")]
    context = Context(path.resolve().parent, path.name, {} if cache is None else cache)
    validator = Validator(docs, context)
    errors: list[Error] = []
    seen: dict[str, int] = {}
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
        for problem in validator.validate(record, schema, (), schema):
            errors.append(Error(where, number, problem.field, problem.message))
        identity = record.get("id")
        if isinstance(identity, str):
            if not schema.get("x-versioned") and identity in seen:
                errors.append(Error(where, number, "id", f"duplicate of line {seen[identity]}"))
            seen.setdefault(identity, number)
            if schema.get("x-id-from-filename") and identity != path.name.removesuffix(".json"):
                errors.append(
                    Error(where, number, "id", f'must equal the file name "{path.name.removesuffix(".json")}"')
                )
    return errors


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
                    if _match(file, docs) is not None:
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
