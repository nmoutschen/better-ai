"""Tests for the text of the skills that name the files an agent writes for bookkeeping.

code-better: its SKILL.md, modes, agents, templates and docs name the JSON files and their fields and none of the old
Markdown files, SKILL.md, each mode and each agent tell the writer to run `schema.py check` after every write, the
templates have a placeholder line for every record type and shape in the schemas, and every file the evals plant or
write under `.code/` passes the schema check.

research-better: its SKILL.md, worker and verifier prompts, board template and docs name the JSON board's files and
fields and none of the old Markdown board's, every step that writes tells the writer to run `schema.py check`, the
template has a placeholder line for every record type and status in the schemas, and every board the evals plant
passes the schema check.
"""

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "skills" / "research-better"
SCHEMAS = RESEARCH / "schemas"
SCHEMA_PY = RESEARCH / "scripts" / "schema.py"
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
CHECK_SENTENCE = (
    "After every write to the board, run `python3 <skill dir>/scripts/schema.py check <file>` "
    "and fix every error before your next step."
)
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
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


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

    def test_each_loop_starts_with_the_schema_check_sentence(self) -> None:
        """SKILL.md step 2, the worker's loop and the verifier's loop each say once, up front, to check every write."""
        for path in TEXTS[:3]:
            with self.subTest(file=path.name):
                self.assertIn(
                    CHECK_SENTENCE.lower(), path.read_text(encoding="utf-8").lower()
                )  # SKILL.md writes its verbs in capitals
        for name in ("worker.md", "verifier.md"):
            text = (RESEARCH / "agents" / name).read_text(encoding="utf-8")
            loop = text[text.index("## Loop") :]
            with self.subTest(file=name):
                self.assertTrue(
                    loop[len("## Loop") :].lstrip().startswith(CHECK_SENTENCE), "not at the head of the loop"
                )
        skill = (RESEARCH / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("schema.py check <file>` from this skill's directory", skill)

    def test_the_board_template_has_the_schema_check_sentence(self) -> None:
        """The conventions in templates/board.md carry the check sentence."""
        text = (RESEARCH / "templates" / "board.md").read_text(encoding="utf-8")
        self.assertIn(CHECK_SENTENCE, text)

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
            for status in schema_json(name)["properties"]["status"]["enum"]:
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
            done = subprocess.run(
                [sys.executable, "-I", str(SCHEMA_PY), "check", str(path)], capture_output=True, text=True
            )
            self.assertEqual(done.returncode, 0, done.stdout)

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
            with self.subTest(type=kind, status=record.get("status")):
                self.assertLessEqual(set(record), set(doc["properties"]))
                self.assertLessEqual(set(doc["required"]), set(record))

    def test_every_planted_eval_board_passes_the_schema_check(self) -> None:
        """Each board under evals/cases/research-better/*/repo/.research/ has a brief.json and no schema error."""
        boards = sorted((ROOT / "evals" / "cases" / "research-better").glob("*/repo/.research/*"))
        self.assertTrue(boards)
        for board in boards:
            with self.subTest(board=str(board.relative_to(ROOT))):
                self.assertTrue((board / "brief.json").is_file(), "no brief.json")
                done = subprocess.run(
                    [sys.executable, "-I", str(SCHEMA_PY), "check", str(board)], capture_output=True, text=True
                )
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

    def test_code_better_every_entry_point_runs_schema_check_after_a_write(self):
        """SKILL.md, each mode, the builder and the verifier say once to check every file written in `.code/`."""
        sentence = (
            "after every write to a json or jsonl file in `.code/`, or to the architect folder's `spec.jsonl`, "
            "run `python3 <skill dir>/scripts/schema.py check <file>` and fix every error before your next step."
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
            self.assertIn("WRITE `.code/<change>/spec.jsonl`", text, mode)
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

    def test_code_better_small_text_fixes_of_round_three(self):
        """The decisions schema names its writers as the text does; the notes table and the tasks template are exact."""
        comment = json.loads((CODE_SCHEMAS / "decisions.schema.json").read_text())["$comment"]
        self.assertIn("In coordinate mode only the coordinator writes it", comment)
        skill = (CODE_BETTER / "SKILL.md").read_text()
        self.assertIn("EACH file below is typed JSON", skill)
        self.assertIn("`.code/audit/<YYYY-MM-DD>/audit.json`, `evidence.jsonl` and `findings.jsonl`", skill)
        tasks = (CODE_BETTER / "templates" / "tasks.md").read_text()
        self.assertIn(
            "SAVE the tasks in `.code/<change>/tasks.jsonl`; IF the repo's spec tool also keeps tasks, "
            "UPDATE its tasks from it",
            tasks,
        )
        self.assertIn("REWRITE the line in place", tasks)
        self.assertIn("COMMIT after each task", tasks)

    def test_code_better_lessons_are_in_the_coordinate_text_and_both_agents(self):
        """The coordinator writes lessons after each verifier report and gives the file to every agent, which uses it."""
        coordinate = (CODE_BETTER / "modes" / "coordinate.md").read_text()
        self.assertIn("lessons.jsonl", coordinate)
        self.assertNotIn("EXTEND its `found_in`", coordinate)
        self.assertIn(
            "REWRITE that lesson's line in place, keeping `at` and `by`, with the task added to `found_in`", coordinate
        )
        self.assertIn("WRITE no second lesson", coordinate)
        self.assertIn("a split task gets a new `T<n>`, never `T5b`", coordinate)
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
            "REWRITE that lesson's line in place, keeping `at` and `by`, with the task added to `found_in`; "
            "WRITE no second lesson",
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


if __name__ == "__main__":
    unittest.main()
