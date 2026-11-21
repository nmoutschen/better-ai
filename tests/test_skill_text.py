"""The text of code-better names the JSON files and their fields, and its templates follow the schemas.

No instruction, template or doc names a file the skill no longer writes. Every step that writes a JSON file tells the
writer to run `schema.py check`. Each template holds one placeholder line for every record type and status shape of
the schemas it covers, with only fields the schema has. Every file an eval case of code-better plants or writes under
`.code/` passes `schema.py check`.
"""

import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE_BETTER = ROOT / "skills" / "code-better"
SCHEMAS = CODE_BETTER / "schemas"
CASES = ROOT / "evals" / "cases" / "code-better"


def load_schema_module():
    spec = importlib.util.spec_from_file_location("code_better_schema", CODE_BETTER / "scripts" / "schema.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("code_better_schema", module)
    spec.loader.exec_module(module)
    return module


schema = load_schema_module()

TEXT_FILES = sorted(
    [CODE_BETTER / "SKILL.md"]
    + list((CODE_BETTER / "modes").glob("*.md"))
    + list((CODE_BETTER / "agents").glob("*.md"))
    + list((CODE_BETTER / "templates").glob("*.md"))
    + [ROOT / "docs" / "code-better.md"]
)

# The files the skill no longer writes. A template may still be called tasks.md or next-steps.md.
OLD_FILES = re.compile(
    r"\b(?:specs|notes)\.md\b|(?<!templates/)\b(?:tasks|next-steps)\.md\b|\bdecisions/|\blogs/[\w<>. *-]*\.md\b"
    r"|\blogs/<[^>]*>\.json\b|\baudit/[^\s`]*\.md\b|\b(?:findings|evidence)\.md\b|\bblocked_by\b|\bBlocked by\b"
)

# Which schemas each template covers.
TEMPLATES = {
    "spec.md": ["code", "spec"],
    "tasks.md": ["tasks", "progress"],
    "decision.md": ["decisions"],
    "next-steps.md": ["next-steps"],
    "instructions.md": ["instructions"],
    "log.md": ["card", "log"],
    "audit.md": ["audit", "evidence", "findings"],
}

# A shape a schema does not name with an if/then, but that a template must still show.
EXTRA_SHAPES = {"tasks": [("reason", {"user"}), ("reason", {"repair limit"})]}


def read_schema(name: str) -> dict:
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text())


def walk(node):
    """Every dict inside a JSON value, the value itself first."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def values_of(condition: dict) -> set:
    if "const" in condition:
        return {condition["const"]}
    return set(condition.get("enum", []))


def shapes(doc: dict) -> list[tuple[str, set]]:
    """The (field, values) a record's shape depends on: a field an if/then in the schema tests, whose then adds or
    forbids fields, with the values that give the same shape together; and each value of the top-level type."""
    found: list[tuple[str, set]] = []
    for node in walk(doc):
        for item in node.get("allOf", []) if isinstance(node.get("allOf"), list) else []:
            then = item.get("then")
            if not isinstance(item, dict) or "if" not in item or not isinstance(then, dict):
                continue
            if set(then) <= {"x-check"}:
                continue
            for field, condition in item["if"].get("properties", {}).items():
                if values_of(condition):
                    found.append((field, values_of(condition)))
    kind = doc.get("properties", {}).get("type", {})
    for value in sorted(values_of(kind)):
        found.append(("type", {value}))
    return found


def type_values(doc: dict) -> set:
    return values_of(doc.get("properties", {}).get("type", {}))


def names_in(doc: dict) -> set[str]:
    """Every field name the schema declares at any depth, and the base fields."""
    names = {"type", "at", "by", "id"}
    for node in walk(doc):
        if isinstance(node.get("properties"), dict):
            names |= set(node["properties"])
    return names


def holds(line, field: str, wanted: set) -> bool:
    return any(isinstance(node.get(field), str) and node[field] in wanted for node in walk(line))


def placeholder_lines(template: str) -> list[dict]:
    lines = []
    for number, text in enumerate((CODE_BETTER / "templates" / template).read_text().splitlines(), 1):
        if text.startswith("{"):
            try:
                lines.append(json.loads(text))
            except ValueError as error:
                raise AssertionError(f"templates/{template}:{number} is not JSON: {error}") from error
    return lines


class CodeBetterTextTest(unittest.TestCase):
    def test_code_better_text_names_no_old_file_or_field(self):
        """No instruction, template or doc names a Markdown file the skill replaced, or a field a schema dropped."""
        found = [
            f"{path.relative_to(ROOT)}:{number}: {match.group(0)}"
            for path in TEXT_FILES
            for number, line in enumerate(path.read_text().splitlines(), 1)
            for match in OLD_FILES.finditer(line)
        ]
        self.assertEqual(found, [])

    def test_code_better_every_entry_point_runs_schema_check_after_a_write(self):
        """SKILL.md, each mode, the builder and the verifier say once to check every file written in `.code/`."""
        sentence = (
            "after every write to a file in `.code/`, run `python3 <skill dir>/scripts/schema.py check <file>` "
            "and fix every error before your next step."
        )
        entry_points = [CODE_BETTER / "SKILL.md", *sorted((CODE_BETTER / "modes").glob("*.md"))]
        entry_points += sorted((CODE_BETTER / "agents").glob("*.md"))
        missing = [str(p.relative_to(ROOT)) for p in entry_points if sentence not in p.read_text().casefold()]
        self.assertEqual(missing, [])

    def test_code_better_every_template_is_present(self):
        names = sorted(path.name for path in (CODE_BETTER / "templates").glob("*.md"))
        self.assertEqual(names, sorted(TEMPLATES))

    def test_code_better_templates_hold_a_line_for_every_record_type_and_shape(self):
        """One placeholder line per record type and status shape of each schema, as JSON, with only schema fields."""
        problems = []
        for template, names in TEMPLATES.items():
            lines = placeholder_lines(template)
            for name in names:
                doc = read_schema(name)
                wanted = shapes(doc) + EXTRA_SHAPES.get(name, [])
                for field, values in wanted:
                    if not any(holds(line, field, values) for line in lines):
                        problems.append(f"templates/{template}: no line with {field} {sorted(values)} for {name}")
                own = [line for line in lines if line.get("type") in type_values(doc)]
                if not own:
                    problems.append(f"templates/{template}: no line of type {sorted(type_values(doc))}")
                for line in own:
                    extra = [key for node in walk(line) for key in node if key not in names_in(doc)]
                    if extra:
                        problems.append(f"templates/{template}: {line['type']} line has fields {extra} not in {name}")
                    kind = doc.get("$defs", {}).get(line["type"], doc)
                    missing = [key for key in kind.get("required", []) if key not in line]
                    if missing:
                        problems.append(f"templates/{template}: {line['type']} line lacks {missing}")
            stray = [line for line in lines if not any(line.get("type") in type_values(read_schema(n)) for n in names)]
            if stray:
                problems.append(f"templates/{template}: a line has a type no schema of it has: {stray[0].get('type')}")
        self.assertEqual(problems, [])

    def test_code_better_templates_give_the_conventions(self):
        """Each template says what an agent needs to write the file: the schema as the authority, and the check."""
        for template in TEMPLATES:
            text = (CODE_BETTER / "templates" / template).read_text()
            self.assertIn("schema.py check", text, template)
            self.assertIn("schemas/", text, template)

    def test_code_better_eval_files_under_code_pass_the_schema_check(self):
        """A file a case plants or a replay writes under `.code/` is in the new format and passes `schema.py check`."""
        files: list[tuple[str, str]] = []
        for case in sorted(CASES.iterdir()):
            if not case.is_dir():
                continue
            for planted in (case / "repo").rglob("*") if (case / "repo").is_dir() else []:
                if planted.is_file() and ".code" in planted.relative_to(case / "repo").parts:
                    files.append((f"{case.name}:{planted.relative_to(case / 'repo')}", planted.read_text()))
            for replay in sorted((case / "replays").glob("*.yaml")) if (case / "replays").is_dir() else []:
                for action in re.split(r"(?m)^- ", replay.read_text())[1:]:
                    match = re.match(r"write: (\S*\.code/\S+)\n\s+content: [|>]-?\n(.*)", action, re.S)
                    if match:
                        body = "\n".join(line[4:] for line in match.group(2).splitlines()) + "\n"
                        files.append((f"{case.name}/{replay.name}:{match.group(1)}", body))
        self.assertTrue(files, "no case plants or writes a file under .code/")
        problems = []
        for where, text in files:
            relative = where.split(":", 1)[1]
            self.assertFalse(relative.endswith(".md"), f"{where} is an old Markdown file")
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
                problems += [f"{where}: {error}" for error in schema.check_paths([path], SCHEMAS)]
        self.assertEqual(problems, [])

    def test_code_better_case_files_name_no_old_file(self):
        """The case files name the templates and files of the new format."""
        old = re.compile(r"templates/specs\.md|\.code/\S*\.md\b|\bnotes\.md\b|\bspecs\.md\b")
        found = [
            f"{path.relative_to(ROOT)}: {match.group(0)}"
            for path in sorted(CASES.rglob("*.yaml"))
            for match in old.finditer(path.read_text())
        ]
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
