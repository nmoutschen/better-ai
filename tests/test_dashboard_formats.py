"""code-better's files as typed JSON: the schemas of every file kind on the spec page, and the dashboard that reads them.

The examples of the spec page (tests/fixtures/code-better-examples.json) are the fixtures: each must validate. A change
folder built from them must check clean, one bad record per kind must be reported with file:line and field, and
the dashboard must show every valid record next to the errors of the invalid ones.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import sweep  # noqa: E402
import wrong_types  # noqa: E402
from better import call  # noqa: E402
from better import run as better  # noqa: E402
from code_records import (  # noqa: E402
    AT,
    DOCS,
    card,
    change,
    check,
    check_record,
    code,
    load,
    log,
    spec,
    task,
    write,
)

from better_ai import paths, schema  # noqa: E402
from better_ai.code import SKILL, dashboard  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = json.loads((Path(__file__).parent / "fixtures" / "code-better-examples.json").read_text())


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


def examples(kind):
    """The (title, record) pairs of one file kind on the spec page. The audit header is listed with the findings."""
    return [(e["title"], json.loads(e["line"])) for e in EXAMPLES[kind] if not e["title"].startswith("audit")]


def audit_header():
    (found,) = [
        json.loads(e["line"]) for e in EXAMPLES["audit/<date>/findings.jsonl"] if e["title"].startswith("audit")
    ]
    return found


class Examples(unittest.TestCase):
    """Every example of the spec page validates against the schema of its file kind."""

    def test_every_example_has_a_schema_that_accepts_it(self):
        for kind, (name, _) in KINDS.items():
            for title, record in examples(kind):
                with self.subTest(kind=kind, example=title):
                    self.assertEqual(check_record(record, [name]), [])
        with self.subTest(kind="audit.json"):
            self.assertEqual(check_record(audit_header(), [AUDIT[0]]), [])

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
                records = [mutate(good)] if kind in ("code.json", "logs/<agent>.card.json") else [good, mutate(good)]
                path = write(folder, relative, records, as_json=kind.endswith(".json"))
                errors = [e for e in schema.check_paths([path], docs=DOCS) if e.field.split(".")[0] == field]
                self.assertTrue(errors, f"{kind}: no error on {field} for {title}")
                self.assertEqual(errors[0].line, 1 if kind.endswith(".json") else 2)
                self.assertTrue(errors[0].file.endswith(relative))

    def test_the_audit_header(self):
        with tempfile.TemporaryDirectory() as d:
            record = {k: v for k, v in audit_header().items() if k != "goal"}
            path = write(Path(d), AUDIT[1], [record], as_json=True)
            self.assertEqual([e.field for e in schema.check_paths([path], docs=DOCS)], ["goal"])


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
            "default": None,
            "deadline": None,
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

    def test_a_task_points_to_the_changes_own_spec_not_the_architect_folders(self):
        design = {"type": "architect", "folder": "docs/designs/up/"}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".git").mkdir()
            write(root / "docs" / "designs" / "up", "spec.jsonl", [spec("S3")])
            folder = change(root, specs=[spec("S1")], design=design, tasks=[task("T1", requirements=["S3"])])
            self.assertIn("dangling", check(folder)[0].message)
            write(folder, "spec.jsonl", [spec("S1"), spec("S3")])
            self.assertEqual(check(folder), [])

    def test_the_copied_spec_resolves_its_sources_in_the_architect_folder(self):
        design = {"type": "architect", "folder": "docs/designs/up/"}
        decision = {"type": "decision", "at": AT, "by": "architect", "id": "D1"}
        source = {"type": "decision", "decision": "D1"}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".git").mkdir()
            folder = change(root, specs=[spec("S1", source=source)], design=design)
            self.assertIn("dangling", check(folder)[0].message)
            write(root / "docs" / "designs" / "up", "decisions.jsonl", [decision])
            self.assertEqual(check(folder), [])
            # the change's own decisions.jsonl never answers a design pointer
            (root / "docs" / "designs" / "up" / "decisions.jsonl").unlink()
            own = {**decision, "raised_by": "coordinator", "about": {"type": "change"}, "asked": "Which?"}
            write(folder, "decisions.jsonl", [{**own, "status": "decided", "decision": "A"}])
            self.assertEqual(
                [e.message for e in check(folder)], ["dangling: docs/designs/up/decisions.jsonl does not exist"]
            )


class Dashboard(unittest.TestCase):
    def test_the_page_is_named_by_the_goal_of_code_json_else_by_the_folder(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            self.assertEqual(load(folder)["name"], "Uploads fail loudly")
            write(folder, "code.json", [{**code(), "goal": "  Export invoices as CSV  \nand more"}], as_json=True)
            self.assertEqual(load(folder)["name"], "Export invoices as CSV")
            write(folder, "code.json", [{**code(), "mode": "nonsense"}], as_json=True)  # invalid
            self.assertEqual(load(folder)["name"], "c")
            (folder / "code.json").write_text("{not json", encoding="utf-8")
            self.assertEqual(load(folder)["name"], "c")

    def test_a_folder_with_one_bad_task_still_shows_every_other_task(self):
        with tempfile.TemporaryDirectory() as d:
            tasks = [task("T1"), task("T2", status="in review"), task("T3", status="built")]
            folder = change(Path(d), tasks=tasks)
            data = load(folder)
        # the bad task stays on the page, marked, so the page can show its status as written
        self.assertEqual([t["id"] for t in data["tasks"]], ["T1", "T2", "T3"])
        self.assertEqual([bool(t.get("_errors")) for t in data["tasks"]], [False, True, False])
        (error,) = data["errors"]  # one error: the enum, not also the mode set
        self.assertEqual(
            (error["file"], error["line"], error["field"], error["by"]), ("tasks.jsonl", 2, "status", "coordinator")
        )
        self.assertIn("must be one of", error["message"])
        self.assertEqual(data["tasks"][1]["_errors"], [f"{error['field']}: {error['message']}"])

    def test_an_invalid_lessons_file_is_listed_by_load_and_by_check(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            write(folder, "lessons.jsonl", [{"type": "lesson", "at": AT, "by": "coordinator", "id": "L1"}])
            errors = load(folder)["errors"]
            self.assertTrue(errors)
            self.assertEqual({e["file"] for e in errors}, {"lessons.jsonl"})
            done = call("code-better", "check", folder, cwd=d)
        self.assertEqual(done.returncode, 1)
        self.assertIn("lessons.jsonl", done.stdout)

    def test_an_unparsed_line_is_an_error_without_an_author(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            with (folder / "tasks.jsonl").open("a") as f:
                f.write("{not json\n")
            data = load(folder)
        self.assertEqual([t["id"] for t in data["tasks"]], ["T1"])
        self.assertEqual([(e["file"], e["line"]) for e in data["errors"]], [("tasks.jsonl", 2)])
        self.assertNotIn("by", data["errors"][0])

    def test_a_line_nested_50000_deep_is_an_error_and_the_other_tasks_still_show(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            with (folder / "tasks.jsonl").open("a") as f:
                f.write('{"type": "task", "x": ' + "[" * 50000 + "]" * 50000 + "}\n")
            data = load(folder)
        self.assertEqual([t["id"] for t in data["tasks"]][:1], ["T1"])
        self.assertTrue(any(e["line"] == 2 for e in data["errors"]))

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
            data = load(folder)
        self.assertEqual(data["errors"], [])
        self.assertEqual(data["name"], "Uploads fail loudly")
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
            (decisions["D1"]["status"], decisions["D1"]["answer"], decisions["D1"]["raised_by"]),
            ("answered", {"type": "chat", "text": "50 MB"}, "b1"),
        )
        self.assertEqual((decisions["D1"]["task"], decisions["D2"]["status"]), ("T2", "waiting"))

    def test_a_decision_answered_on_the_page_points_to_the_event_that_holds_the_text(self):
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
            data = load(folder)
        self.assertEqual(data["errors"], [])
        self.assertEqual(data["decisions"][0]["answer"], {"type": "page", "event": "a-1"})
        self.assertEqual([e["text"] for e in data["conversation"] if e["id"] == "a-1"], ["Business days."])

    def test_a_task_pointing_at_a_missing_spec_record_is_listed_as_dangling(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d), tasks=[task("T1"), task("T2", requirements=["S4"])])
            data = load(folder)
        self.assertEqual([t["id"] for t in data["tasks"]], ["T1", "T2"])
        self.assertIn("dangling", data["errors"][0]["message"])
        self.assertEqual(data["errors"][0]["field"], "requirements[0]")

    def test_requirements_come_from_the_changes_own_spec_even_when_it_names_an_architect_folder(self):
        design = {"type": "architect", "folder": "docs/designs/up/"}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".git").mkdir()
            write(root / "docs" / "designs" / "up", "spec.jsonl", [spec("S3", "Only in the design folder.")])
            folder = change(
                root,
                specs=[spec("S3", "The page shall show errors.")],
                design=design,
                tasks=[task("T1", requirements=["S3"])],
            )
            data = load(folder)
        self.assertEqual(data["errors"], [])
        self.assertEqual(data["requirements"], {"S3": "The page shall show errors."})

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
            data = load(folder)
        self.assertEqual(
            ([t["id"] for t in data["tasks"]], data["decisions"], data["agents"], data["errors"]), (["T1"], [], [], [])
        )

    def test_a_change_with_only_its_head_loads_without_error(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / ".code" / "c"
            write(folder, "code.json", [code()], as_json=True)
            data = load(folder)
        self.assertEqual((data["tasks"], data["agents"], data["decisions"], data["errors"]), ([], [], [], []))

    def test_verified_without_a_passing_verifier_is_listed(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d), tasks=[task("T1", status="verified")])
            data = load(folder)
        self.assertEqual([t["id"] for t in data["tasks"]], ["T1"])
        self.assertIn("verifier", data["tasks"][0]["_errors"][0])
        self.assertIn("verifier", data["errors"][0]["message"])

    def test_a_coordinate_task_with_status_done_is_listed(self):
        with tempfile.TemporaryDirectory() as d:
            data = load(change(Path(d), tasks=[task("T1", status="done")]))
        self.assertEqual([(e["file"], e["field"]) for e in data["errors"]], [("tasks.jsonl", "status")])
        self.assertEqual([t["id"] for t in data["tasks"]], ["T1"])

    def test_a_broken_code_json_does_not_empty_the_task_list(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d), tasks=[task("T1"), task("T2", status="built")])
            (folder / "code.json").write_text("{broken")
            data = load(folder)
        self.assertEqual([t["id"] for t in data["tasks"]], ["T1", "T2"])
        messages = [e["message"] for e in data["errors"]]
        self.assertTrue(any("not valid JSON" in m for m in messages), messages)
        self.assertTrue(any("does not exist or is not valid JSON" in m for m in messages), messages)

    def test_a_waiting_decision_with_a_bad_task_pointer_stays_so_the_user_can_answer_it(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            bad = {
                "type": "decision",
                "at": AT,
                "by": "coordinator",
                "id": "D1",
                "raised_by": "b1",
                "about": {"type": "task", "task": "T9"},
                "asked": "Which limit?",
                "status": "waiting",
            }
            write(folder, "decisions.jsonl", [bad])
            data = load(folder)
        self.assertEqual(
            [(x["id"], x["status"], x["asked"]) for x in data["decisions"]], [("D1", "waiting", "Which limit?")]
        )
        self.assertTrue(data["decisions"][0]["_errors"])
        self.assertIn("dangling", data["errors"][0]["message"])

    def test_a_decision_missing_fields_still_shows(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            write(
                folder,
                "decisions.jsonl",
                [{"type": "decision", "at": AT, "by": "coordinator", "id": "D1", "status": "waiting"}],
            )
            data = load(folder)
        self.assertEqual([x["id"] for x in data["decisions"]], ["D1"])
        self.assertTrue(data["errors"])

    def test_a_line_written_after_the_read_is_not_shown_unchecked(self):
        """One read: the text that is validated is the text that is shown, so a line added between is in neither."""
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            real = dashboard.schema.check_text

            def late(path, text, docs, cache=None, **options):
                if path.name == "tasks.jsonl":
                    with path.open("a") as f:
                        f.write(json.dumps(task("T2", status="in review")) + "\n")
                return real(path, text, docs, cache, **options)

            dashboard.schema.check_text = late
            try:
                data = load(folder)
            finally:
                dashboard.schema.check_text = real
        self.assertEqual([t["id"] for t in data["tasks"]], ["T1"])
        self.assertEqual(data["errors"], [])

    def test_a_bug_in_the_loader_is_not_a_record_error(self):
        """Only a file that cannot be read or parsed becomes an entry; anything else reaches the page's bug path."""
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            with (
                mock.patch.object(dashboard.Reader, "records", side_effect=KeyError("bug")),
                self.assertRaises(KeyError),
            ):
                load(folder)

    def test_the_audit_folder_is_not_the_changes(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            write(folder, "audit/2026-11-21/findings.jsonl", [{"type": "finding"}])
            self.assertEqual(load(folder)["errors"], [])


RAW_LINES = wrong_types.RAW_LINES


class WrongTypes(unittest.TestCase):
    """For every field of every record the dashboard reads, each wrong type, one at a time: `check` and `load` do not
    fail, and the page draws what it gets. A record that is not valid is shown without the fields that failed."""

    def files(self):
        gap = {
            "type": "gap",
            "at": AT,
            "by": "coordinator",
            "id": "G1",
            "text": "t",
            "status": "asked",
            "decision": "D1",
        }
        gap["if_wrong"] = "x"
        decision = {"type": "decision", "at": AT, "by": "coordinator", "raised_by": "b1", "asked": "Which?"}
        decision |= {"about": {"type": "task", "task": "T1"}}
        answered = {**decision, "id": "D1", "status": "answered", "answer": {"type": "page", "event": "a-1"}}
        chat = {**decision, "id": "D2", "status": "answered", "answer": {"type": "chat", "text": "50 MB"}}
        decided = {**decision, "id": "D4", "status": "decided", "decision": "Yes"}
        waiting = {**decision, "id": "D3", "status": "waiting"}
        event = {"type": "answer", "at": AT, "by": "user", "id": "a-1", "decision": "D1", "text": "A", "default": False}
        return {
            "code.json": ([code("coordinate", {"type": "file", "path": "d.md"})], True),
            "spec.jsonl": ([spec("S1"), gap], False),
            "tasks.jsonl": (
                [task("T1", status="building"), task("T2", status="blocked", reason="task", waits_on="T1")],
                False,
            ),
            "decisions.jsonl": ([answered, chat, waiting, decided], False),
            "conversation.jsonl": ([event], False),
            "logs/b1.card.json": ([card("builder", "T1")], True),
            "logs/b1.jsonl": ([log("start", "b1"), log("handed_back", "b1", result="done")], False),
        }

    def test_no_wrong_type_breaks_check_load_or_the_page(self):
        base = self.files()
        files = {name: records for name, (records, _) in base.items()}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".git").mkdir()
            folder = root / ".code" / "c"

            def put(name, records):
                write(folder, name, records, base[name][1])

            for name, records in files.items():
                put(name, records)
            unit = paths.resolve_unit(str(folder), SKILL)  # once: the folder stays where it is

            def survives(label):
                data = load(folder, unit)
                json.dumps(data, allow_nan=False)
                for error in schema.check_paths([folder], docs=DOCS):  # `check` does not raise either
                    str(error)
                return data

            # What git says of a branch does not depend on the card's types: only the card's own fields are fuzzed here.
            with (
                mock.patch.object(dashboard.activity, "worktrees", return_value={}),
                mock.patch.object(dashboard.activity, "branch_activity", return_value=None),
            ):
                payloads, total = wrong_types.fuzz(self, files, put, survives)
                pairs = [(name, raw) for name in files for raw in RAW_LINES]
                picked = sweep.cases(pairs, key=lambda pair: pair[1])  # each raw line once, across the files
                total += len(pairs)
                for name, raw in picked:
                    with self.subTest(f"{name}: raw {raw[:10]}"):
                        path = folder / name
                        path.write_text(raw + "\n" + ("" if base[name][1] else path.read_text()), encoding="utf-8")
                        payloads.append({"label": f"{name}: raw {raw[:10]}", "data": survives(raw)})
                        put(name, files[name])
            self.assertGreater(total, 1000)
        wrong_types.render("render-payloads.js", payloads, self)

    def test_an_invalid_record_shows_without_the_fields_that_failed(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d), tasks=[{**task("T1"), "id": ["T1"], "requirements": "S1", "mode": 5}, task("T2")])
            data = load(folder)
        first, second = data["tasks"]
        self.assertEqual(first["id"], "(line 1)")
        self.assertNotIn("requirements", first)
        self.assertNotIn("mode", first)
        self.assertEqual(first["task"], "Reject empty uploads")
        self.assertTrue(first["_errors"])
        self.assertEqual(second["id"], "T2")
        self.assertEqual({e["field"] for e in data["errors"]}, {"id", "requirements", "mode"})

    def test_a_status_that_failed_stays_as_written_text(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d), tasks=[task("T1", status="in review"), {**task("T2"), "status": ["x"]}])
            data = load(folder)
        self.assertEqual(data["tasks"][0]["status"], "in review")
        self.assertNotIn("status", data["tasks"][1])


class BaseFieldsOfEveryKind(unittest.TestCase):
    """Every kind of file starts with type, at and by, `at` is UTC with a Z, and `id` is there exactly where the spec
    page puts one (verifier of the file-format scripts: R8 held for the kinds first tried, not for all)."""

    def kinds(self):
        for kind, (name, _) in KINDS.items():
            for title, record in examples(kind):
                yield f"{kind}: {title}", name, record
        yield "audit header", AUDIT[0], audit_header()

    def problems(self, name, record):
        return check_record(record, [name])

    def test_a_record_without_type_at_or_by_is_refused(self):
        for label, name, record in self.kinds():
            for field in ("type", "at", "by"):
                with self.subTest(label, missing=field):
                    changed = {k: v for k, v in record.items() if k != field}
                    self.assertTrue(self.problems(name, changed))

    def test_at_must_be_utc_with_a_z(self):
        for label, name, record in self.kinds():
            for at in ("2026-11-21T10:00:00", "2026-11-21T10:00:00+01:00", "yesterday", 5):
                with self.subTest(label, at=at):
                    self.assertTrue(self.problems(name, {**record, "at": at}))

    def test_id_is_required_where_the_page_marks_one_and_refused_where_it_does_not(self):
        for label, name, record in self.kinds():
            with self.subTest(label):
                if "id" in record:
                    self.assertTrue(self.problems(name, {k: v for k, v in record.items() if k != "id"}))
                else:
                    self.assertTrue(self.problems(name, {**record, "id": "X1"}))


class LoneSurrogates(unittest.TestCase):
    """A lone surrogate (JSON `\\ud800`) in any string or key of any record of any kind: `check` and `load` do not fail,
    and what they answer can be printed and sent as UTF-8."""

    @staticmethod
    def places(value):
        """Each string value and each key of a JSON value, as (kind, path to the object holding it, its key or index)."""
        found, pending = [], [(value, ())]
        while pending:
            item, path = pending.pop()
            if isinstance(item, dict):
                for key, child in item.items():
                    found.append(("key", path, key))
                    pending.append((child, (*path, key)))
            elif isinstance(item, list):
                pending.extend((child, (*path, i)) for i, child in enumerate(item))
            elif isinstance(item, str) and path:
                found.append(("value", path[:-1], path[-1]))
        return found

    @staticmethod
    def with_a_surrogate(record, place):
        record = json.loads(json.dumps(record))
        kind, path, key = place
        holder = record
        for step in path:
            holder = holder[step]
        if kind == "value":
            holder[key] = "\ud800"
        else:
            renamed = {(key + "\ud800" if k == key else k): v for k, v in holder.items()}
            holder.clear()
            holder.update(renamed)
        return record

    def cases(self):
        for kind, (_, relative) in KINDS.items():
            for title, record in examples(kind):
                yield f"{kind}: {title}", relative, record
        yield "audit header", AUDIT[1], audit_header()

    def test_every_string_and_key_of_every_example(self):
        every = [
            (label, relative, record, place)
            for label, relative, record in self.cases()
            if not relative.startswith("audit/")  # an audit is not shown by the dashboard; `check` reads it below
            for place in self.places(record)
        ]
        for label, relative, record, place in sweep.cases(every, key=[lambda e: e[0], lambda e: e[3][0]]):
            with self.subTest(label, place=place[1:]), tempfile.TemporaryDirectory() as d:
                folder = change(Path(d))
                changed = self.with_a_surrogate(record, place)
                write(folder, relative, [changed], relative.endswith(".json"))
                for error in schema.check_paths([folder], docs=DOCS):
                    str(error).encode("utf-8", "backslashreplace")
                    self.assertTrue(error.message.isprintable() or "\n" in error.message)
                json.dumps(load(folder), ensure_ascii=False, allow_nan=False).encode("utf-8")

    def test_check_names_the_surrogate_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            write(folder, "tasks.jsonl", [task("T1", task="a\ud800b")])
            done = call("code-better", "check", folder, cwd=d)
        self.assertEqual(done.returncode, 1, done.stderr)
        self.assertNotIn("Traceback", done.stderr)
        self.assertRegex(done.stdout, r"non-text|ud800")


class OneBadRecordKeepsTheRest(unittest.TestCase):
    """What the verifiers found by loading a folder with one bad record in it (each used to hide something)."""

    def test_a_pretty_printed_card_with_a_bad_role_is_listed_and_the_other_agents_stay(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d), tasks=[task("T1", status="building")])
            write(folder, "logs/b2.card.json", [card("builder", "T1")], as_json=True)
            (folder / "logs" / "b1.card.json").write_text(
                json.dumps({**card("builder", "T1"), "role": "boss"}, indent=2), encoding="utf-8"
            )
            data = load(folder)
        self.assertIn(("logs/b1.card.json", "role"), [(e["file"], e["field"]) for e in data["errors"]])
        self.assertEqual([t["id"] for t in data["tasks"]], ["T1"])
        self.assertIn("b2", [a["name"] for a in data["agents"]])

    def test_a_code_json_with_an_unknown_mode_does_not_hide_the_tasks(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d), tasks=[task("T1", status="building")])
            write(folder, "code.json", [{**code(), "mode": "weird"}], as_json=True)
            data = load(folder)
        self.assertEqual([t["id"] for t in data["tasks"]], ["T1"])
        self.assertIn("mode", [e["field"] for e in data["errors"] if e["file"] == "code.json"])

    def test_every_status_of_a_task_with_a_requirement_nobody_wrote_still_lists_the_task(self):
        with tempfile.TemporaryDirectory() as d:
            tasks = [
                task("T1", status="merged"),
                task("T2", status="in review"),
                task("T3", status="verified"),
                task("T4", status="blocked", reason="task", waits_on="T2"),
                task("T5", requirements=["S9"]),
            ]
            data = load(change(Path(d), tasks=tasks))
        self.assertEqual([t["id"] for t in data["tasks"]], ["T1", "T2", "T3", "T4", "T5"])
        self.assertTrue(data["errors"])


GOOD_LESSON = {
    "type": "lesson",
    "at": AT,
    "by": "coordinator",
    "id": "L1",
    "class": "c",
    "rule": "r",
    "found_in": [{"task": "T1", "finding": "f"}],
}


class LessonsWrongTypes(unittest.TestCase):
    """Every field of lessons.jsonl given each wrong value, raw lines, NaN, 50,000-deep nesting and bad UTF-8: `load`
    lists the file's errors and nothing else, `check` exits 1 without a traceback, and the page draws the payload."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.folder = change(Path(cls.tmp.name))
        cls.unit = paths.resolve_unit(str(cls.folder), SKILL)  # once: every case rewrites the one file

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_all(self, text):
        """(load result, lessons errors, exit code of check, its output) for a lessons.jsonl holding `text`, str or bytes."""
        (self.folder / "lessons.jsonl").write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))
        data = load(self.folder, self.unit)
        json.dumps(data, allow_nan=False)
        done = call("code-better", "check", self.folder, cwd=self.tmp.name)
        self.assertNotEqual(done.returncode, 5, done.stderr)
        self.assertNotIn("Traceback", done.stderr)
        lessons = [(e["line"], e["field"]) for e in data["errors"] if e["file"] == "lessons.jsonl"]
        self.assertEqual([e for e in data["errors"] if e["file"] != "lessons.jsonl"], [])
        return data, lessons, done.returncode, done.stdout

    def test_a_valid_lesson_is_clean(self):
        _, lessons, code_, out = self.run_all(json.dumps(GOOD_LESSON) + "\n")
        self.assertEqual((lessons, code_, out), ([], 0, ""))

    def test_each_text_field_with_a_value_that_is_not_text_is_one_error_on_that_field(self):
        for field in ("type", "at", "by", "id", "class", "rule"):
            for bad in (None, 0, 1.5, True, [], {}, [None], {"a": 1}):
                with self.subTest(field=field, bad=bad):
                    _, lessons, code_, out = self.run_all(json.dumps({**GOOD_LESSON, field: bad}) + "\n")
                    self.assertIn(field, [f.split(".")[0] for _, f in lessons])
                    self.assertEqual(code_, 1)
                    self.assertIn("lessons.jsonl:1", out)

    def test_found_in_with_a_wrong_item_or_a_wrong_task_is_an_error(self):
        for found in ([None], [0], [[]], [{}], [{"task": None, "finding": "f"}], [{"task": 1, "finding": 2}], "x", 5):
            with self.subTest(found=found):
                _, lessons, code_, _ = self.run_all(json.dumps({**GOOD_LESSON, "found_in": found}) + "\n")
                self.assertTrue(lessons)
                self.assertEqual(code_, 1)

    def test_a_task_that_is_not_in_tasks_jsonl_and_an_extra_field_are_errors(self):
        for record in (
            {**GOOD_LESSON, "found_in": [{"task": "T99", "finding": "f"}]},
            {**GOOD_LESSON, "extra": 1},
            {**GOOD_LESSON, "found_in": [{"task": "T1", "finding": "f", "x": {"y": [1]}}]},
        ):
            with self.subTest(record=record):
                _, lessons, code_, _ = self.run_all(json.dumps(record) + "\n")
                self.assertTrue(lessons)
                self.assertEqual(code_, 1)

    def test_a_field_left_out_is_an_error(self):
        for field in GOOD_LESSON:
            with self.subTest(field):
                record = {k: v for k, v in GOOD_LESSON.items() if k != field}
                _, lessons, _, _ = self.run_all(json.dumps(record) + "\n")
                self.assertEqual([f for _, f in lessons], [field])

    def test_the_same_id_twice_is_an_error_on_the_second_line(self):
        _, lessons, _, _ = self.run_all((json.dumps(GOOD_LESSON) + "\n") * 2)
        self.assertEqual([line for line, _ in lessons], [2])

    def test_lines_that_are_not_records_and_values_that_are_not_json_are_errors(self):
        deep_list = "[" * 50000 + "]" * 50000
        deep_object = '{"a":' * 50000 + "1" + "}" * 50000
        deep_field = json.dumps({**GOOD_LESSON, "class": 1})[:-1] + ',"x":' + deep_list + "}"
        raw = [
            *RAW_LINES[:-1],
            "[1,2]",
            "true",
            "not json at all",
            deep_list,
            deep_object,
            deep_field,
            '{"type":"lesson","at":NaN,"by":Infinity,"id":"L1","class":-Infinity,"rule":"r","found_in":[{"task":NaN,"finding":"f"}]}',
        ]
        for line in raw:
            with self.subTest(line=line[:30]):
                _, lessons, code_, out = self.run_all(line + "\n")
                self.assertTrue(lessons)
                self.assertEqual(code_, 1)
                self.assertIn("lessons.jsonl", out)

    def test_bytes_that_are_not_utf8_are_an_error_not_a_traceback(self):
        _, lessons, code_, _ = self.run_all(b'{"type":"lesson","by":"\xff\xfe"}\n')
        self.assertTrue(lessons)
        self.assertEqual(code_, 1)

    def test_every_payload_is_drawn_by_the_page(self):
        def put(name, records):
            (self.folder / name).write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")

        def survives(label):
            return self.run_all((self.folder / "lessons.jsonl").read_bytes())[0]

        payloads, total = wrong_types.fuzz(self, {"lessons.jsonl": [GOOD_LESSON]}, put, survives)
        self.assertGreater(total, 100)
        wrong_types.render("render-payloads.js", payloads, self)


class Check(unittest.TestCase):
    def run_check(self, folder, run=call):
        return run("code-better", "check", folder, cwd=folder.parent.parent.parent)

    def test_check_exits_one_on_a_bad_folder_and_zero_on_a_good_one(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            good = self.run_check(folder, better)  # the one run of `check` in its own process
            self.assertEqual((good.returncode, good.stdout), (0, ""))
            with (folder / "tasks.jsonl").open("a") as f:
                f.write(json.dumps(task("T2", status="in review")) + "\n")
            bad = self.run_check(folder)
            self.assertEqual(bad.returncode, 1)
            lines = bad.stdout.strip().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertRegex(lines[0], r"tasks\.jsonl:2: status: must be one of")
            data = load(folder)
            self.assertEqual(
                [line.split("/")[-1] for line in lines],
                [f"{e['file']}:{e['line']}: {e['field']}: {e['message']}" for e in data["errors"]],
            )

    def test_check_reads_the_files_the_page_does_not_show(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            write(folder, "next-steps.jsonl", [{"type": "step", "at": AT, "by": "coordinator"}])
            self.assertEqual(self.run_check(folder).returncode, 1)


class Usage(unittest.TestCase):
    def test_a_note_on_the_dashboard_cannot_carry_an_on_field(self):
        note = {"type": "note", "at": AT, "by": "user", "id": "m-1", "text": "hi", "to": None}
        names = ["dashboard-events.schema.json"]
        self.assertEqual(check_record(note, names), [])
        problems = check_record({**note, "on": {"kind": "agent", "id": "b1", "title": "b1"}}, names)
        self.assertEqual([field for field, _ in problems], ["on"])


class NoOldFiles(unittest.TestCase):
    """No code-better instruction or module writes the old Markdown files."""

    def test_no_module_reads_or_writes_them(self):
        text = (ROOT / "src" / "better_ai" / "code" / "dashboard.py").read_text()
        for old in ("tasks.md", "specs.md", "decisions/", "logs/*.md", "read_tasks", "read_requirements", "read_entry"):
            self.assertNotIn(old, text)


if __name__ == "__main__":
    unittest.main()
