"""Tests for schema.py, the one validator every skill's agent files go through.

The schemas here are small ones shaped like the spec page's (a tasks-like file with a status, a pointer between two
files, a status against the change's mode, a log against its card, a claim), not the skills' own: the skills' schemas
come in later tasks and have their own tests.
"""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("architect-better", "code-better", "research-better", "design-better", "show-better")
SCRIPT = ROOT / "skills" / "architect-better" / "scripts" / "schema.py"
BASE = ROOT / "skills" / "architect-better" / "schemas" / "base.schema.json"

SPEC = importlib.util.spec_from_file_location("schema", SCRIPT)
schema = importlib.util.module_from_spec(SPEC)
sys.modules["schema"] = schema
SPEC.loader.exec_module(schema)

AT = "2026-11-21T10:00:00Z"
COORDINATE = ["todo", "building", "built", "verifying", "changes needed", "verified", "merged", "blocked"]
OTHER = ["todo", "done", "blocked"]


def base_ref(name):
    return {"$ref": f"base.schema.json#/$defs/{name}"}


TASKS = {
    "$id": "tasks.schema.json",
    "x-files": ["tasks.jsonl"],
    "type": "object",
    "additionalProperties": False,
    "required": ["type", "at", "by", "id", "task", "requirements", "status"],
    "properties": {
        "type": {"const": "task"},
        "at": base_ref("at"),
        "by": base_ref("by"),
        "id": {"type": "string", "pattern": r"^T\d+$"},
        "task": {"type": "string", "minLength": 1},
        "requirements": {
            "type": "array",
            "items": {"type": "string", "pattern": r"^S\d+$", "x-points-to": {"file": "spec.jsonl", "type": "spec"}},
        },
        "status": {
            "enum": [
                "todo",
                "building",
                "built",
                "verifying",
                "changes needed",
                "verified",
                "merged",
                "done",
                "blocked",
            ],
            "x-mode-sets": {"file": "code.json", "field": "mode", "coordinate": COORDINATE, "other": OTHER},
        },
        "reason": {"enum": ["task", "user", "repair limit"]},
        "waits_on": {
            "type": "string",
            "pattern": r"^T\d+$",
            "x-points-to": {"file": "tasks.jsonl", "type": "task"},
        },
    },
    "allOf": [
        {
            "if": {"properties": {"status": {"const": "blocked"}}},
            "then": {"required": ["reason"]},
            "else": {"not": {"anyOf": [{"required": ["reason"]}, {"required": ["waits_on"]}]}},
        },
        {
            "if": {"properties": {"reason": {"const": "task"}}, "required": ["reason"]},
            "then": {"required": ["waits_on"]},
            "else": {"not": {"required": ["waits_on"]}},
        },
        {
            "if": {"properties": {"status": {"const": "verified"}}},
            "then": {"x-check": "verified-needs-passing-verifier"},
        },
    ],
}

SPECS = {
    "$id": "spec.schema.json",
    "x-files": ["spec.jsonl"],
    "type": "object",
    "additionalProperties": False,
    "required": ["type", "at", "by", "id", "statement"],
    "properties": {
        "type": {"const": "spec"},
        "at": base_ref("at"),
        "by": base_ref("by"),
        "id": {"type": "string", "pattern": r"^S\d+$"},
        "statement": {"type": "string", "minLength": 1},
    },
}

CODE = {
    "$id": "code.schema.json",
    "x-files": ["code.json"],
    "type": "object",
    "additionalProperties": False,
    "required": ["type", "at", "by", "goal", "mode"],
    "properties": {
        "type": {"const": "code"},
        "at": base_ref("at"),
        "by": base_ref("by"),
        "goal": {"type": "string", "minLength": 1},
        "mode": {"enum": ["feature", "bug fix", "refactor", "tests", "coordinate"]},
    },
}

CARD = {
    "$id": "card.schema.json",
    "x-files": ["logs/*.card.json"],
    "type": "object",
    "additionalProperties": False,
    "required": ["type", "at", "by", "role", "task"],
    "properties": {
        "type": {"const": "card"},
        "at": base_ref("at"),
        "by": base_ref("by"),
        "role": {"enum": ["builder", "verifier"]},
        "task": {"type": "string", "pattern": r"^T\d+$"},
    },
}

LOG = {
    "$id": "log.schema.json",
    "x-files": ["logs/*.jsonl"],
    "type": "object",
    "additionalProperties": False,
    "required": ["type", "at", "by", "text"],
    "properties": {
        "type": {"enum": ["start", "step", "handed_back"]},
        "at": base_ref("at"),
        "by": base_ref("by"),
        "text": {"type": "string", "minLength": 1},
        "result": {
            "enum": ["done", "partly done", "blocked", "passes", "fails"],
            "x-mode-sets": {
                "file": "{stem}.card.json",
                "field": "role",
                "builder": ["done", "partly done", "blocked"],
                "verifier": ["passes", "fails"],
            },
        },
    },
    "allOf": [
        {
            "if": {"properties": {"type": {"const": "handed_back"}}},
            "then": {"required": ["result"]},
            "else": {"not": {"required": ["result"]}},
        }
    ],
}

QUESTIONS = {
    "$id": "question.schema.json",
    "x-files": ["questions/*.json"],
    "x-id-from-filename": True,
    "type": "object",
    "additionalProperties": False,
    "required": ["type", "at", "by", "id", "question"],
    "properties": {
        "type": {"const": "question"},
        "at": base_ref("at"),
        "by": base_ref("by"),
        "id": {"type": "string", "pattern": r"^Q-"},
        "question": {"type": "string", "minLength": 1},
    },
}

CLAIMS = {
    "$id": "claim.schema.json",
    "x-files": ["claims/*.json"],
    "x-id-from-filename": True,
    "type": "object",
    "additionalProperties": False,
    "required": ["type", "at", "by", "id", "question", "status"],
    "properties": {
        "type": {"const": "claim"},
        "at": base_ref("at"),
        "by": base_ref("by"),
        "id": {"type": "string", "pattern": r"^C-"},
        "question": {"type": "string", "x-points-to": {"file": "../questions/", "type": "question"}},
        "status": {"enum": ["unchecked", "checking"]},
        "checker": {"type": "string", "x-differs-from": "by"},
    },
}

EVENTS = {
    "$id": "events.schema.json",
    "x-files": ["events.jsonl"],
    "x-versioned": True,
    "type": "object",
    "required": ["type", "at", "by", "id"],
    "properties": {"type": {"const": "comment"}, "at": base_ref("at"), "by": base_ref("by"), "id": {"type": "string"}},
    "additionalProperties": False,
}

ALL = [TASKS, SPECS, CODE, CARD, LOG, QUESTIONS, CLAIMS, EVENTS]


def spec_line(n=1, **extra):
    return {"type": "spec", "at": AT, "by": "coordinator", "id": f"S{n}", "statement": "s", **extra}


def task(n=1, **extra):
    record = {
        "type": "task",
        "at": AT,
        "by": "coordinator",
        "id": f"T{n}",
        "task": "do it",
        "requirements": ["S1"],
        "status": "todo",
    }
    record.update(extra)
    return {k: v for k, v in record.items() if v is not None}


def jsonl(*records):
    return "".join(json.dumps(r) + "\n" for r in records)


class Case(unittest.TestCase):
    """A scratch change folder with the small schemas next to it."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.schemas = self.root / "schemas"
        self.schemas.mkdir()
        (self.schemas / "base.schema.json").write_text(BASE.read_text(encoding="utf-8"), encoding="utf-8")
        for item in ALL:
            self.put_schema(item)
        self.change = self.root / "change"
        self.change.mkdir()
        self.write("spec.jsonl", jsonl(spec_line(1), spec_line(2)))
        self.write(
            "code.json", json.dumps({"type": "code", "at": AT, "by": "coordinator", "goal": "g", "mode": "coordinate"})
        )

    def put_schema(self, item):
        (self.schemas / item["$id"]).write_text(json.dumps(item), encoding="utf-8")

    def write(self, name, text):
        path = self.change / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def check(self, name):
        return schema.check_paths([self.change / name], self.schemas)

    def messages(self, name):
        return [f"{e.line}: {e.field}: {e.message}" for e in self.check(name)]

    def assertError(self, errors, text):
        self.assertTrue(any(text in e for e in errors), f"{text!r} not in {errors}")


class CommandLine(Case):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-I", str(SCRIPT), "check", "--schemas", str(self.schemas), *map(str, args)],
            capture_output=True,
            text=True,
        )

    def test_r2_clean_file_prints_nothing_and_exits_zero(self):
        self.write("tasks.jsonl", jsonl(task(1)))
        result = self.run_cli(self.change / "tasks.jsonl")
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_r2_one_line_per_error_in_the_stated_format_and_exit_one(self):
        path = self.write("tasks.jsonl", jsonl(task(1), task(2, status="blocked")))
        result = self.run_cli(path)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.splitlines(), [f'{path}:2: reason: required when status is "blocked"'])

    def test_r2_several_paths_and_a_folder(self):
        self.write("tasks.jsonl", jsonl(task(1, status="blocked")))
        self.write("logs/b.card.json", json.dumps({"type": "card", "at": AT, "by": "c", "role": "x", "task": "T1"}))
        result = self.run_cli(self.change)
        lines = result.stdout.splitlines()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(lines), 2, lines)
        for line in lines:
            self.assertRegex(line, r"^.+:\d+: [^:]+: .+$")

    def test_r2_a_file_no_schema_describes_is_an_error_but_a_folder_skips_it(self):
        notes = self.write("notes.md", "hello")
        self.assertEqual(self.run_cli(notes).returncode, 1)
        self.assertEqual(self.run_cli(self.change).returncode, 0)

    def test_help_runs(self):
        for args in (["--help"], ["check", "--help"]):
            result = subprocess.run([sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn("check", result.stdout)


class CopiesAndCi(unittest.TestCase):
    def test_r1_every_page_skill_carries_identical_copies_of_the_script_and_the_base_schema(self):
        for relative in ("scripts/schema.py", "schemas/base.schema.json"):
            texts = {s: (ROOT / "skills" / s / relative).read_text(encoding="utf-8") for s in SKILLS}
            self.assertEqual(len(set(texts.values())), 1, f"{relative} differs between skills")

    def test_r1_the_workflow_compares_the_copies(self):
        workflow = (ROOT / ".github" / "workflows" / "scripts.yml").read_text(encoding="utf-8")
        self.assertIn("schema.py", workflow)
        self.assertIn("base.schema.json", workflow)
        for skill in SKILLS:
            # the loop names no skill but the one it requires and compares the rest by glob
            self.assertTrue(skill in workflow or "skills/*/" in workflow)

    def test_r1_the_script_imports_only_the_standard_library(self):
        import ast

        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names.add(node.module.split(".")[0])
        self.assertLessEqual(names, set(sys.stdlib_module_names) | {"__future__"})


class Required(Case):
    def test_r3_a_missing_required_field_is_an_error(self):
        record = task(1)
        del record["task"]
        self.write("tasks.jsonl", jsonl(record))
        self.assertEqual(self.messages("tasks.jsonl"), ["1: task: required"])

    def test_r3_a_field_the_schema_does_not_list_is_an_error(self):
        self.write("tasks.jsonl", jsonl(task(1), task(2, colour="red")))
        self.assertEqual(self.messages("tasks.jsonl"), ["2: colour: not allowed (the schema does not list it)"])

    def test_r3_every_error_of_a_record_is_listed(self):
        record = task(1, colour="red")
        del record["by"]
        del record["task"]
        self.write("tasks.jsonl", jsonl(record))
        errors = self.messages("tasks.jsonl")
        self.assertEqual(len(errors), 3, errors)

    def test_r3_a_nested_extra_field_names_its_path(self):
        schema_ = copy.deepcopy(CODE)
        schema_["properties"]["design"] = {
            "type": "object",
            "required": ["type"],
            "additionalProperties": False,
            "properties": {"type": {"const": "file"}},
        }
        self.put_schema(schema_)
        self.write(
            "code.json",
            json.dumps(
                {
                    "type": "code",
                    "at": AT,
                    "by": "x",
                    "goal": "g",
                    "mode": "tests",
                    "design": {"type": "file", "path": "p"},
                }
            ),
        )
        self.assertEqual(self.messages("code.json"), ["1: design.path: not allowed (the schema does not list it)"])

    def test_a_line_that_is_not_json_is_reported_with_its_line(self):
        self.write("tasks.jsonl", jsonl(task(1)) + "{not json\n")
        errors = self.messages("tasks.jsonl")
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("2: (record): not valid JSON"), errors)

    def test_a_record_that_is_not_an_object_is_an_error(self):
        self.write("tasks.jsonl", "[1, 2]\n")
        self.assertEqual(self.messages("tasks.jsonl"), ["1: (record): expected object, got array"])

    def test_a_blank_line_is_an_error_but_the_final_newline_is_not(self):
        self.write("tasks.jsonl", jsonl(task(1)) + "\n" + jsonl(task(2)))
        self.assertEqual(self.messages("tasks.jsonl"), ["2: (record): empty line"])


class StatusRules(Case):
    """R4: the message names the rule."""

    def test_r4_blocked_requires_reason(self):
        self.write("tasks.jsonl", jsonl(task(1, status="blocked")))
        self.assertEqual(self.messages("tasks.jsonl"), ['1: reason: required when status is "blocked"'])

    def test_r4_reason_is_rejected_in_another_status(self):
        self.write("tasks.jsonl", jsonl(task(1, status="todo", reason="user")))
        self.assertEqual(self.messages("tasks.jsonl"), ['1: reason: not allowed unless status is "blocked"'])

    def test_r4_reason_task_requires_waits_on(self):
        self.write("tasks.jsonl", jsonl(task(1), task(2, status="blocked", reason="task")))
        self.assertEqual(self.messages("tasks.jsonl"), ['2: waits_on: required when reason is "task"'])

    def test_r4_waits_on_is_rejected_for_another_reason(self):
        self.write("tasks.jsonl", jsonl(task(1), task(2, status="blocked", reason="user", waits_on="T1")))
        self.assertEqual(self.messages("tasks.jsonl"), ['2: waits_on: not allowed unless reason is "task"'])

    def test_r4_a_valid_chain_passes(self):
        self.write("tasks.jsonl", jsonl(task(1), task(2, status="blocked", reason="task", waits_on="T1")))
        self.assertEqual(self.messages("tasks.jsonl"), [])

    def test_r4_a_wrong_value_names_the_allowed_ones(self):
        self.write("tasks.jsonl", jsonl(task(1, status="blocked", reason="nap")))
        errors = self.messages("tasks.jsonl")
        self.assertEqual(len(errors), 1)
        self.assertIn('reason: must be one of "task", "user", "repair limit"', errors[0])


class Keywords(unittest.TestCase):
    """R5: each keyword on its own."""

    def errors(self, instance, schema_, extra=None):
        return [
            (e.field, e.message) for e in schema.validate_instance(instance, schema_, {"base.schema.json": BASE_DOC})
        ]

    def test_type(self):
        s = {"type": "string"}
        self.assertEqual(self.errors("a", s), [])
        self.assertEqual(self.errors(1, s), [("(record)", "expected string, got integer")])
        self.assertEqual(self.errors(True, {"type": "integer"}), [("(record)", "expected integer, got boolean")])
        self.assertEqual(self.errors(1.5, {"type": "integer"}), [("(record)", "expected integer, got number")])
        self.assertEqual(self.errors(1, {"type": "number"}), [])
        self.assertEqual(self.errors(None, {"type": ["string", "null"]}), [])
        self.assertEqual(len(self.errors(3, {"type": ["string", "null"]})), 1)
        for value, name in (({}, "object"), ([], "array"), (False, "boolean"), (None, "null")):
            self.assertEqual(self.errors(value, {"type": name}), [])

    def test_const_and_enum(self):
        self.assertEqual(self.errors("a", {"const": "a"}), [])
        self.assertEqual(self.errors("b", {"const": "a"}), [("(record)", 'must be "a"')])
        self.assertEqual(self.errors("b", {"enum": ["a", "b"]}), [])
        self.assertEqual(self.errors("c", {"enum": ["a", "b"]}), [("(record)", 'must be one of "a", "b"')])

    def test_pattern_and_min_length(self):
        self.assertEqual(self.errors("T1", {"pattern": r"^T\d+$"}), [])
        self.assertEqual(self.errors("x", {"pattern": r"^T\d+$"}), [("(record)", r"must match ^T\d+$")])
        self.assertEqual(self.errors("", {"minLength": 1}), [("(record)", "must have at least 1 character")])
        self.assertEqual(self.errors("a", {"minLength": 1}), [])
        self.assertEqual(self.errors(5, {"pattern": "x", "minLength": 3}), [])  # they apply to strings only

    def test_min_items_and_items(self):
        s = {"type": "array", "minItems": 1, "items": {"type": "string"}}
        self.assertEqual(self.errors(["a"], s), [])
        self.assertEqual(self.errors([], s), [("(record)", "must have at least 1 item")])
        self.assertEqual(self.errors(["a", 2], s), [("[1]", "expected string, got integer")])

    def test_properties_required_and_additional_properties(self):
        s = {
            "type": "object",
            "required": ["a"],
            "properties": {"a": {"type": "string"}},
            "additionalProperties": False,
        }
        self.assertEqual(self.errors({"a": "x"}, s), [])
        self.assertEqual(self.errors({}, s), [("a", "required")])
        self.assertEqual(self.errors({"a": 1}, s), [("a", "expected string, got integer")])
        self.assertEqual(self.errors({"a": "x", "b": 1}, s), [("b", "not allowed (the schema does not list it)")])

    def test_additional_properties_as_a_schema(self):
        s = {"type": "object", "properties": {"a": {}}, "additionalProperties": {"type": "integer"}}
        self.assertEqual(self.errors({"a": "x", "b": 1}, s), [])
        self.assertEqual(self.errors({"b": "no"}, s), [("b", "expected integer, got string")])

    def test_all_of_any_of_not(self):
        self.assertEqual(self.errors(1, {"allOf": [{"type": "integer"}, {"enum": [1, 2]}]}), [])
        self.assertEqual(len(self.errors(3, {"allOf": [{"type": "integer"}, {"enum": [1, 2]}]})), 1)
        any_of = {"anyOf": [{"type": "string"}, {"type": "null"}]}
        self.assertEqual(self.errors(None, any_of), [])
        errors = self.errors(1, any_of)
        self.assertEqual(len(errors), 1)
        self.assertIn("matches none of the allowed shapes", errors[0][1])
        self.assertEqual(self.errors("a", {"not": {"type": "integer"}}), [])
        self.assertEqual(
            self.errors(1, {"not": {"type": "integer"}}), [("(record)", "must not match the excluded shape")]
        )

    def test_a_rejection_in_then_names_the_rule(self):
        s = {"if": {"properties": {"status": {"const": "done"}}}, "then": {"not": {"required": ["reason"]}}}
        self.assertEqual(
            self.errors({"status": "done", "reason": "x"}, s), [("reason", 'not allowed when status is "done"')]
        )

    def test_a_nested_rule_keeps_its_own_name(self):
        inner = {
            "if": {"properties": {"reason": {"const": "task"}}, "required": ["reason"]},
            "then": {"required": ["waits_on"]},
        }
        s = {
            "if": {"properties": {"status": {"const": "blocked"}}},
            "then": {"required": ["reason"], "allOf": [inner]},
        }
        self.assertEqual(
            self.errors({"status": "blocked", "reason": "task"}, s), [("waits_on", 'required when reason is "task"')]
        )

    def test_not_with_a_non_object_schema_is_a_schema_error_not_a_traceback(self):
        with self.assertRaises(schema.SchemaError):
            self.errors({"a": 1}, {"not": True})

    def test_if_then_else(self):
        s = {
            "if": {"properties": {"k": {"const": 1}}, "required": ["k"]},
            "then": {"required": ["a"]},
            "else": {"required": ["b"]},
        }
        self.assertEqual(self.errors({"k": 1, "a": 0}, s), [])
        self.assertEqual(self.errors({"k": 2, "b": 0}, s), [])
        self.assertEqual(self.errors({"k": 1}, s), [("a", "required when k is 1")])
        self.assertEqual(self.errors({"k": 2}, s), [("b", "required unless k is 1")])

    def test_ref_local_and_to_the_base_schema(self):
        s = {
            "$defs": {"n": {"type": "integer"}},
            "type": "object",
            "properties": {"a": {"$ref": "#/$defs/n"}, "at": {"$ref": "base.schema.json#/$defs/at"}},
        }
        self.assertEqual(self.errors({"a": 1, "at": AT}, s), [])
        self.assertEqual(self.errors({"a": "x"}, s), [("a", "expected integer, got string")])
        self.assertEqual(len(self.errors({"at": "2026-11-21 10:00"}, s)), 1)

    def test_an_unsupported_keyword_is_refused_instead_of_ignored(self):
        with self.assertRaises(schema.SchemaError) as caught:
            self.errors(1, {"multipleOf": 2})
        self.assertIn("multipleOf", str(caught.exception))

    def test_an_unknown_ref_is_refused(self):
        with self.assertRaises(schema.SchemaError):
            self.errors(1, {"$ref": "nope.schema.json#/x"})


BASE_DOC = json.loads(BASE.read_text(encoding="utf-8"))


class Base(unittest.TestCase):
    """R8: the shared definitions the per-kind schemas build on."""

    def valid(self, name, value):
        return (
            schema.validate_instance(value, {"$ref": f"base.schema.json#/$defs/{name}"}, {"base.schema.json": BASE_DOC})
            == []
        )

    def test_at_is_iso_8601_utc_with_z(self):
        for good in ("2026-11-21T10:40:00Z", "2026-12-31T23:59:59Z"):
            self.assertTrue(self.valid("at", good), good)
        for bad in (
            "2026-11-21T10:40:00",
            "2026-11-21T10:40:00+01:00",
            "2026-11-21 10:40:00Z",
            "2026-13-01T00:00:00Z",
            "21/11/2026",
            5,
            None,
        ):
            self.assertFalse(self.valid("at", bad), bad)

    def test_by_is_a_non_empty_string(self):
        self.assertTrue(self.valid("by", "builder-t3"))
        self.assertTrue(self.valid("by", "user"))
        self.assertFalse(self.valid("by", ""))
        self.assertFalse(self.valid("by", None))


class BaseFields(Case):
    def test_r8_each_base_field_is_required(self):
        for field in ("type", "at", "by", "id"):
            record = spec_line(1)
            del record[field]
            self.write("spec.jsonl", jsonl(record))
            self.assertEqual(self.messages("spec.jsonl"), [f"1: {field}: required"], field)

    def test_r8_at_must_be_utc_with_z(self):
        self.write("spec.jsonl", jsonl(spec_line(1, at="2026-11-21T10:00:00+01:00")))
        self.assertEqual(len(self.check("spec.jsonl")), 1)

    def test_r8_id_is_forbidden_on_a_kind_the_schema_marks_without_one(self):
        self.write(
            "logs/b.card.json", json.dumps({"type": "card", "at": AT, "by": "c", "role": "builder", "task": "T1"})
        )
        self.write("logs/b.jsonl", jsonl({"type": "start", "at": AT, "by": "b", "text": "x", "id": "L1"}))
        self.assertEqual(self.messages("logs/b.jsonl"), ["1: id: not allowed (the schema does not list it)"])


class Pointers(Case):
    """R6."""

    def test_r6_a_pointer_to_a_record_of_the_named_type_resolves(self):
        self.write("tasks.jsonl", jsonl(task(1, requirements=["S1", "S2"])))
        self.assertEqual(self.messages("tasks.jsonl"), [])

    def test_r6_a_pointer_to_no_record_is_dangling_and_names_where_it_looked(self):
        self.write("tasks.jsonl", jsonl(task(1, requirements=["S1", "S9"])))
        self.assertEqual(
            self.messages("tasks.jsonl"), ['1: requirements[1]: dangling: "S9" is not a spec record in spec.jsonl']
        )

    def test_r6_a_record_of_another_type_does_not_count(self):
        self.write(
            "spec.jsonl", jsonl(spec_line(1), {"type": "gap", "at": AT, "by": "x", "id": "S2", "statement": "s"})
        )
        self.write("tasks.jsonl", jsonl(task(1, requirements=["S2"])))
        errors = self.messages("tasks.jsonl")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("dangling", errors[0])

    def test_r6_a_pointer_into_the_same_file(self):
        self.write("tasks.jsonl", jsonl(task(1), task(2, status="blocked", reason="task", waits_on="T7")))
        self.assertEqual(
            self.messages("tasks.jsonl"), ['2: waits_on: dangling: "T7" is not a task record in tasks.jsonl']
        )

    def test_r6_a_missing_target_file_is_dangling_too(self):
        (self.change / "spec.jsonl").unlink()
        self.write("tasks.jsonl", jsonl(task(1)))
        errors = self.messages("tasks.jsonl")
        self.assertEqual(len(errors), 1)
        self.assertIn("spec.jsonl does not exist", errors[0])

    def test_r6_a_pointer_into_a_folder_of_id_json_files(self):
        self.write(
            "questions/Q-w1-1.json",
            json.dumps({"type": "question", "at": AT, "by": "w1", "id": "Q-w1-1", "question": "why"}),
        )
        claim = {"type": "claim", "at": AT, "by": "w1", "id": "C-w1-1", "question": "Q-w1-1", "status": "unchecked"}
        self.write("claims/C-w1-1.json", json.dumps(claim))
        self.assertEqual(self.messages("claims/C-w1-1.json"), [])
        self.write("claims/C-w1-2.json", json.dumps({**claim, "id": "C-w1-2", "question": "Q-w1-9"}))
        errors = self.messages("claims/C-w1-2.json")
        self.assertEqual(len(errors), 1)
        self.assertIn('question: dangling: "Q-w1-9"', errors[0])

    def test_r6_a_pointer_does_not_hide_the_structural_errors_of_other_fields(self):
        self.write("tasks.jsonl", jsonl(task(1, requirements=["S9"], colour="red")))
        self.assertEqual(len(self.check("tasks.jsonl")), 2)

    def test_r6_a_pointer_inside_a_tagged_shape(self):
        s = {
            "$id": "gap.schema.json",
            "x-files": ["gaps.jsonl"],
            "type": "object",
            "properties": {
                "about": {
                    "anyOf": [
                        {
                            "type": "object",
                            "required": ["type", "task"],
                            "additionalProperties": False,
                            "properties": {
                                "type": {"const": "task"},
                                "task": {"type": "string", "x-points-to": {"file": "tasks.jsonl", "type": "task"}},
                            },
                        },
                        {
                            "type": "object",
                            "required": ["type"],
                            "additionalProperties": False,
                            "properties": {"type": {"const": "change"}},
                        },
                    ]
                }
            },
        }
        self.put_schema(s)
        self.write("tasks.jsonl", jsonl(task(1)))
        self.write(
            "gaps.jsonl",
            jsonl(
                {"about": {"type": "task", "task": "T1"}},
                {"about": {"type": "task", "task": "T4"}},
                {"about": {"type": "change"}},
            ),
        )
        errors = self.messages("gaps.jsonl")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn('2: about.task: dangling: "T4"', errors[0])

    def test_r6_the_type_can_be_a_list(self):
        s = copy.deepcopy(TASKS)
        s["properties"]["requirements"]["items"]["x-points-to"] = {"file": "spec.jsonl", "type": ["gap", "spec"]}
        self.put_schema(s)
        self.write("tasks.jsonl", jsonl(task(1)))
        self.assertEqual(self.messages("tasks.jsonl"), [])


class Identity(Case):
    def test_a_repeated_id_in_a_file_is_an_error(self):
        self.write("spec.jsonl", jsonl(spec_line(1), spec_line(2), spec_line(1)))
        self.assertEqual(self.messages("spec.jsonl"), ["3: id: duplicate of line 1"])

    def test_a_schema_marked_versioned_allows_a_repeated_id(self):
        event = {"type": "comment", "at": AT, "by": "user", "id": "c-1"}
        self.write("events.jsonl", jsonl(event, event))
        self.assertEqual(self.messages("events.jsonl"), [])

    def test_a_folder_entry_is_named_after_its_id(self):
        self.write(
            "questions/Q-w1-2.json",
            json.dumps({"type": "question", "at": AT, "by": "w1", "id": "Q-w1-1", "question": "x"}),
        )
        self.assertEqual(self.messages("questions/Q-w1-2.json"), ['1: id: must equal the file name "Q-w1-2"'])


class CrossRecord(Case):
    """R7."""

    def test_r7_a_status_must_be_in_the_set_for_the_change_mode(self):
        self.write("tasks.jsonl", jsonl(task(1, status="done")))
        self.assertEqual(
            self.messages("tasks.jsonl"),
            [
                '1: status: "done" is not allowed when mode is "coordinate" in code.json (allowed: todo, building, built, verifying, changes needed, verified, merged, blocked)'
            ],
        )

    def test_r7_the_other_set_applies_to_every_other_mode(self):
        for mode in ("feature", "bug fix", "refactor", "tests"):
            self.write("code.json", json.dumps({"type": "code", "at": AT, "by": "x", "goal": "g", "mode": mode}))
            self.write("tasks.jsonl", jsonl(task(1, status="done"), task(2, status="building")))
            errors = self.messages("tasks.jsonl")
            self.assertEqual(len(errors), 1, (mode, errors))
            self.assertIn(f'2: status: "building" is not allowed when mode is "{mode}"', errors[0])

    def test_r7_a_missing_code_json_is_an_error_not_a_pass(self):
        (self.change / "code.json").unlink()
        self.write("tasks.jsonl", jsonl(task(1)))
        errors = self.messages("tasks.jsonl")
        self.assertEqual(len(errors), 1)
        self.assertIn("code.json does not exist", errors[0])

    def verifier(self, name, task_id, at, last):
        self.write(
            f"logs/{name}.card.json",
            json.dumps({"type": "card", "at": at, "by": "coordinator", "role": "verifier", "task": task_id}),
        )
        lines = [{"type": "start", "at": at, "by": name, "text": "go"}]
        if last:
            lines.append({"type": "handed_back", "at": at, "by": name, "result": last, "text": "r"})
        self.write(f"logs/{name}.jsonl", jsonl(*lines))

    def test_r7_verified_needs_a_verifier_card_for_the_task(self):
        self.write("tasks.jsonl", jsonl(task(1, status="verified")))
        errors = self.messages("tasks.jsonl")
        self.assertEqual(len(errors), 1)
        self.assertIn('status: "verified" needs a verifier card for T1', errors[0])

    def test_r7_verified_needs_the_verifiers_last_line_to_be_handed_back_passes(self):
        self.write("tasks.jsonl", jsonl(task(1, status="verified")))
        self.verifier("v1", "T1", AT, None)
        self.assertIn("has not handed back", self.messages("tasks.jsonl")[0])
        self.verifier("v1", "T1", AT, "fails")
        self.assertIn('handed back "fails"', self.messages("tasks.jsonl")[0])
        self.verifier("v1", "T1", AT, "passes")
        self.assertEqual(self.messages("tasks.jsonl"), [])

    def test_r7_only_a_verifier_for_that_task_counts(self):
        self.write("tasks.jsonl", jsonl(task(1, status="verified")))
        self.verifier("v2", "T2", AT, "passes")
        self.assertEqual(len(self.check("tasks.jsonl")), 1)
        self.write(
            "logs/b1.card.json", json.dumps({"type": "card", "at": AT, "by": "c", "role": "builder", "task": "T1"})
        )
        self.write("logs/b1.jsonl", jsonl({"type": "handed_back", "at": AT, "by": "b1", "result": "done", "text": "r"}))
        self.assertEqual(len(self.check("tasks.jsonl")), 1)

    def test_r7_the_latest_verifier_of_the_task_decides(self):
        self.write("tasks.jsonl", jsonl(task(1, status="verified")))
        self.verifier("v1", "T1", "2026-11-21T10:00:00Z", "passes")
        self.verifier("v2", "T1", "2026-11-21T12:00:00Z", "fails")
        errors = self.messages("tasks.jsonl")
        self.assertEqual(len(errors), 1)
        self.assertIn("v2", errors[0])
        self.verifier("v3", "T1", "2026-11-21T13:00:00Z", "passes")
        self.assertEqual(self.messages("tasks.jsonl"), [])

    def test_r7_other_statuses_need_no_verifier(self):
        self.write("tasks.jsonl", jsonl(task(1, status="built")))
        self.assertEqual(self.messages("tasks.jsonl"), [])

    def test_r7_handed_back_result_must_be_in_the_set_for_the_cards_role(self):
        self.write(
            "logs/b.card.json", json.dumps({"type": "card", "at": AT, "by": "c", "role": "builder", "task": "T1"})
        )
        self.write("logs/b.jsonl", jsonl({"type": "handed_back", "at": AT, "by": "b", "result": "passes", "text": "r"}))
        self.assertEqual(
            self.messages("logs/b.jsonl"),
            [
                '1: result: "passes" is not allowed when role is "builder" in b.card.json (allowed: done, partly done, blocked)'
            ],
        )
        self.write(
            "logs/v.card.json", json.dumps({"type": "card", "at": AT, "by": "c", "role": "verifier", "task": "T1"})
        )
        self.write("logs/v.jsonl", jsonl({"type": "handed_back", "at": AT, "by": "v", "result": "done", "text": "r"}))
        self.assertEqual(len(self.check("logs/v.jsonl")), 1)
        self.write("logs/v.jsonl", jsonl({"type": "handed_back", "at": AT, "by": "v", "result": "fails", "text": "r"}))
        self.assertEqual(self.messages("logs/v.jsonl"), [])

    def test_r7_a_result_without_a_card_is_an_error(self):
        self.write("logs/x.jsonl", jsonl({"type": "handed_back", "at": AT, "by": "x", "result": "done", "text": "r"}))
        errors = self.messages("logs/x.jsonl")
        self.assertEqual(len(errors), 1)
        self.assertIn("x.card.json does not exist", errors[0])

    def test_r7_a_claim_checker_must_differ_from_its_author(self):
        self.write(
            "questions/Q-w1-1.json",
            json.dumps({"type": "question", "at": AT, "by": "w1", "id": "Q-w1-1", "question": "why"}),
        )
        claim = {
            "type": "claim",
            "at": AT,
            "by": "w1",
            "id": "C-w1-1",
            "question": "Q-w1-1",
            "status": "checking",
            "checker": "w1",
        }
        self.write("claims/C-w1-1.json", json.dumps(claim))
        self.assertEqual(self.messages("claims/C-w1-1.json"), ['1: checker: must differ from by ("w1")'])
        self.write("claims/C-w1-1.json", json.dumps({**claim, "checker": "v1"}))
        self.assertEqual(self.messages("claims/C-w1-1.json"), [])

    def test_a_hook_the_script_does_not_have_is_refused(self):
        s = copy.deepcopy(TASKS)
        s["allOf"].append({"x-check": "no-such-check"})
        self.put_schema(s)
        self.write("tasks.jsonl", jsonl(task(1)))
        with self.assertRaises(schema.SchemaError) as caught:
            self.check("tasks.jsonl")
        self.assertIn("no-such-check", str(caught.exception))


class Hooks(unittest.TestCase):
    def test_a_hook_is_a_function_registered_by_name(self):
        self.assertIn("verified-needs-passing-verifier", schema.HOOKS)


class Schemas(Case):
    def test_a_schema_that_cannot_be_applied_is_a_failure_with_a_message_not_a_traceback(self):
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                str(SCRIPT),
                "check",
                "--schemas",
                str(self.root / "missing"),
                str(self.change / "tasks.jsonl"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)

    def test_the_most_specific_file_pattern_wins(self):
        # logs/*.card.json must use the card schema, not the log schema (which matches logs/*.jsonl only by extension)
        self.write(
            "logs/b.card.json", json.dumps({"type": "card", "at": AT, "by": "c", "role": "builder", "task": "T1"})
        )
        self.assertEqual(self.messages("logs/b.card.json"), [])


class Paths(Case):
    def test_a_relative_path_from_inside_the_folder_finds_its_schema(self):
        self.write(
            "logs/b.card.json", json.dumps({"type": "card", "at": AT, "by": "c", "role": "builder", "task": "T1"})
        )
        self.write("logs/b.jsonl", jsonl({"type": "start", "at": AT, "by": "b", "text": "x", "id": "L1"}))
        result = subprocess.run(
            [sys.executable, "-I", str(SCRIPT), "check", "--schemas", str(self.schemas), "b.jsonl"],
            capture_output=True,
            text=True,
            cwd=self.change / "logs",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("id: not allowed", result.stdout)
        self.assertNotIn("no schema", result.stdout)

    def test_dot_checks_the_current_folder(self):
        self.write("tasks.jsonl", jsonl(task(1, status="blocked")))
        result = subprocess.run(
            [sys.executable, "-I", str(SCRIPT), "check", "--schemas", str(self.schemas), "."],
            capture_output=True,
            text=True,
            cwd=self.change,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn('reason: required when status is "blocked"', result.stdout)

    def test_a_folder_with_no_file_that_has_a_schema_is_an_error(self):
        empty = self.root / "empty"
        empty.mkdir()
        (empty / "notes.md").write_text("x", encoding="utf-8")
        errors = schema.check_paths([empty], self.schemas)
        self.assertEqual([(e.field, e.message) for e in errors], [("(folder)", "no file here has a schema")])


class Lines(Case):
    def test_a_unicode_line_separator_inside_a_string_does_not_split_a_record(self):
        for char in ("\u2028", "\u2029", "\u0085", "\x1c", "\x1d", "\x1e"):
            self.write("spec.jsonl", jsonl_raw(spec_line(1, statement=f"a{char}b"), spec_line(2)))
            self.write("tasks.jsonl", jsonl(task(1, requirements=["S1", "S2"])))
            self.assertEqual(self.messages("spec.jsonl"), [], repr(char))
            self.assertEqual(self.messages("tasks.jsonl"), [], repr(char))

    def test_crlf_line_ends_are_fine_and_a_blank_line_is_still_found(self):
        self.write("spec.jsonl", "\r\n".join(json.dumps(r) for r in (spec_line(1), spec_line(2))) + "\r\n")
        self.assertEqual(self.messages("spec.jsonl"), [])
        self.write("spec.jsonl", jsonl(spec_line(1)) + "\n" + jsonl(spec_line(2)))
        self.assertEqual(self.messages("spec.jsonl"), ["2: (record): empty line"])


def jsonl_raw(*records):
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)


class ArchitectFolder(Case):
    """Decided 21: code.json `design` can point to an architect folder that holds the spec and the decisions."""

    POINTER = {"from": "code.json", "field": "design.folder", "name": "spec.jsonl", "else": "spec.jsonl"}

    def setUp(self):
        super().setUp()
        s = copy.deepcopy(TASKS)
        s["properties"]["requirements"]["items"]["x-points-to"] = {"file": self.POINTER, "type": "spec"}
        self.put_schema(s)
        code = copy.deepcopy(CODE)
        code["properties"]["design"] = {
            "type": "object",
            "properties": {"type": {"enum": ["architect", "file"]}, "folder": {"type": "string"}},
        }
        self.put_schema(code)
        (self.root / ".git").mkdir()
        arch = self.root / "docs" / "designs" / "up"
        arch.mkdir(parents=True)
        (arch / "spec.jsonl").write_text(jsonl(spec_line(1), spec_line(7)), encoding="utf-8")

    def code_json(self, design):
        record = {"type": "code", "at": AT, "by": "x", "goal": "g", "mode": "coordinate"}
        if design is not None:
            record["design"] = design
        self.write("code.json", json.dumps(record))

    def test_requirements_resolve_in_the_architect_folder(self):
        self.code_json({"type": "architect", "folder": "docs/designs/up"})
        self.write("tasks.jsonl", jsonl(task(1, requirements=["S7"])))
        self.assertEqual(self.messages("tasks.jsonl"), [])

    def test_a_requirement_only_in_the_local_spec_is_dangling_then_and_names_the_folder_file(self):
        self.code_json({"type": "architect", "folder": "docs/designs/up"})
        self.write("tasks.jsonl", jsonl(task(1, requirements=["S2"])))
        errors = self.messages("tasks.jsonl")
        self.assertEqual(len(errors), 1)
        self.assertIn('dangling: "S2" is not a spec record in docs/designs/up/spec.jsonl', errors[0])

    def test_another_design_falls_back_to_the_local_file(self):
        for design in (None, {"type": "file", "path": "p.md"}):
            self.code_json(design)
            self.write("tasks.jsonl", jsonl(task(1, requirements=["S2"]), task(2, requirements=["S7"])))
            errors = self.messages("tasks.jsonl")
            self.assertEqual(len(errors), 1, errors)
            self.assertIn('2: requirements[0]: dangling: "S7"', errors[0])

    def test_a_missing_code_json_falls_back_to_the_local_file(self):
        (self.change / "code.json").unlink()
        self.write("tasks.jsonl", jsonl(task(1, requirements=["S2"])))
        self.assertEqual([e for e in self.messages("tasks.jsonl") if "dangling" in e], [])

    def test_a_missing_architect_folder_is_dangling(self):
        self.code_json({"type": "architect", "folder": "docs/designs/none"})
        self.write("tasks.jsonl", jsonl(task(1)))
        self.assertIn("docs/designs/none/spec.jsonl does not exist", self.messages("tasks.jsonl")[0])

    def test_no_repo_root_is_an_error_not_a_pass(self):
        (self.root / ".git").rmdir()
        self.code_json({"type": "architect", "folder": "docs/designs/up"})
        self.write("tasks.jsonl", jsonl(task(1)))
        errors = [e for e in self.messages("tasks.jsonl") if "repo root" in e]
        self.assertEqual(len(errors), 1)


class SchemaAudit(Case):
    """A schema is checked as a whole when it loads, not only where a record reaches it."""

    def refused(self, node, text):
        self.put_schema(
            {"$id": "bad.schema.json", "x-files": ["bad.jsonl"], "type": "object", "properties": {"a": node}}
        )
        self.write("bad.jsonl", "{}\n")
        with self.assertRaises(schema.SchemaError) as caught:
            self.check("bad.jsonl")
        self.assertIn(text, str(caught.exception))

    def test_an_unsupported_keyword_under_an_optional_property_is_refused_on_load(self):
        self.refused({"multipleOf": 2}, "multipleOf")

    def test_an_unsupported_keyword_in_every_place_a_schema_nests(self):
        for node in (
            {"items": {"nope": 1}},
            {"allOf": [{"nope": 1}]},
            {"anyOf": [{"nope": 1}]},
            {"not": {"nope": 1}},
            {"if": {"nope": 1}, "then": {}},
            {"if": {}, "then": {"nope": 1}},
            {"if": {}, "else": {"nope": 1}},
            {"additionalProperties": {"nope": 1}},
            {"properties": {"b": {"nope": 1}}},
            {"$defs": {"d": {"nope": 1}}},
        ):
            self.refused(node, "nope")

    def test_a_type_that_is_not_a_type_name_is_refused(self):
        self.refused({"type": True}, "type")
        self.refused({"type": "x"}, "type")
        self.refused({"type": ["string", "x"]}, "type")
        self.refused({"type": ["string", 3]}, "type")

    def test_a_pattern_that_is_not_a_regex_is_refused(self):
        self.refused({"type": "string", "pattern": "(unclosed"}, "pattern")
        self.refused({"type": "string", "pattern": 3}, "pattern")

    def test_required_must_be_a_list_of_strings(self):
        self.refused({"required": "a"}, "required")
        self.refused({"required": ["a", 3]}, "required")
        self.refused({"required": {"a": 1}}, "required")

    def test_a_pointer_without_its_file_and_type_is_refused(self):
        self.refused({"x-points-to": {"type": "spec"}}, "x-points-to")
        self.refused({"x-points-to": {"file": "spec.jsonl"}}, "x-points-to")
        self.refused({"x-points-to": "spec.jsonl"}, "x-points-to")

    def test_a_mode_set_without_its_file_and_field_is_refused(self):
        self.refused({"x-mode-sets": {"field": "mode", "other": ["a"]}}, "x-mode-sets")
        self.refused({"x-mode-sets": {"file": "code.json", "other": ["a"]}}, "x-mode-sets")
        self.refused({"x-mode-sets": ["code.json"]}, "x-mode-sets")

    def test_a_check_that_names_no_registered_hook_is_refused_on_load(self):
        self.refused({"x-check": "no-such-hook"}, "no-such-hook")

    def test_a_registered_hook_loads(self):
        self.put_schema(
            {
                "$id": "ok.schema.json",
                "x-files": ["ok.jsonl"],
                "type": "object",
                "properties": {"a": {"x-check": "verified-needs-passing-verifier"}},
            }
        )
        self.write("ok.jsonl", "{}\n")
        self.assertEqual(self.messages("ok.jsonl"), [])

    def test_x_files_must_be_a_list_of_strings(self):
        for files in ("a.jsonl", {"a": 1}, ["a.jsonl", 3]):
            self.put_schema({"$id": "bad.schema.json", "x-files": files, "type": "object"})
            self.write("a.jsonl", "{}\n")
            with self.assertRaises(schema.SchemaError) as caught:
                self.check("a.jsonl")
            self.assertIn("x-files", str(caught.exception))

    def test_valid_types_and_boolean_additional_properties_load(self):
        self.put_schema(
            {"$id": "ok.schema.json", "x-files": ["ok.jsonl"], "type": ["object"], "additionalProperties": False}
        )
        self.write("ok.jsonl", "{}\n")
        self.assertEqual(self.messages("ok.jsonl"), [])


class Retry(Case):
    """A reader that caught a file mid-write reads it once more before it reports a parse error."""

    def reads(self, *texts):
        calls = []
        real = schema.read_text

        def fake(path):
            if path.name == "tasks.jsonl":
                calls.append(path)
                return texts[min(len(calls), len(texts)) - 1]
            return real(path)

        return fake, calls

    def test_a_second_read_that_parses_is_used(self):
        fake, calls = self.reads('{"type": "tas', jsonl(task(1)))
        self.write("tasks.jsonl", "")
        with mock.patch.object(schema, "read_text", fake), mock.patch.object(schema, "PAUSE", 0):
            self.assertEqual(self.messages("tasks.jsonl"), [])
        self.assertEqual(len(calls), 2)

    def test_a_parse_error_is_reported_only_if_the_second_read_fails_too(self):
        fake, calls = self.reads('{"type": "tas')
        self.write("tasks.jsonl", "")
        with mock.patch.object(schema, "read_text", fake), mock.patch.object(schema, "PAUSE", 0):
            errors = self.messages("tasks.jsonl")
        self.assertEqual(len(errors), 1)
        self.assertIn("not valid JSON", errors[0])
        self.assertEqual(len(calls), 2)

    def test_a_first_read_that_is_not_utf8_is_retried_like_a_parse_failure(self):
        real = schema.read_text
        calls = []

        def fake(path):
            if path.name == "tasks.jsonl":
                calls.append(path)
                if len(calls) == 1:
                    raise UnicodeDecodeError("utf-8", b"\xe2", 0, 1, "unexpected end of data")
            return real(path)

        self.write("tasks.jsonl", jsonl(task(1)))
        with mock.patch.object(schema, "read_text", fake), mock.patch.object(schema, "PAUSE", 0):
            self.assertEqual(self.messages("tasks.jsonl"), [])
        self.assertEqual(len(calls), 2)

    def test_a_file_that_is_never_utf8_is_reported_not_raised(self):
        self.write("tasks.jsonl", "")
        (self.change / "tasks.jsonl").write_bytes(b'{"task": "\xe2"}\n')
        with mock.patch.object(schema, "PAUSE", 0):
            errors = self.messages("tasks.jsonl")
        self.assertEqual(len(errors), 1)
        self.assertIn("cannot be read", errors[0])

    def test_a_clean_file_is_read_once(self):
        fake, calls = self.reads(jsonl(task(1)))
        self.write("tasks.jsonl", "")
        with mock.patch.object(schema, "read_text", fake):
            self.assertEqual(self.messages("tasks.jsonl"), [])
        self.assertEqual(len(calls), 1)

    def test_a_file_a_pointer_reads_is_retried_too(self):
        real = schema.read_text
        seen = []

        def fake(path):
            if path.name == "spec.jsonl":
                seen.append(1)
                return "{broken" if len(seen) == 1 else real(path)
            return real(path)

        self.write("tasks.jsonl", jsonl(task(1)))
        with mock.patch.object(schema, "read_text", fake), mock.patch.object(schema, "PAUSE", 0):
            self.assertEqual(self.messages("tasks.jsonl"), [])


class Records(Case):
    """One record checked against named schemas, as page.py checks an event before it writes it."""

    PAIR = [
        {
            "$id": "common.schema.json",
            "x-files": ["log.jsonl"],
            "type": "object",
            "required": ["type", "at", "by"],
            "properties": {"type": {"type": "string"}, "at": base_ref("at"), "by": base_ref("by")},
        },
        {
            "$id": "own.schema.json",
            "x-files": ["log.jsonl"],
            "type": "object",
            "properties": {"type": {"enum": ["a", "b"]}},
        },
    ]

    def setUp(self):
        super().setUp()
        for item in self.PAIR:
            self.put_schema(item)

    def record(self, **fields):
        return {"type": "a", "at": AT, "by": "user", **fields}

    def test_a_record_that_meets_every_named_schema_has_no_problems(self):
        problems = schema.check_record(self.record(), ["common.schema.json", "own.schema.json"], self.schemas)
        self.assertEqual(problems, [])

    def test_each_named_schema_is_applied(self):
        names = ["common.schema.json", "own.schema.json"]
        self.assertEqual([f for f, _ in schema.check_record(self.record(by=""), names, self.schemas)], ["by"])
        self.assertEqual([f for f, _ in schema.check_record(self.record(type="c"), names, self.schemas)], ["type"])

    def test_an_unknown_schema_name_is_a_schema_error(self):
        with self.assertRaises(schema.SchemaError):
            schema.check_record(self.record(), ["nope.schema.json"], self.schemas)

    def test_every_schema_that_names_a_file_with_the_same_pattern_applies_to_it(self):
        self.write("log.jsonl", jsonl(self.record(), self.record(type="c")))
        errors = self.messages("log.jsonl")
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("2: type: "), errors)

    def test_a_versioned_pair_may_reuse_an_id(self):
        for item in self.PAIR:
            self.put_schema({**item, "x-versioned": True})
        self.write("log.jsonl", jsonl(self.record(id="c1"), self.record(id="c1")))
        self.assertEqual(self.messages("log.jsonl"), [])


if __name__ == "__main__":
    unittest.main()
