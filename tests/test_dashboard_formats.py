"""code-better's files as typed JSON: the schemas of every file kind on the spec page, and the dashboard that reads them.

The examples of the spec page (tests/fixtures/code-better-examples.json) are the fixtures: each must validate. A change
folder built from them must check clean, one bad record per kind must be reported with file:line and field, and
dashboard.py must show every valid record next to the errors of the invalid ones.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "code-better" / "scripts"
SCHEMAS = ROOT / "skills" / "code-better" / "schemas"
EXAMPLES = json.loads((Path(__file__).parent / "fixtures" / "code-better-examples.json").read_text())


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


schema = load("schema", SCRIPTS / "schema.py")
dashboard = load("dashboard_formats_dashboard", SCRIPTS / "dashboard.py")

# The spec page's file kinds, the schema each is checked against, and where the file sits in a change folder.
KINDS = {
    "code.json": ("code.schema.json", "code.json"),
    "spec.jsonl": ("spec.schema.json", "spec.jsonl"),
    "tasks.jsonl": ("tasks.schema.json", "tasks.jsonl"),
    "progress.jsonl": ("progress.schema.json", "progress.jsonl"),
    "decisions.jsonl": ("decisions.schema.json", "decisions.jsonl"),
    "next-steps.jsonl": ("next-steps.schema.json", "next-steps.jsonl"),
    "instructions.jsonl": ("instructions.schema.json", "instructions.jsonl"),
    "logs/<agent>.card.json": ("card.schema.json", "logs/builder-t3.card.json"),
    "logs/<agent>.jsonl": ("log.schema.json", "logs/builder-t3.jsonl"),
    "audit/<date>/evidence.jsonl": ("evidence.schema.json", "audit/2026-11-21/evidence.jsonl"),
    "audit/<date>/findings.jsonl": ("findings.schema.json", "audit/2026-11-21/findings.jsonl"),
}
AUDIT = ("audit.schema.json", "audit/2026-11-21/audit.json")
AT = "2026-11-21T10:00:00Z"


def examples(kind):
    """The (title, record) pairs of one file kind on the spec page. The audit header is listed with the findings."""
    return [(e["title"], json.loads(e["line"])) for e in EXAMPLES[kind] if not e["title"].startswith("audit")]


def audit_header():
    (found,) = [
        json.loads(e["line"]) for e in EXAMPLES["audit/<date>/findings.jsonl"] if e["title"].startswith("audit")
    ]
    return found


def write(folder: Path, relative: str, records, as_json=False):
    path = folder / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if as_json:
        path.write_text(json.dumps(records[0]) + "\n", encoding="utf-8")
    else:
        path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


def by_id(kind, wanted):
    return [r for _, r in examples(kind) if r.get("id") in wanted]


def spec(identity, statement="The upload service shall reject empty files.", **more):
    record = {"type": "spec", "at": AT, "by": "coordinator", "id": identity, "statement": statement}
    record["source"] = {"type": "request", "sentence": "empty uploads should fail loudly"}
    record["checked_by"] = "code review"
    return {**record, **more}


def task(identity, **more):
    record = {
        "type": "task",
        "at": AT,
        "by": "coordinator",
        "id": identity,
        "task": "Reject empty uploads",
        "mode": "feature",
        "requirements": ["S1"],
        "check": "uv run pytest",
        "status": "todo",
    }
    return {**record, **more}


def code(mode="coordinate", design=None):
    design = design or {"type": "request", "text": "empty uploads should fail loudly"}
    return {
        "type": "code",
        "at": AT,
        "by": "coordinator",
        "goal": "Uploads fail loudly",
        "design": design,
        "mode": mode,
    }


def card(role, task_id, **more):
    return {"type": "card", "at": AT, "by": "coordinator", "role": role, "task": task_id, "branch": "b", **more}


def log(kind, by, text="x", **more):
    return {"type": kind, "at": AT, "by": by, "text": text, **more}


def change(root: Path, mode="coordinate", tasks=None, specs=None, design=None) -> Path:
    """A small valid change folder: code.json, one spec record, the given tasks."""
    folder = root / ".code" / "c"
    write(folder, "code.json", [code(mode, design)], as_json=True)
    if specs is not False:
        write(folder, "spec.jsonl", specs or [spec("S1")])
    write(folder, "tasks.jsonl", tasks or [task("T1")])
    return folder


def check(folder: Path):
    return schema.check_paths([folder], SCHEMAS)


class Examples(unittest.TestCase):
    """Every example of the spec page validates against the schema of its file kind."""

    def test_every_example_has_a_schema_that_accepts_it(self):
        for kind, (name, _) in KINDS.items():
            for title, record in examples(kind):
                with self.subTest(kind=kind, example=title):
                    self.assertEqual(schema.check_record(record, [name], SCHEMAS), [])
        with self.subTest(kind="audit.json"):
            self.assertEqual(schema.check_record(audit_header(), [AUDIT[0]], SCHEMAS), [])

    def test_a_folder_built_from_the_examples_checks_clean(self):
        """Pointers resolve across the files: tasks to spec records, a block to its task, an answer to a page event."""
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / ".code" / "c"
            (Path(d) / ".git").mkdir()
            specs = [r for _, r in examples("spec.jsonl")]
            specs[0:0] = [spec("S5"), spec("S8")]
            specs[-3]["id"] = "G3"  # the spec page shows one gap twice, asked and answered: one file holds each id once
            write(folder, "code.json", [examples("code.json")[1][1] | {"mode": "coordinate"}], as_json=True)
            write(folder, "spec.jsonl", specs)
            write(folder, "requirements.jsonl", [{"type": "requirement", "at": AT, "by": "architect", "id": "Q1"}])
            tasks = [r for _, r in examples("tasks.jsonl")]
            tasks[0]["status"] = "building"  # `verified` needs a verifier: its own check below
            write(folder, "tasks.jsonl", tasks)
            write(folder, "progress.jsonl", [r for _, r in examples("progress.jsonl")])
            decisions = [{**r, "id": f"D{i + 1}"} for i, (_, r) in enumerate(examples("decisions.jsonl"))]
            write(folder, "decisions.jsonl", decisions)
            write(folder, "next-steps.jsonl", [r for _, r in examples("next-steps.jsonl")])
            write(folder, "instructions.jsonl", [r for _, r in examples("instructions.jsonl")])
            write(folder, "logs/builder-t3.card.json", [examples("logs/<agent>.card.json")[0][1]], as_json=True)
            write(folder, "logs/verifier-t3.card.json", [examples("logs/<agent>.card.json")[1][1]], as_json=True)
            builder_log = [r for t, r in examples("logs/<agent>.jsonl") if t != "handed_back, verifier"]
            write(folder, "logs/builder-t3.jsonl", builder_log)
            write(folder, "logs/verifier-t3.jsonl", [r for t, r in examples("logs/<agent>.jsonl") if "verifier" in t])
            write(folder, "audit/2026-11-21/audit.json", [audit_header()], as_json=True)
            write(folder, "audit/2026-11-21/evidence.jsonl", [r for _, r in examples("audit/<date>/evidence.jsonl")])
            write(folder, "audit/2026-11-21/findings.jsonl", [r for _, r in examples("audit/<date>/findings.jsonl")])
            write(
                folder,
                "conversation.jsonl",
                [
                    {
                        "type": "answer",
                        "at": AT,
                        "by": "user",
                        "id": "a-lq3z",
                        "decision": "D3",
                        "text": "50 MB",
                        "default": False,
                    }
                ],
            )
            self.assertEqual([str(e) for e in check(folder)], [])


class OneBadRecordPerKind(unittest.TestCase):
    """A bad record is reported with its file, its line and the field, and the good record above it is not."""

    BAD = {
        "code.json": (lambda r: {**r, "mode": "weird"}, "mode"),
        "spec.jsonl": (lambda r: {k: v for k, v in r.items() if k != "statement"}, "statement"),
        "tasks.jsonl": (lambda r: {**r, "status": "blocked"}, "reason"),
        "progress.jsonl": (lambda r: {k: v for k, v in r.items() if k != "text"}, "text"),
        "decisions.jsonl": (lambda r: {**r, "status": "answered"}, "answer"),
        "next-steps.jsonl": (lambda r: {**r, "priority": "urgent"}, "priority"),
        "instructions.jsonl": (lambda r: {k: v for k, v in r.items() if k != "said"}, "said"),
        "logs/<agent>.card.json": (lambda r: {**r, "role": "boss"}, "role"),
        "logs/<agent>.jsonl": (lambda r: {k: v for k, v in r.items() if k != "result"}, "result"),
        "audit/<date>/evidence.jsonl": (lambda r: {k: v for k, v in r.items() if k != "fact"}, "fact"),
        "audit/<date>/findings.jsonl": (lambda r: {**r, "status": "unconfirmed"}, "settle"),
    }

    def test_each_kind(self):
        for kind, (mutate, field) in self.BAD.items():
            _, relative = KINDS[kind]
            if kind == "logs/<agent>.jsonl":
                title, good = next((t, r) for t, r in examples(kind) if t.startswith("handed_back, builder"))
            elif kind == "tasks.jsonl":
                title, good = examples(kind)[0]
            elif kind == "decisions.jsonl":
                title, good = examples(kind)[1]
            else:
                title, good = examples(kind)[0]
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as d:
                folder = Path(d) / ".code" / "c"
                (Path(d) / ".git").mkdir()
                write(folder, "code.json", [code("feature")], as_json=True)
                if kind == "logs/<agent>.jsonl":
                    write(folder, "logs/builder-t3.card.json", [card("builder", "T3")], as_json=True)
                if kind in ("code.json", "logs/<agent>.card.json"):
                    records = [mutate(good)]
                else:
                    records = [good, mutate(good)]
                path = write(folder, relative, records, as_json=kind.endswith(".json"))
                errors = [e for e in schema.check_paths([path], SCHEMAS) if e.field.split(".")[0] == field]
                self.assertTrue(errors, f"{kind}: no error on {field} for {title}")
                self.assertEqual(errors[0].line, 1 if kind.endswith(".json") else 2)
                self.assertTrue(errors[0].file.endswith(relative))

    def test_the_audit_header(self):
        with tempfile.TemporaryDirectory() as d:
            record = {k: v for k, v in audit_header().items() if k != "goal"}
            path = write(Path(d), AUDIT[1], [record], as_json=True)
            self.assertEqual([e.field for e in schema.check_paths([path], SCHEMAS)], ["goal"])


class StatusRules(unittest.TestCase):
    def test_a_task_pointing_at_a_missing_spec_record_is_dangling(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d), tasks=[task("T1", requirements=["S1", "S9"])])
            errors = check(folder)
            self.assertEqual(
                [(e.file.endswith("tasks.jsonl"), e.line, e.field) for e in errors], [(True, 1, "requirements[1]")]
            )
            self.assertIn("dangling", errors[0].message)

    def test_a_blocked_task_names_its_reason_and_the_task_it_waits_on(self):
        with tempfile.TemporaryDirectory() as d:
            ok = [task("T1"), task("T2", status="blocked", reason="task", waits_on="T1")]
            self.assertEqual(check(change(Path(d), tasks=ok)), [])
        with tempfile.TemporaryDirectory() as d:
            bad = [task("T1"), task("T2", status="blocked", reason="task", waits_on="T9")]
            self.assertIn("dangling", check(change(Path(d), tasks=bad))[0].message)
        with tempfile.TemporaryDirectory() as d:
            bad = [task("T1"), task("T2", status="blocked", reason="user", waits_on="T1")]
            self.assertEqual([e.field for e in check(change(Path(d), tasks=bad))], ["waits_on"])

    def test_a_coordinate_task_cannot_be_done_and_another_mode_cannot_be_merged(self):
        with tempfile.TemporaryDirectory() as d:
            errors = check(change(Path(d), "coordinate", tasks=[task("T1", status="done")]))
            self.assertEqual([e.field for e in errors], ["status"])
            self.assertIn('"done" is not allowed when mode is "coordinate"', errors[0].message)
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(check(change(Path(d), "feature", tasks=[task("T1", status="done")])), [])
            errors = check(change(Path(d) / "x", "feature", tasks=[task("T1", status="merged")]))
            self.assertEqual([e.field for e in errors], ["status"])

    def test_verified_needs_a_passing_verifier_card(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d), tasks=[task("T1", status="verified")])
            self.assertIn("verifier card", check(folder)[0].message)
            write(folder, "logs/verifier-t1.card.json", [card("verifier", "T1")], as_json=True)
            write(folder, "logs/verifier-t1.jsonl", [log("start", "verifier-t1")])
            self.assertIn("has not handed back", check(folder)[0].message)
            write(
                folder,
                "logs/verifier-t1.jsonl",
                [log("start", "verifier-t1"), log("handed_back", "verifier-t1", result="fails")],
            )
            self.assertIn('handed back "fails"', check(folder)[0].message)
            write(
                folder,
                "logs/verifier-t1.jsonl",
                [log("start", "verifier-t1"), log("handed_back", "verifier-t1", result="passes")],
            )
            self.assertEqual(check(folder), [])

    def test_a_hand_back_result_must_fit_the_role_of_its_card(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            write(folder, "logs/b1.card.json", [card("builder", "T1")], as_json=True)
            write(folder, "logs/b1.jsonl", [log("handed_back", "b1", result="passes")])
            errors = check(folder)
            self.assertEqual([e.field for e in errors], ["result"])

    def test_a_decision_answered_on_the_page_points_to_the_event(self):
        decision = {
            "type": "decision",
            "at": AT,
            "by": "coordinator",
            "id": "D1",
            "raised_by": "b1",
            "about": {"type": "change"},
            "asked": "Which?",
            "status": "answered",
            "answer": {"type": "page", "event": "a-1"},
        }
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            write(folder, "decisions.jsonl", [decision])
            self.assertIn("dangling", check(folder)[0].message)
            write(
                folder,
                "conversation.jsonl",
                [
                    {
                        "type": "answer",
                        "at": AT,
                        "by": "user",
                        "id": "a-1",
                        "decision": "D1",
                        "text": "A",
                        "default": False,
                    }
                ],
            )
            self.assertEqual(check(folder), [])

    def test_a_task_in_the_architect_folder_resolves_its_requirements_there(self):
        design = {"type": "architect", "folder": "docs/designs/up/"}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".git").mkdir()
            folder = change(root, specs=False, design=design, tasks=[task("T1", requirements=["S3"])])
            self.assertIn("dangling", check(folder)[0].message)
            write(root / "docs" / "designs" / "up", "spec.jsonl", [spec("S3")])
            self.assertEqual(check(folder), [])


class Dashboard(unittest.TestCase):
    def test_a_folder_with_one_bad_task_still_shows_every_other_task(self):
        with tempfile.TemporaryDirectory() as d:
            tasks = [task("T1"), task("T2", status="in review"), task("T3", status="built")]
            folder = change(Path(d), tasks=tasks)
            data = dashboard.load(folder)
        self.assertEqual([t["id"] for t in data["tasks"]], ["T1", "T3"])
        (error,) = data["errors"]
        self.assertEqual(
            (error["file"], error["line"], error["field"], error["by"]), ("tasks.jsonl", 2, "status", "coordinator")
        )
        self.assertIn("must be one of", error["message"])

    def test_an_unparsed_line_is_an_error_without_an_author(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            with (folder / "tasks.jsonl").open("a") as f:
                f.write("{not json\n")
            data = dashboard.load(folder)
        self.assertEqual([t["id"] for t in data["tasks"]], ["T1"])
        self.assertEqual([(e["file"], e["line"]) for e in data["errors"]], [("tasks.jsonl", 2)])
        self.assertNotIn("by", data["errors"][0])

    def test_the_dashboard_reads_each_file_it_shows(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d), tasks=[task("T1", status="building"), task("T2", mode="bug fix")])
            write(folder, "logs/b1.card.json", [card("builder", "T2")], as_json=True)
            write(
                folder,
                "logs/b1.jsonl",
                [log("start", "b1", "reading"), log("step", "b1", "wrote the check"), log("asked", "b1", "which sort")],
            )
            write(folder, "logs/v1.card.json", [card("verifier", "T1")], as_json=True)
            write(folder, "logs/v1.jsonl", [log("handed_back", "v1", "all met", result="passes")])
            write(folder, "logs/b2.card.json", [card("builder", "T1")], as_json=True)  # started, no log line yet
            chat = {"answer": {"type": "chat", "text": "50 MB"}, "status": "answered"}
            decision = {
                "type": "decision",
                "at": AT,
                "by": "coordinator",
                "id": "D1",
                "raised_by": "b1",
                "about": {"type": "task", "task": "T2"},
                "asked": "Which limit?",
            }
            write(folder, "decisions.jsonl", [{**decision, **chat}, {**decision, "id": "D2", "status": "waiting"}])
            data = dashboard.load(folder)
        self.assertEqual(data["errors"], [])
        self.assertEqual(data["name"], "c")
        self.assertEqual(data["requirements"], {"S1": "The upload service shall reject empty files."})
        agents = {a["name"]: a for a in data["agents"]}
        self.assertEqual(
            (agents["b1"]["role"], agents["b1"]["task"], agents["b1"]["state"]), ("builder", "T2", "waiting")
        )
        self.assertEqual(agents["b1"]["mode"], "bug fix")  # the mode is the task's, the card has none
        self.assertEqual(agents["b1"]["branch"], "b")
        self.assertEqual([x["type"] for x in agents["b1"]["lines"]], ["start", "step", "asked"])
        self.assertEqual((agents["v1"]["role"], agents["v1"]["state"]), ("verifier", "finished"))
        self.assertEqual((agents["b2"]["task"], agents["b2"]["state"]), ("T1", "working"))
        decisions = {x["id"]: x for x in data["decisions"]}
        self.assertEqual(
            (decisions["D1"]["status"], decisions["D1"]["answer"], decisions["D1"]["from"]), ("answered", "50 MB", "b1")
        )
        self.assertEqual((decisions["D1"]["task"], decisions["D2"]["status"]), ("T2", "waiting"))

    def test_a_decision_answered_on_the_page_shows_the_event_text(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            event = {
                "type": "answer",
                "at": AT,
                "by": "user",
                "id": "a-1",
                "decision": "D1",
                "text": "Business days.",
                "default": False,
            }
            write(folder, "conversation.jsonl", [event])
            decision = {
                "type": "decision",
                "at": AT,
                "by": "coordinator",
                "id": "D1",
                "raised_by": "coordinator",
                "about": {"type": "change"},
                "asked": "Which?",
                "status": "answered",
                "answer": {"type": "page", "event": "a-1"},
            }
            write(folder, "decisions.jsonl", [decision])
            data = dashboard.load(folder)
        self.assertEqual(data["errors"], [])
        self.assertEqual(data["decisions"][0]["answer"], "Business days.")

    def test_a_task_pointing_at_a_missing_spec_record_is_listed_as_dangling(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d), tasks=[task("T1"), task("T2", requirements=["S4"])])
            data = dashboard.load(folder)
        self.assertEqual([t["id"] for t in data["tasks"]], ["T1"])
        self.assertIn("dangling", data["errors"][0]["message"])
        self.assertEqual(data["errors"][0]["field"], "requirements[0]")

    def test_requirements_resolve_through_the_architect_folder(self):
        design = {"type": "architect", "folder": "docs/designs/up/"}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".git").mkdir()
            write(root / "docs" / "designs" / "up", "spec.jsonl", [spec("S3", "The page shall show errors.")])
            folder = change(root, specs=False, design=design, tasks=[task("T1", requirements=["S3"])])
            data = dashboard.load(folder)
        self.assertEqual(data["errors"], [])
        self.assertEqual(data["requirements"], {"S3": "The page shall show errors."})
        self.assertEqual(data["tasks"][0]["requirements"], ["S3"])

    def test_the_old_markdown_files_are_not_read(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d), tasks=[task("T1")])
            (folder / "tasks.md").write_text("| # | Task | Status |\n|---|---|---|\n| T9 | Old | done |\n")
            (folder / "specs.md").write_text("| ID | Requirement |\n|---|---|\n| R1 | Old |\n")
            (folder / "decisions").mkdir()
            (folder / "decisions" / "D-1.md").write_text("id: D-1\nstatus: waiting\n")
            (folder / "logs").mkdir()
            (folder / "logs" / "old.md").write_text("start: x\n")
            (folder / "logs" / "old.json").write_text('{"role": "builder"}')
            data = dashboard.load(folder)
        self.assertEqual(
            ([t["id"] for t in data["tasks"]], data["decisions"], data["agents"], data["errors"]), (["T1"], [], [], [])
        )

    def test_an_empty_folder_loads_without_error(self):
        with tempfile.TemporaryDirectory() as d:
            data = dashboard.load(Path(d))
        self.assertEqual((data["tasks"], data["agents"], data["decisions"]), ([], [], []))

    def test_verified_without_a_passing_verifier_is_listed(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d), tasks=[task("T1", status="verified")])
            data = dashboard.load(folder)
        self.assertEqual(data["tasks"], [])
        self.assertIn("verifier", data["errors"][0]["message"])

    def test_a_coordinate_task_with_status_done_is_listed(self):
        with tempfile.TemporaryDirectory() as d:
            data = dashboard.load(change(Path(d), tasks=[task("T1", status="done")]))
        self.assertEqual([(e["file"], e["field"]) for e in data["errors"]], [("tasks.jsonl", "status")])


class Check(unittest.TestCase):
    def run_check(self, folder):
        cmd = [sys.executable, "-I", str(SCRIPTS / "dashboard.py"), "check", str(folder)]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    def test_check_exits_one_on_a_bad_folder_and_zero_on_a_good_one(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            good = self.run_check(folder)
            self.assertEqual((good.returncode, good.stdout), (0, ""))
            with (folder / "tasks.jsonl").open("a") as f:
                f.write(json.dumps(task("T2", status="in review")) + "\n")
            bad = self.run_check(folder)
            self.assertEqual(bad.returncode, 1)
            lines = bad.stdout.strip().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertRegex(lines[0], r"tasks\.jsonl:2: status: must be one of")
            data = dashboard.load(folder)
            self.assertEqual(lines, [f"{e['file']}:{e['line']}: {e['field']}: {e['message']}" for e in data["errors"]])

    def test_check_reads_the_files_the_page_does_not_show(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            write(folder, "next-steps.jsonl", [{"type": "step", "at": AT, "by": "coordinator"}])
            self.assertEqual(self.run_check(folder).returncode, 1)


class Usage(unittest.TestCase):
    def test_the_usage_line_for_accepted_shows_the_users_words(self):
        doc = dashboard.__doc__
        self.assertIn('accepted ID... --text "the user\'s words"', doc)

    def test_a_note_on_the_dashboard_cannot_carry_an_on_field(self):
        note = {"type": "note", "at": AT, "by": "user", "id": "m-1", "text": "hi", "to": None}
        names = ["dashboard-events.schema.json"]
        self.assertEqual(schema.check_record(note, names, SCHEMAS), [])
        problems = schema.check_record({**note, "on": {"kind": "agent", "id": "b1", "title": "b1"}}, names, SCHEMAS)
        self.assertEqual([field for field, _ in problems], ["on"])


class NoOldFiles(unittest.TestCase):
    """No code-better instruction or script writes the old Markdown files."""

    def test_no_script_reads_or_writes_them(self):
        text = (SCRIPTS / "dashboard.py").read_text()
        for old in ("tasks.md", "specs.md", "decisions/", "logs/*.md", "read_tasks", "read_requirements", "read_entry"):
            self.assertNotIn(old, text)


if __name__ == "__main__":
    unittest.main()
