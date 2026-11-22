"""Tests for the text of the skills that name the files an agent writes for bookkeeping.

code-better: its SKILL.md, modes, agents, templates and docs name the JSON files and their fields and none of the old
Markdown files, SKILL.md, each mode and each agent tell the writer to run `schema.py check` after every write, the
templates have a placeholder line for every record type and shape in the schemas, and every file the evals plant or
write under `.code/` passes the schema check.

research-better: its SKILL.md, worker and verifier prompts, board template and docs name the JSON board's files and
fields and none of the old Markdown board's, SKILL.md and the two agents state the record rule (`better.pyz add` and
`set`), the template has a placeholder line for every record type and status, and every board the evals plant passes
the schema check.

Both skills: no text names an old script or `schemas/`, and no template line holds `at`, `by` or `id`.
"""

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import better  # noqa: E402

from better_ai import research, resources  # noqa: E402,F401  (research registers the hooks the schemas name)
from better_ai import schema as better_schema  # noqa: E402

RESEARCH = ROOT / "skills" / "research-better"
SCHEMAS = ROOT / "src" / "better_ai" / "research" / "schemas"
SHARED_SCHEMAS = ROOT / "src" / "better_ai" / "schemas"
TEXTS = [
    RESEARCH / "SKILL.md",
    RESEARCH / "agents" / "worker.md",
    RESEARCH / "agents" / "verifier.md",
    RESEARCH / "templates" / "board.md",
    ROOT / "docs" / "research-better.md",
]
OLD_FILES = [
    r"brief\.md",
    r"questions/(<id>|\*)?\.?md",
    r"claims/(<id>|\*)?\.?md",
    r"sources/(<id>|\*)?\.?md",
    r"decisions/",
    r"logs/(<[^>]+>|\*)\.md",
    r"<YOUR NAME>\.md",
    r"`key: value`",
    r"one `key: value`",
]
OLD_FIELDS = [
    r"done-when",
    r"trust-reason",
    r"stop-at",
    r"verified:",
    r"verified line",
    r"\banswer:",
    r"\banswer line",
]
RECORD_RULE = (
    "WRITE each record of the board with `python3 <skill dir>/scripts/better.pyz add <board> <type> --by <your agent name>`, "
    "with its fields as JSON on stdin, or edit it with `set`. WRITE a line of a log with `--for <the log's agent name>` instead of `--by`. "
    "IF it refuses the record, FIX the record and RUN it again. "
    "IF it reports busy, RUN it again. DO NOT write the record by hand to get past a refusal."
)
AGENT_RECORD_RULE = (
    "WRITE each record of the board with `python3 <skill dir>/scripts/better.pyz add <BOARD> <type> --by <YOUR NAME>`, "
    "with its fields as JSON on stdin, or edit it with `set`. WRITE a line of your log with `--for <YOUR NAME>` instead of `--by`. "
    "IF it refuses the record, FIX the record and RUN it again. "
    "IF it reports busy, RUN it again. DO NOT write the record by hand to get past a refusal. "
    "IF you cannot run commands, STOP and SAY so in your hand-back."
)
# Fields the command stamps or assigns: a template line does not show them.
STAMPED = {"at", "by", "id"}
# The decision shape every skill shares: its statuses and its fields.
DECISION_STATUSES = {"waiting", "defaulted", "answered"}
DECISION_FIELDS = {
    "type",
    "raised_by",
    "about",
    "asked",
    "status",
    "default",
    "deadline",
    "answer",
    "decision",
}
RECORD_FILES = {
    "brief": "brief.schema.json",
    "question": "questions.schema.json",
    "claim": "claims.schema.json",
    "source": "sources.schema.json",
    "decision": "decisions.schema.json",
}


def template_records() -> list[dict]:
    """The JSON lines in the template's code blocks, with each `<placeholder>` left as text."""
    records = []
    for line in (RESEARCH / "templates" / "board.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("{"):
            records.append(json.loads(line))
    return records


def schema_json(name: str) -> dict:
    """A research schema, or the shared one of that name."""
    path = SCHEMAS / name if (SCHEMAS / name).exists() else SHARED_SCHEMAS / name
    return json.loads(path.read_text(encoding="utf-8"))


class ResearchBetterText(unittest.TestCase):
    def test_no_old_board_file_is_named(self) -> None:
        """The text names no brief.md, questions/*.md, claims/*.md, sources/*.md, decisions/, logs/*.md or key: value."""
        for path in TEXTS:
            text = path.read_text(encoding="utf-8")
            for pattern in OLD_FILES:
                with self.subTest(file=path.name, pattern=pattern):
                    self.assertIsNone(re.search(pattern, text), f"{path.name} still names {pattern}")

    def test_no_old_field_is_named(self) -> None:
        """The text names no done-when, trust-reason, stop-at, `verified:` claim state or `answer:` on a question."""
        for path in TEXTS:
            text = path.read_text(encoding="utf-8")
            for pattern in OLD_FIELDS:
                with self.subTest(file=path.name, pattern=pattern):
                    self.assertIsNone(re.search(pattern, text), f"{path.name} still names {pattern}")

    def test_the_json_files_and_fields_are_named(self) -> None:
        """The skill text names the JSON board's files and the fields that replaced the old ones."""
        text = "\n".join(p.read_text(encoding="utf-8") for p in TEXTS[:4])
        for name in (
            "brief.json",
            "decisions.jsonl",
            "questions/<id>.json",
            "claims/<id>.json",
            "sources/<id>.json",
            "logs/<agent>.jsonl",
            "done_when",
            "trust_reason",
            "stop_at",
            "raised_in",
            "withdrawn",
            "duplicate",
            "merged_into",
            "empty_lenses",
        ):
            with self.subTest(name=name):
                self.assertIn(name, text)

    def test_each_loop_starts_with_the_record_rule(self) -> None:
        """SKILL.md states the record rule once in its general rules, and the worker's and verifier's loops restate it."""
        skill = (RESEARCH / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(skill.count(RECORD_RULE), 1)
        general = skill[skill.index("## General rules") :]
        self.assertIn(RECORD_RULE, general)
        self.assertIn("IF you cannot run commands, MARK the research **not finished**", general)
        for name in ("worker.md", "verifier.md"):
            text = (RESEARCH / "agents" / name).read_text(encoding="utf-8")
            loop = text[text.index("## Loop") :]
            with self.subTest(file=name):
                self.assertTrue(
                    loop[len("## Loop") :].lstrip().startswith(AGENT_RECORD_RULE), "not at the head of the loop"
                )
                self.assertIn("run commands", text.split("---")[1])

    def test_the_board_template_holds_no_record_rule_and_no_check_line(self) -> None:
        """The board template states neither the record rule nor a check after every write."""
        text = (RESEARCH / "templates" / "board.md").read_text(encoding="utf-8")
        self.assertNotIn("better.pyz", text)
        self.assertNotIn("RUN `", text)
        self.assertNotIn("counter", text)

    def test_text_fixes_from_the_verifier(self) -> None:
        """A verifier's flag goes in reason or differs, a question's owner may edit its note, the verifier's reason keeps unverified."""
        skill = (RESEARCH / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("the claim's the claim's", skill)
        self.assertIn(
            "A verifier's flag reaches you in the claim's `reason`, or in its `differs` for source fields.", skill
        )
        template = (RESEARCH / "templates" / "board.md").read_text(encoding="utf-8")
        self.assertIn("the `owner`, `status`, `summary`, `gist` and `note` of a question you own", template)
        verifier = (RESEARCH / "agents" / "verifier.md").read_text(encoding="utf-8")
        self.assertIn("If you have a reason to write, the claim is `unverified`.", verifier)

    def test_eval_board_lib_none_treats_the_string_none_as_missing(self) -> None:
        """board_lib.none is true for None, "", "none" and [], and false for a real value."""
        sys.path.insert(0, str(ROOT / "evals/cases/research-better/_checks"))
        try:
            import board_lib
        finally:
            sys.path.pop(0)
        for value in (None, "", "none", []):
            self.assertTrue(board_lib.none(value), repr(value))
        for value in ("text", ["a"], 0):
            self.assertFalse(board_lib.none(value), repr(value))

    def test_no_step_deletes_a_record_others_point_to(self) -> None:
        """The coordinator's steps withdraw, mark a duplicate or merge; none says to delete."""
        skill = (RESEARCH / "SKILL.md").read_text(encoding="utf-8")
        section = skill[skill.index("#### 6.2.") : skill.index("### 7.")]
        self.assertNotRegex(section, r"\bDELETE\b")
        self.assertIn("merged_into", section)
        self.assertIn("withdrawn", section)

    def test_template_has_a_line_for_every_record_type_and_status(self) -> None:
        """One placeholder line per record type, and a line naming each status the schemas give a record's shape."""
        records = template_records()
        types = {r["type"] for r in records}
        logs = schema_json("logs.schema.json")["properties"]["type"]["enum"]
        self.assertEqual(types, set(RECORD_FILES) | set(logs))
        for kind, name in RECORD_FILES.items():
            lines = {value.strip(" <>") for r in records if r["type"] == kind for value in str(r["status"]).split("|")}
            statuses = DECISION_STATUSES if kind == "decision" else schema_json(name)["properties"]["status"]["enum"]
            for status in statuses:
                with self.subTest(kind=kind, status=status):
                    self.assertIn(status, lines, f"no {kind} line for status {status}")

    def test_template_has_placeholders_only(self) -> None:
        """The template holds no example IDs, and its challenge question has a question as origin."""
        text = (RESEARCH / "templates" / "board.md").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\b[QCS]-w\d", text), "an example ID")
        challenge = [r for r in template_records() if r["type"] == "question" and r["kind"] == "challenge"]
        self.assertTrue(challenge, "no challenge question line")
        for record in challenge:
            self.assertEqual(record["origin"]["type"], "question")

    def test_null_date_is_accepted_and_planted_in_the_missing_field_board(self) -> None:
        """A source with date null passes the schema check, and S-w2-2 of findings-missing-field has none."""
        planted = ROOT / "evals/cases/research-better/findings-missing-field/repo/.research/checkout-drop/sources"
        record = json.loads((planted / "S-w2-2.json").read_text(encoding="utf-8"))
        self.assertIsNone(record["date"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources" / "S-w2-2.json"
            path.parent.mkdir()
            path.write_text(json.dumps(record), encoding="utf-8")
            docs = better_schema.load_schemas(*resources.schema_sources("research"))
            self.assertEqual(better_schema.check_paths([path], docs=docs), [])

    def test_planted_challenge_questions_are_not_owned_by_the_answerer(self) -> None:
        """A planted challenge question is not owned by the agent that owns the question it challenges."""
        for path in sorted((ROOT / "evals/cases/research-better").glob("*/repo/.research/*/questions/*.json")):
            q = json.loads(path.read_text(encoding="utf-8"))
            if q["kind"] != "challenge" or "owner" not in q:
                continue
            origin = json.loads((path.parent / (q["origin"]["question"] + ".json")).read_text(encoding="utf-8"))
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotEqual(q["owner"], origin.get("owner"))

    def test_eval_board_lib_reads_a_pretty_printed_json_file(self) -> None:
        """board_lib.entry reads a .json file that spans several lines, as schema.py does."""
        sys.path.insert(0, str(ROOT / "evals/cases/research-better/_checks"))
        try:
            import board_lib
        finally:
            sys.path.pop(0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Q-w1-1.json"
            path.write_text(json.dumps({"id": "Q-w1-1", "status": "open"}, indent=2), encoding="utf-8")
            self.assertEqual(board_lib.entry(path)["status"], "open")

    def test_template_lines_use_only_the_schemas_fields(self) -> None:
        """Each placeholder line holds every field its record type requires and no field its schema lacks."""
        schemas = {kind: schema_json(name) for kind, name in RECORD_FILES.items()}
        defs = schema_json("logs.schema.json")["$defs"]
        shared = {"challenge": "after", "chain": "after", "strategy": "text", "stop": "text"}
        for record in template_records():
            kind = record["type"]
            doc = schemas[kind] if kind in schemas else defs[shared.get(kind, kind)]
            allowed = DECISION_FIELDS if kind == "decision" else set(doc["properties"])
            required = {"type", "raised_by", "about", "asked", "status"} if kind == "decision" else set(doc["required"])
            with self.subTest(type=kind, status=record.get("status")):
                self.assertLessEqual(set(record), allowed)
                self.assertLessEqual(required - STAMPED, set(record))

    def test_every_planted_eval_board_passes_the_schema_check(self) -> None:
        """Each board under evals/cases/research-better/*/repo/.research/ has a brief.json and no schema error."""
        boards = sorted((ROOT / "evals" / "cases" / "research-better").glob("*/repo/.research/*"))
        self.assertTrue(boards)
        for board in boards:
            with self.subTest(board=str(board.relative_to(ROOT))):
                self.assertTrue((board / "brief.json").is_file(), "no brief.json")
                with tempfile.TemporaryDirectory() as tmp:  # a unit sits at <root>/.research/<slug>
                    shutil.copytree(board, Path(tmp) / ".research" / board.name)
                    done = better.run("research-better", "check", f".research/{board.name}", cwd=tmp)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


CODE_BETTER = ROOT / "skills" / "code-better"
CODE_SCHEMAS = CODE_BETTER / "schemas"
CASES = ROOT / "evals" / "cases" / "code-better"


def load_schema_module():
    spec = importlib.util.spec_from_file_location("code_better_schema", CODE_BETTER / "scripts" / "schema.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("code_better_schema", module)
    spec.loader.exec_module(module)
    return module


schema = load_schema_module()

CODE_TEXT_FILES = sorted(
    [CODE_BETTER / "SKILL.md"]
    + list((CODE_BETTER / "modes").glob("*.md"))
    + list((CODE_BETTER / "agents").glob("*.md"))
    + list((CODE_BETTER / "templates").glob("*.md"))
    + [ROOT / "docs" / "code-better.md"]
)

# The files the skill no longer writes. A template may still be called tasks.md or next-steps.md.
CODE_OLD_FILES = re.compile(
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
    "lessons.md": ["lessons"],
    "log.md": ["card", "log"],
    "audit.md": ["audit", "evidence", "findings"],
}

# A shape a schema does not name with an if/then, but that a template must still show.
EXTRA_SHAPES = {"tasks": [("reason", {"user"}), ("reason", {"repair limit"})]}


# Until the schemas move into the command, the old ones name `step`, and no `default` or `deadline` on a decision.
TYPE_ALIASES = {"next_step": "step"}
NEW_FIELDS = {"default", "deadline"}


def read_schema(name: str) -> dict:
    return json.loads((CODE_SCHEMAS / f"{name}.schema.json").read_text())


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
            for path in CODE_TEXT_FILES
            for number, line in enumerate(path.read_text().splitlines(), 1)
            for match in CODE_OLD_FILES.finditer(line)
        ]
        self.assertEqual(found, [])

    def test_code_better_the_record_rule_is_in_skill_md_and_both_agents_only(self):
        """SKILL.md states the record rule once, the builder and the verifier restate it, and the modes do not."""
        rule = (
            "WRITE each record of a unit with `python3 <skill dir>/scripts/better.pyz add <unit> <type> --by <your agent name>`,"
            " with its fields as JSON on stdin, or edit it with `set`. IF it refuses the record, FIX the record and RUN"
            " it again. IF it reports busy, RUN it again. DO NOT write the record by hand to get past a refusal."
        )
        skill = (CODE_BETTER / "SKILL.md").read_text()
        self.assertEqual(skill.count(rule), 1)
        self.assertIn("IF you cannot run commands, the rule of Missing capabilities applies", skill)
        for name in ("builder.md", "verifier.md"):
            text = (CODE_BETTER / "agents" / name).read_text()
            self.assertIn(rule + " IF you cannot run commands, STOP and SAY so in your hand-back.", text, name)
        for mode in sorted((CODE_BETTER / "modes").glob("*.md")):
            text = mode.read_text()
            self.assertNotIn("DO NOT write the record by hand", text, mode.name)
            self.assertNotIn("check <file>", text, mode.name)

    def test_code_better_every_template_is_present(self):
        names = sorted(path.name for path in (CODE_BETTER / "templates").glob("*.md"))
        self.assertEqual(names, sorted(TEMPLATES))

    def test_code_better_templates_hold_a_line_for_every_record_type_and_shape(self):
        """One placeholder line per record type and status shape of each schema, as JSON, with only schema fields."""
        problems = []
        for template, names in TEMPLATES.items():
            lines = [
                dict(line, type=TYPE_ALIASES.get(line["type"], line["type"])) for line in placeholder_lines(template)
            ]
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
                    extra = [key for node in walk(line) for key in node if key not in names_in(doc) | NEW_FIELDS]
                    if extra:
                        problems.append(f"templates/{template}: {line['type']} line has fields {extra} not in {name}")
                    kind = doc.get("$defs", {}).get(line["type"], doc)
                    missing = [key for key in kind.get("required", []) if key not in line and key not in STAMPED]
                    if missing:
                        problems.append(f"templates/{template}: {line['type']} line lacks {missing}")
            stray = [line for line in lines if not any(line.get("type") in type_values(read_schema(n)) for n in names)]
            if stray:
                problems.append(f"templates/{template}: a line has a type no schema of it has: {stray[0].get('type')}")
        self.assertEqual(problems, [])

    def test_code_better_templates_name_no_check_and_no_schema_folder(self):
        """A template names neither `schema.py` nor `schemas/`: the command checks, and the lines show the fields."""
        for template in TEMPLATES:
            text = (CODE_BETTER / "templates" / template).read_text()
            self.assertNotIn("schema.py", text, template)
            self.assertNotIn("schemas/", text, template)

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
        runs: dict[str, list[tuple[str, str]]] = {}
        for where, text in files:
            runs.setdefault(where.split(":", 1)[0], []).append((where.split(":", 1)[1], text))
        for run, written in runs.items():
            with tempfile.TemporaryDirectory() as temp:
                for relative, text in written:
                    self.assertFalse(relative.endswith(".md"), f"{run}: {relative} is an old Markdown file")
                    path = Path(temp) / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(text)
                problems += [f"{run}: {error}" for error in schema.check_paths([Path(temp) / ".code"], CODE_SCHEMAS)]
        self.assertEqual(problems, [])

    def test_code_better_a_solo_mode_can_record_a_question_and_the_spec_always_exists(self):
        """A solo run records its questions, and every mode writes spec.jsonl, which tasks and gaps point to."""
        skill = (CODE_BETTER / "SKILL.md").read_text()
        self.assertIn(
            "RECORD each question you ask in `decisions.jsonl` with status `waiting` before the gap that points to it",
            skill,
        )
        decision = (CODE_BETTER / "templates" / "decision.md").read_text()
        self.assertIn("In coordinate mode only the coordinator writes it", decision)
        self.assertNotIn("Only the coordinator writes it", decision)
        for mode in ("feature", "bug-fix", "refactor", "tests", "coordinate"):
            text = (CODE_BETTER / "modes" / f"{mode}.md").read_text()
            self.assertIn("scripts/better.pyz create .code/<change>", text, mode)
            self.assertIn("`spec.jsonl`", text, mode)
            self.assertNotIn("IF no existing spec covers the change, READ", text, mode)
            self.assertIn("UPDATE its files from it", text, mode)

    def test_code_better_eval_note_checks_count_code_json_working_files(self):
        """The hidden checks that look for notes accept a `.code/` JSON working file, as a run of the skill writes."""
        cases = [
            ("record-session-constraint/checks/command_passes_3/recorded.py", [], "instructions.jsonl"),
            ("shared-migration-plan/checks/command_passes_1/plan.py", ["sales", "stock"], "tasks.jsonl"),
            ("oldlog-multi-session-plan/checks/command_passes/plan.py", ["billing", "search"], "tasks.jsonl"),
        ]
        for script, arguments, name in cases:
            with self.subTest(script=script), tempfile.TemporaryDirectory() as temp:
                repo = Path(temp)
                git = ["git", "-C", temp, "-c", "user.name=t", "-c", "user.email=t@t"]
                subprocess.run([*git, "init", "-q"], check=True)
                (repo / "a.py").write_text("x = 1\n")
                subprocess.run([*git, "add", "."], check=True)
                subprocess.run([*git, "commit", "-q", "-m", "start"], check=True)
                start = subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
                (repo / ".git" / "info" / "exclude").write_text(".code/\n")
                (repo / ".code" / "change").mkdir(parents=True)
                line = {"said": "Never change anything under vendor/", "text": " ".join(arguments) or "vendor/"}
                (repo / ".code" / "change" / name).write_text(json.dumps(line) + "\n")
                result = subprocess.run(
                    [sys.executable, str(CASES / script), *arguments],
                    cwd=temp,
                    env={"START_COMMIT": start, "PATH": "/usr/bin:/bin"},
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_code_better_judge_and_rubrics_name_the_json_working_files(self):
        """The judge's record and the no-plan rubrics cover `.code/` working files as well as Markdown notes."""
        judge = (ROOT / "evals" / "skill_evals" / "grading" / "judge.py").read_text()
        self.assertNotIn('"Markdown notes the agent wrote or changed"', judge)
        for case in ("iso-dates-no-plan", "no-plan-one-session", "no-plan-small-fix"):
            text = (CASES / case / "case.yaml").read_text()
            self.assertIn("any Markdown note or `.code/` working file", " ".join(text.split()), case)
        oldlog = " ".join((CASES / "oldlog-multi-session-plan" / "case.yaml").read_text().split())
        self.assertIn("Markdown notes or `.code/` working files", oldlog)

    def test_code_better_good_audit_replays_model_the_format(self):
        """A good audit replay writes audit.json, evidence.jsonl and findings.jsonl, with a real cost and a where."""
        for replay in sorted(CASES.glob("audit-*/replays/good-*.yaml")):
            text = replay.read_text()
            if "findings.jsonl" not in text:
                continue
            with self.subTest(replay=str(replay.relative_to(CASES))):
                self.assertIn("/audit.json", text)
                self.assertIn("/evidence.jsonl", text)
                block = text[text.index("write: .code/audit/2026-11-21/findings.jsonl") :]
                for line in re.findall(r"(?m)^    (\{.*\})$", block):
                    record = json.loads(line)
                    self.assertTrue(record["where"], record["id"])
                    self.assertNotEqual(record["cost"], record["problem"], record["id"])

    def test_code_better_template_instructions_are_capitalised_imperatives(self):
        """The instructions in a template's fill-in block use verbs in capitals, as PRINCIPLES 6.1 asks."""
        weak = re.compile(
            r"(?:^- |[.:] )(?:Save|Add|Keep|Set|Give|Begin|Change|List|Put|Use|Write|Run|Read|Drop|Fix|Rewrite|Commit)\b"
        )
        for path in sorted((CODE_BETTER / "templates").glob("*.md")):
            block = path.read_text().split("<HOW TO FILL", 1)[1].split(">\n", 1)[0]
            found = [line[:50] for line in block.splitlines() if weak.search(line)]
            self.assertEqual(found, [], path.name)

    def test_code_better_an_architect_spec_never_points_to_a_code_better_decision(self):
        """With an architect folder's spec, a question goes to decisions.jsonl and the answer becomes a request source."""
        rule = "NEVER write a gap or a source in it that points to a decision"
        for path in (
            CODE_BETTER / "templates" / "spec.md",
            CODE_BETTER / "SKILL.md",
            CODE_BETTER / "modes" / "coordinate.md",
        ):
            text = path.read_text()
            self.assertIn("architect folder's `spec.jsonl`", text, path.name)
            self.assertIn(rule, text, path.name)
            self.assertIn("source `request`", text, path.name)

    def test_code_better_requirement_source_is_only_for_an_architect_folder_spec(self):
        """`requirements.jsonl` exists only in an architect folder, so the spec template limits that source to it."""
        text = (CODE_BETTER / "templates" / "spec.md").read_text()
        self.assertIn(
            "USE a source of type `requirement` only when the spec is a copy of an architect folder's `spec.jsonl`",
            text,
        )

    def test_code_better_small_text_fixes_of_round_three(self):
        """The decisions schema names its writers as the text does; the notes table and the tasks template are exact."""
        comment = json.loads((CODE_SCHEMAS / "decisions.schema.json").read_text())["$comment"]
        self.assertIn("In coordinate mode only the coordinator writes it", comment)
        skill = (CODE_BETTER / "SKILL.md").read_text()
        self.assertIn("EACH file below is typed JSON", skill)
        self.assertIn("`.code/audit/<YYYY-MM-DD>/audit.json`, `evidence.jsonl` and `findings.jsonl`", skill)
        tasks = (CODE_BETTER / "templates" / "tasks.md").read_text()
        self.assertIn(
            "ADD the tasks to `.code/<change>/tasks.jsonl`; IF the repo's spec tool also keeps tasks, "
            "UPDATE its tasks from it",
            tasks,
        )
        self.assertIn("EDIT the line with `set`", tasks)
        self.assertIn("COMMIT after each task", tasks)

    def test_code_better_lessons_are_in_the_coordinate_text_and_both_agents(self):
        """The coordinator writes lessons after each verifier report and gives the file to every agent, which uses it."""
        coordinate = (CODE_BETTER / "modes" / "coordinate.md").read_text()
        self.assertIn("lessons.jsonl", coordinate)
        self.assertNotIn("EXTEND its `found_in`", coordinate)
        self.assertIn("EDIT that lesson with `set`, with the task added to `found_in`", coordinate)
        self.assertIn("WRITE no second lesson", coordinate)
        self.assertIn(
            "SPLIT the task, GIVING each new task its own new `T<n>`, never a suffixed id such as `T5b`", coordinate
        )
        self.assertIn("found_in", coordinate)
        self.assertIn("`.code/<change>/lessons.jsonl` in every builder's and verifier's `lessons` input", coordinate)
        self.assertIn(
            "only you write `tasks.jsonl`, `progress.jsonl`, `instructions.jsonl`, `decisions.jsonl` and `lessons.jsonl`",
            coordinate,
        )
        builder = (CODE_BETTER / "agents" / "builder.md").read_text()
        self.assertIn('- `lessons`: <path of `.code/<change>/lessons.jsonl`, or "none">', builder)
        self.assertIn("CHECK your work against each lesson in `lessons` before you hand back", builder)
        verifier = (CODE_BETTER / "agents" / "verifier.md").read_text()
        self.assertIn('- `lessons`: <path of `.code/<change>/lessons.jsonl`, or "none">', verifier)
        self.assertIn("LOOK for the class of each lesson in `lessons`", verifier)

    def test_code_better_lessons_template_and_docs(self):
        """The template has one placeholder line and the conventions; the notes table and the docs name the file."""
        lines = placeholder_lines("lessons.md")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["type"], "lesson")
        template = (CODE_BETTER / "templates" / "lessons.md").read_text()
        self.assertNotIn("ADD its task", template)
        self.assertIn(
            "EDIT that lesson with `set`, with the task added to `found_in`; WRITE no second lesson",
            template,
        )
        self.assertIn("lessons.jsonl", (CODE_BETTER / "SKILL.md").read_text())
        docs = (ROOT / "docs" / "code-better.md").read_text()
        self.assertIn("`lessons.jsonl`", docs)

    def test_code_better_t4_text_fixes(self):
        """Decisions are named by their file, the builder does not write code.json or the spec, docs list decisions solo."""
        phrase = "a decision of `.code/<change>/decisions.jsonl`: RECORD the question in that file"
        for path in (
            CODE_BETTER / "SKILL.md",
            CODE_BETTER / "modes" / "coordinate.md",
            CODE_BETTER / "templates" / "spec.md",
        ):
            text = path.read_text()
            self.assertIn(phrase, text, path.name)
            self.assertNotIn("a decision of `decisions.jsonl`", text, path.name)
        builder = (CODE_BETTER / "agents" / "builder.md").read_text()
        self.assertIn("DO NOT write `code.json` or the spec: the coordinator holds them.", builder)
        docs = (ROOT / "docs" / "code-better.md").read_text()
        self.assertIn("- **Decisions**: `decisions.jsonl` holds", docs)

    def test_code_better_case_files_name_no_old_file(self):
        """The case files name the templates and files of the new format."""
        old = re.compile(r"templates/specs\.md|\.code/\S*\.md\b|(?<![\w-])notes\.md\b|\bspecs\.md\b")
        found = [
            f"{path.relative_to(ROOT)}: {match.group(0)}"
            for path in sorted(CASES.rglob("*.yaml"))
            for match in old.finditer(path.read_text())
        ]
        self.assertEqual(found, [])


OLD_SCRIPTS = re.compile(r"\b(?:dashboard|board|schema|page)\.py\b|\bschemas/")


class SkillTextCommands(unittest.TestCase):
    """The text of code-better and research-better names the commands of `better.pyz`, and the templates show only
    the fields an agent writes."""

    FOLDERS = (CODE_BETTER, RESEARCH)

    def files(self):
        for folder in self.FOLDERS:
            for sub in ("", "modes", "agents", "templates"):
                yield from sorted((folder / sub).glob("*.md"))

    def test_no_file_names_an_old_script_or_the_schemas_folder(self):
        found = [
            f"{path.relative_to(ROOT)}:{number}: {match.group(0)}"
            for path in self.files()
            for number, line in enumerate(path.read_text().splitlines(), 1)
            for match in OLD_SCRIPTS.finditer(line)
        ]
        self.assertEqual(found, [])

    def test_no_template_example_line_holds_at_by_or_id(self):
        found = []
        for path in self.files():
            if path.parent.name != "templates":
                continue
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if line.startswith("{") and re.search(r'"(?:at|by|id)":', line):
                    found.append(f"{path.relative_to(ROOT)}:{number}")
        self.assertEqual(found, [])

    def test_commands_are_named_by_their_common_names(self):
        """Every `better.pyz` command line in the text uses a verb the contract names."""
        verbs = {"create", "add", "set", "check", "serve", "wait", "reply", "status", "pending", "render"}
        pattern = re.compile(r"scripts/better\.pyz (\S+)")
        for path in self.files():
            for verb in pattern.findall(path.read_text()):
                with self.subTest(file=path.name, verb=verb):
                    self.assertIn(verb, verbs)

    def test_each_text_that_writes_records_names_a_command_for_each_hand_made_unit(self):
        """The change folder, the audit folder and the board are made with `create`."""
        for relative in ("modes/feature.md", "modes/bug-fix.md", "modes/refactor.md", "modes/tests.md"):
            self.assertIn("better.pyz create .code/<change>", (CODE_BETTER / relative).read_text(), relative)
        self.assertIn(
            "better.pyz create .code/<change> --by coordinator", (CODE_BETTER / "modes/coordinate.md").read_text()
        )
        self.assertIn("better.pyz create .code/audit/<YYYY-MM-DD>", (CODE_BETTER / "modes/audit.md").read_text())
        self.assertIn("better.pyz create .research/<topic-slug>", (RESEARCH / "SKILL.md").read_text())

    def test_the_spec_copy_is_edited_in_the_change_folder(self):
        for path in (*sorted((CODE_BETTER / "modes").glob("*.md")), CODE_BETTER / "templates" / "spec.md"):
            text = path.read_text()
            self.assertNotIn("WRITE no copy", text, path.name)
            self.assertNotIn("UPDATE it there", text, path.name)

    def test_the_record_rule_is_deleted_from_templates_and_modes(self):
        for path in self.files():
            if path.parent.name in ("templates", "modes"):
                text = path.read_text()
                self.assertNotIn("after every write", text.casefold(), path.name)
                self.assertNotIn("START each record with", text, path.name)

    def test_serve_opens_the_browser_only_with_open_and_reply_takes_its_words_on_stdin(self):
        for path in self.files():
            text = path.read_text()
            for line in re.findall(r"better\.pyz serve [^`]*`", text):
                self.assertIn("--open", line, path.name)
            for line in re.findall(r"better\.pyz reply [^`]*`", text):
                self.assertNotIn('"', line, path.name)

    def test_the_text_does_not_say_what_a_command_writes(self):
        coordinate = (CODE_BETTER / "modes" / "coordinate.md").read_text()
        self.assertNotIn("The reply marks the item", coordinate)
        self.assertNotIn("it refuses a name another agent has", coordinate)
        self.assertNotIn("opens the user's browser", coordinate)
        self.assertNotIn("exits by itself", (RESEARCH / "SKILL.md").read_text())
        for path in self.files():
            text = path.read_text()
            self.assertNotIn("`create` makes", text, path.name)
            self.assertNotIn("`create` copies", text, path.name)

    def test_the_next_step_record_type_is_next_step(self):
        text = (CODE_BETTER / "templates" / "next-steps.md").read_text()
        self.assertIn('{"type": "next_step"', text)
        self.assertNotIn('{"type": "step"', text)

    def test_the_decision_shape_is_the_shared_one(self):
        for path in (CODE_BETTER / "templates" / "decision.md", RESEARCH / "templates" / "board.md"):
            text = path.read_text()
            for status in ("waiting", "defaulted", "answered"):
                self.assertIn(f'"status": "{status}"', text, path.name)
            self.assertNotIn('"status": "pending"', text, path.name)
            self.assertNotIn('"status": "changed"', text, path.name)
        self.assertIn("`+<minutes>m`", (CODE_BETTER / "templates" / "decision.md").read_text())


class UnifiedCommandText(unittest.TestCase):
    """architect-better, design-better and show-better: their text names `better.pyz` and no old script, states the
    record rule once in SKILL.md, and shows template lines with only each record's own fields."""

    SKILLS = ("architect-better", "design-better", "show-better")
    OLD = re.compile(r"\b(architect|diagram|canvas|show|schema|page)\.py\b|schemas/")
    RULE = (
        "WRITE each record of the unit with `python3 <skill dir>/scripts/better.pyz add <unit> <type> --by <your name>`, "
        "or `set`. IF it refuses the record, FIX the record and RUN it again. IF it reports busy, RUN it again. "
        "DO NOT write the record by hand to get past a refusal."
    )

    def texts(self, *names):
        for name in names or self.SKILLS:
            for path in sorted((ROOT / "skills" / name).rglob("*.md")):
                if "scripts" not in path.relative_to(ROOT / "skills" / name).parts:
                    yield path

    def test_no_text_names_an_old_script_or_schemas_as_the_authority(self):
        found = [f"{p.relative_to(ROOT)}: {m.group(0)}" for p in self.texts() for m in self.OLD.finditer(p.read_text())]
        self.assertEqual(found, [])

    def test_the_record_rule_is_stated_once_per_skill_that_writes_records(self):
        for name in ("architect-better", "design-better"):
            with self.subTest(name):
                self.assertEqual((ROOT / "skills" / name / "SKILL.md").read_text().count(self.RULE), 1)

    def test_no_text_tells_the_agent_to_check_after_every_write(self):
        for path in self.texts():
            with self.subTest(path.name):
                self.assertNotIn("AFTER every write", path.read_text())

    def test_no_template_example_line_holds_at_by_or_id(self):
        """The record templates are architect-better's; show-better's spec template is one object, not lines."""
        lines = 0
        for path in self.texts("architect-better"):
            if path.parent.name != "templates":
                continue
            for line in path.read_text().splitlines():
                if line.startswith("{") and line.endswith("}"):
                    lines += 1
                    record = json.loads(
                        re.sub(r"<[^<>\"]+>", "text", line)
                    )  # the spec of show-better is one JSON object
                    for field in ("at", "by", "id"):
                        self.assertNotIn(field, record, line)
        self.assertGreater(lines, 20)

    def test_show_better_names_commands_only_and_design_better_approves(self):
        spec = (ROOT / "skills" / "show-better" / "templates" / "spec.md").read_text()
        for verb in ("create", "check", "render", "serve", "wait", "reply", "status", "pending"):
            self.assertIn(f"better.pyz {verb} ", spec)
        design = (ROOT / "skills" / "design-better" / "SKILL.md").read_text()
        self.assertIn("`canvas.json`", design)
        self.assertNotIn("Decide", design)


if __name__ == "__main__":
    unittest.main()
