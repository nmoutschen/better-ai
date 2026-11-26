"""Tests for `create`, `add` and `set` in src/better_ai/records.py (T2 of the unified command).

The tests run the command in the process (`call`), with `BETTER_AI_SKILL` set and the unit given by its absolute path,
and a few of them as a real subprocess (`run`) where the exit code or the files on disk are the point.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

import sweep  # noqa: E402
from better import call as in_process  # noqa: E402
from better import run  # noqa: E402

from better_ai import architect, code, design, paths, records, research, schema, show  # noqa: E402

SKILLS = {
    "architect-better": architect.SKILL,
    "code-better": code.SKILL,
    "design-better": design.SKILL,
    "research-better": research.SKILL,
    "show-better": show.SKILL,
}
FIXTURES = HERE / "fixtures"
CODE_HEAD = {"goal": "g", "design": {"type": "request", "text": "t"}, "mode": "coordinate"}
BOARD_HEAD = {
    "topic": "why",
    "title": "Why",
    "short": "Why",
    "meaning": "...",
    "goal": "decide",
    "limit": None,
    "stop_at": "medium",
    "collections": ["web"],
    "missing": [],
    "changes": [],
    "status": "running",
}
DECISION = {
    "raised_by": "coordinator",
    "about": {"type": "change"},
    "asked": "which?",
    "status": "decided",
    "decision": "A",
}
WAITING = {
    "raised_by": "coordinator",
    "about": {"type": "change"},
    "asked": "which?",
    "status": "waiting",
    "default": "A",
    "deadline": None,
}
QUESTION = {
    "question": "Did the October form add a step before payment?",
    "title": "Did the form add steps",
    "priority": "high",
    "status": "open",
    "origin": {"type": "goal"},
    "kind": "seed",
    "stakes": "if it did, the drop is self-inflicted",
    "done_when": "release notes show the steps",
    "note": None,
}
TASK = {"task": "Reject empty uploads", "mode": "bug fix", "requirements": [], "check": "pytest", "status": "todo"}
CARD = {"role": "builder", "task": "T1", "branch": "fix/t1"}


def example(fixture, name, index=0):
    """The fields of an example record of the fixtures, without the ones the command stamps."""
    data = json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))[name][index]
    record = data["record"] if "record" in data else json.loads(data["line"])
    return {k: v for k, v in record.items() if k not in ("type", "at", "by", "id")}


def call(skill, *args, stdin="", env=None):
    """Run one command in this process: (exit code, stdout, stderr). A stdin that is not text is written as JSON."""
    done = in_process(skill, *args, stdin=stdin if isinstance(stdin, str) else json.dumps(stdin), env=env)
    return done.returncode, done.stdout, done.stderr


def jsonl(*records_):
    return "".join(json.dumps(r) + "\n" for r in records_)


def lines_of(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


class Repo(unittest.TestCase):
    """A scratch git repository; `unit(folder)` is an absolute unit path inside it."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(os.path.realpath(tmp.name)) / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)

    def unit(self, folder):
        return self.repo / folder

    def code_change(self, name="x"):
        unit = self.unit(f".code/{name}")
        done = call("code-better", "create", unit, "--by", "coordinator", stdin=CODE_HEAD)
        self.assertEqual(done[0], 0, done)
        return unit

    def task(self, unit):
        done = call("code-better", "add", unit, "task", "--by", "coordinator", stdin=TASK)
        self.assertEqual(done[:2], (0, "T1\n"), done)

    def architect(self, name="a"):
        unit = self.unit(f".architect/{name}")
        done = call(
            "architect-better",
            "create",
            unit,
            "--by",
            "architect",
            stdin=example("architect-better-examples.json", "architect.json"),
        )
        self.assertEqual(done[0], 0, done)
        return unit

    def board(self, name="b"):
        unit = self.unit(f".research/{name}")
        done = call("research-better", "create", unit, "--by", "coordinator", stdin=BOARD_HEAD)
        self.assertEqual(done[0], 0, done)
        return unit

    def exclude(self):
        path = self.repo / ".git" / "info" / "exclude"
        return path.read_text() if path.exists() else ""


def snapshot(folder):
    """Every file under `folder` (relative path -> bytes), skipping the .git folder."""
    found = {}
    for base, names, files in os.walk(folder):
        names[:] = [n for n in names if n != ".git"]
        for name in files:
            path = Path(base) / name
            found[str(path.relative_to(folder))] = path.read_bytes()
    return found


class Create(Repo):
    def test_s13_create_writes_a_stamped_head_and_the_folders_and_no_exclude_line(self):
        unit = self.code_change()
        head = json.loads((unit / "code.json").read_text())
        self.assertEqual((head["type"], head["by"]), ("code", "coordinator"))
        self.assertRegex(head["at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertTrue((unit / "logs").is_dir())
        self.assertNotIn(".code/", self.exclude().splitlines())
        self.assertEqual(call("code-better", "check", unit)[0], 0)

    def test_s13_every_skills_unit_can_be_created_with_its_folders(self):
        heads = {
            "research-better": (".research/b", BOARD_HEAD, ["questions", "claims", "sources", "logs"]),
            "code-better": (".code/c", CODE_HEAD, ["logs"]),
            "code-better-audit": (
                ".code/audit/2026-11-22",
                {"goal": "g", "commit": "abc", "not_read": None},
                [],
            ),
        }
        for name, (folder, head, folders) in heads.items():
            unit = self.unit(folder)
            skill = name.removesuffix("-audit")
            done = call(skill, "create", unit, "--by", "agent-1", stdin=head)
            self.assertEqual(done[0], 0, (name, done))
            for sub in folders:
                self.assertTrue((unit / sub).is_dir(), (name, sub))
        self.assertNotIn(".research/", self.exclude().splitlines())
        self.assertNotIn(".code/", self.exclude().splitlines())

    def test_s13_create_in_a_linked_worktree_writes_no_exclude_line(self):
        subprocess.run(
            [
                "git",
                "-C",
                self.repo,
                "-c",
                "user.name=t",
                "-c",
                "user.email=t@t",
                "commit",
                "-q",
                "--allow-empty",
                "-m",
                "x",
            ],
            check=True,
        )
        linked = self.repo.parent / "linked"
        subprocess.run(["git", "-C", self.repo, "worktree", "add", "-q", str(linked)], check=True)
        done = call("code-better", "create", linked / ".code" / "w", "--by", "coordinator", stdin=CODE_HEAD)
        self.assertEqual(done[0], 0, done)
        self.assertNotIn(".code/", self.exclude().splitlines())

    def test_s14_outside_a_repository_create_works_and_says_nothing_about_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            unit = Path(os.path.realpath(tmp)) / ".code" / "x"
            done = call("code-better", "create", unit, "--by", "coordinator", stdin=CODE_HEAD)
        self.assertEqual(done[0], 0, done)
        self.assertNotIn("git", done[1])

    def test_s2_an_invalid_head_leaves_no_folder_head_or_exclude_line(self):
        unit = self.unit(".code/bad")
        done = call("code-better", "create", unit, "--by", "coordinator", stdin={"goal": "g"})
        self.assertEqual(done[0], 1)
        self.assertIn(":new: ", done[1])
        self.assertFalse(unit.exists())
        self.assertEqual(self.exclude().count(".code/"), 0)

    def test_s3_create_refuses_the_fields_the_command_sets(self):
        for field_ in ("at", "by", "id"):
            done = call("code-better", "create", self.unit(".code/z"), "--by", "c", stdin={**CODE_HEAD, field_: "x"})
            self.assertEqual(done[0], 1, field_)
            self.assertIn(repr(field_), done[2])
        self.assertFalse(self.unit(".code/z").exists())

    def test_d8_create_adds_the_head_to_an_existing_folder_without_touching_its_files(self):
        unit = self.unit(".code/doc")
        unit.mkdir(parents=True)
        (unit / "notes.md").write_text("mine")
        (unit / "logs").mkdir()
        (unit / "logs" / "a.txt").write_text("keep")
        done = call("code-better", "create", unit, "--by", "coordinator", stdin=CODE_HEAD)
        self.assertEqual(done[0], 0, done)
        self.assertEqual((unit / "notes.md").read_text(), "mine")
        self.assertEqual((unit / "logs" / "a.txt").read_text(), "keep")
        self.assertTrue((unit / "code.json").is_file())

    def test_d8_create_refuses_a_folder_that_holds_a_head_file_of_any_skill(self):
        unit = self.code_change()
        again = call("code-better", "create", unit, "--by", "coordinator", stdin=CODE_HEAD)
        self.assertEqual(again[0], 1)
        self.assertIn("already holds a unit (code.json)", again[2])
        self.assertIn("set ", again[2])
        other = self.unit(".code/other")
        other.mkdir(parents=True)
        (other / "brief.json").write_text("{}")
        done = call("code-better", "create", other, "--by", "coordinator", stdin=CODE_HEAD)
        self.assertEqual(done[0], 1)
        self.assertFalse((other / "code.json").exists())

    def test_s63_create_refuses_stdin_that_is_not_a_json_object(self):
        for text in ("not json", "[1]", '"a"', "3"):
            done = call("code-better", "create", self.unit(".code/n"), "--by", "coordinator", stdin=text)
            self.assertEqual(done[0], 1, text)
            self.assertFalse(self.unit(".code/n").exists())

    def test_create_refuses_a_bad_by_and_the_page_name(self):
        for by in ("user", "Bad Name", "../x"):
            done = call("code-better", "create", self.unit(".code/n"), "--by", by, stdin=CODE_HEAD)
            self.assertEqual(done[0], 1, by)

    def test_d7_a_stdin_type_must_equal_the_head_type(self):
        done = call("code-better", "create", self.unit(".code/t"), "--by", "c", stdin={**CODE_HEAD, "type": "audit"})
        self.assertEqual(done[0], 1)
        self.assertIn("'audit'", done[2])
        self.assertIn("'code'", done[2])
        done = call("code-better", "create", self.unit(".code/t"), "--by", "c", stdin={**CODE_HEAD, "type": "code"})
        self.assertEqual(done[0], 0, done)

    def test_a_create_step_runs_after_validation_and_may_refuse_before_anything_is_written(self):
        seen = []

        def refuse(ctx):
            seen.append(ctx.record["type"])
            raise paths.refusal(ctx.unit.label, "no", "stop")

        with mock.patch.dict(records.CREATE_STEPS, {"code-better": [refuse]}):
            done = call("code-better", "create", self.unit(".code/s"), "--by", "c", stdin=CODE_HEAD)
        self.assertEqual((done[0], seen), (1, ["code"]))
        self.assertFalse(self.unit(".code/s").exists())
        wrote = []

        def copy(ctx):
            return lambda: wrote.append(sorted(p.name for p in ctx.unit.path.iterdir()))

        with mock.patch.dict(records.CREATE_STEPS, {"code-better": [copy]}):
            done = call("code-better", "create", self.unit(".code/s"), "--by", "c", stdin=CODE_HEAD)
        self.assertEqual(done[0], 0, done)
        self.assertEqual(wrote, [["code.json", "logs"]])

    def test_an_existing_step_can_deal_with_a_unit_that_already_has_its_head(self):
        unit = self.code_change()

        def top_up(ctx):
            ctx.run.out("topped up")
            return True

        with mock.patch.dict(records.EXISTING_STEPS, {"code-better": [top_up]}):
            done = call("code-better", "create", unit, "--by", "coordinator", stdin=CODE_HEAD)
        self.assertEqual((done[0], done[1]), (0, "topped up\n"))


class Add(Repo):
    def test_s1_add_stamps_type_at_by_and_the_id_and_prints_the_id(self):
        unit = self.code_change()
        done = call("code-better", "add", unit, "decision", "--by", "coordinator", stdin=DECISION)
        self.assertEqual((done[0], done[1]), (0, "D1\n"), done)
        (line,) = lines_of(unit / "decisions.jsonl")
        self.assertEqual((line["type"], line["id"], line["by"]), ("decision", "D1", "coordinator"))
        self.assertTrue(line["at"].endswith("Z"))
        self.assertEqual(list(line)[:4], ["type", "at", "by", "id"])
        self.assertEqual(call("code-better", "check", unit)[0], 0)

    def test_s1_add_works_in_a_unit_of_each_skill(self):
        board = self.board()
        done = call("research-better", "add", board, "decision", "--by", "coordinator", stdin=DECISION)
        self.assertEqual(done[:2], (0, "D1\n"), done)
        call("research-better", "add", board, "question", "--by", "w1", stdin=QUESTION)
        search = {"query": "q", "question": "Q-w1-1", "new_terms": []}
        done = call("research-better", "add", board, "search", "--for", "w1", stdin=search)
        self.assertEqual(done[0], 0, done)
        self.assertEqual(lines_of(board / "logs" / "w1.jsonl")[0]["by"], "w1")

    def test_s4_the_next_id_is_the_highest_plus_one_per_prefix_and_per_agent(self):
        unit = self.code_change()
        for expected in ("D1", "D2", "D3", "D4"):
            done = call("code-better", "add", unit, "decision", "--by", "coordinator", stdin=DECISION)
            self.assertEqual(done[1].strip(), expected)
        # a gap does not matter: the highest number counts
        text = (unit / "decisions.jsonl").read_text().replace('"D2"', '"D7"')
        (unit / "decisions.jsonl").write_text(text)
        self.assertEqual(call("code-better", "add", unit, "decision", "--by", "c", stdin=DECISION)[1].strip(), "D8")
        board = self.board()
        for agent, expected in (("ana", "Q-ana-1"), ("ana", "Q-ana-2"), ("bob", "Q-bob-1"), ("ana", "Q-ana-3")):
            done = call("research-better", "add", board, "question", "--by", agent, stdin=QUESTION)
            self.assertEqual((done[0], done[1].strip()), (0, expected), done)

    def test_s4_a_prefix_that_depends_on_a_field_gives_the_requirement_prefix_of_its_kind(self):
        unit = self.architect()
        base = example("architect-better-examples.json", "requirements.jsonl")
        base.pop("kind")
        base["source"] = {"type": "request", "sentence": "Add a dashboard"}
        got = {}
        for kind in ("quality", "functional", "constraint", "quality"):
            done = call(
                "architect-better", "add", unit, "requirement", "--by", "architect", stdin={**base, "kind": kind}
            )
            got.setdefault(kind, []).append(done[1].strip())
        self.assertEqual(got, {"quality": ["Q1", "Q2"], "functional": ["F1"], "constraint": ["C1"]})
        done = call("architect-better", "add", unit, "requirement", "--by", "architect", stdin={**base, "kind": "nope"})
        self.assertEqual(done[0], 1)
        self.assertIn("kind", done[1])

    def test_s5_a_line_that_does_not_parse_blocks_the_id_but_not_a_record_without_one(self):
        unit = self.code_change()
        call("code-better", "add", unit, "decision", "--by", "c", stdin=DECISION)
        with open(unit / "decisions.jsonl", "a") as file:
            file.write("{broken\n")
        before = (unit / "decisions.jsonl").read_bytes()
        done = call("code-better", "add", unit, "decision", "--by", "c", stdin=DECISION)
        self.assertEqual(done[0], 1)
        self.assertIn("line 2 does not parse", done[2])
        self.assertEqual((unit / "decisions.jsonl").read_bytes(), before)
        (unit / "progress.jsonl").write_text("{broken\n")
        done = call(
            "code-better", "add", unit, "progress", "--by", "c", stdin={"about": {"type": "change"}, "text": "t"}
        )
        self.assertEqual(done[0], 0, done)

    def test_s3_add_refuses_a_record_that_holds_at_by_or_id_naming_the_field(self):
        unit = self.code_change()
        for field_ in ("at", "by", "id"):
            done = call("code-better", "add", unit, "decision", "--by", "c", stdin={**DECISION, field_: "x"})
            self.assertEqual(done[0], 1, field_)
            self.assertIn(repr(field_), done[2])
        self.assertFalse((unit / "decisions.jsonl").exists())

    def test_d7_a_stdin_type_is_accepted_only_when_it_equals_the_positional_type(self):
        unit = self.code_change()
        done = call("code-better", "add", unit, "decision", "--by", "c", stdin={**DECISION, "type": "decision"})
        self.assertEqual(done[:2], (0, "D1\n"))
        done = call("code-better", "add", unit, "decision", "--by", "c", stdin={**DECISION, "type": "task"})
        self.assertEqual(done[0], 1)
        self.assertIn("'task'", done[2])
        self.assertIn("'decision'", done[2])

    def test_s2_an_invalid_record_writes_nothing_and_prints_one_line_per_error(self):
        unit = self.code_change()
        self.task(unit)
        call("code-better", "add", unit, "decision", "--by", "c", stdin=DECISION)
        before = snapshot(unit)
        for bad in (
            {**DECISION, "status": "bogus"},  # invalid status
            {k: v for k, v in DECISION.items() if k != "asked"},  # missing required
            {**DECISION, "about": {"type": "task", "task": "T9"}},  # dangling pointer
        ):
            done = call("code-better", "add", unit, "decision", "--by", "c", stdin=bad)
            self.assertEqual(done[0], 1, bad)
            self.assertRegex(done[1], r"decisions\.jsonl:new: \S+: ")
            self.assertEqual(snapshot(unit), before)
        pointer = call(
            "code-better",
            "add",
            unit,
            "decision",
            "--by",
            "c",
            stdin={**DECISION, "about": {"type": "task", "task": "T9"}},
        )
        self.assertIn("T9", pointer[1])

    def test_s32_unknown_fields_wrong_tags_and_unknown_types_say_what_is_allowed(self):
        unit = self.code_change()
        done = call("code-better", "add", unit, "decision", "--by", "c", stdin={**DECISION, "nope": 1})
        self.assertEqual(done[0], 1)
        self.assertIn("nope", done[1])
        self.assertIn("raised_by", done[1])  # the allowed fields are named
        done = call("code-better", "add", unit, "decision", "--by", "c", stdin={**DECISION, "about": {"type": "x"}})
        self.assertEqual(done[0], 1)
        self.assertIn("task", done[1])
        done = call("code-better", "add", unit, "nope", "--by", "c", stdin={})
        self.assertEqual(done[0], 1)
        for name in ("decision", "task", "lesson"):
            self.assertIn(name, done[2])

    def test_s63_add_refuses_stdin_that_is_not_a_json_object_and_a_deadline_that_is_not_relative(self):
        unit = self.code_change()
        for text in ("{nope", "[1]", "null"):
            done = call("code-better", "add", unit, "decision", "--by", "c", stdin=text)
            self.assertEqual(done[0], 1, text)
        for deadline in ("2030-01-01T00:00:00Z", "+10", "10m", "+m", "+-5m", 10, "soon"):
            done = call("code-better", "add", unit, "decision", "--by", "c", stdin={**WAITING, "deadline": deadline})
            self.assertEqual(done[0], 1, deadline)
            self.assertIn("deadline", done[2])
        self.assertFalse((unit / "decisions.jsonl").exists())

    def test_s49_a_relative_deadline_becomes_that_time_from_now(self):
        unit = self.code_change()
        before = datetime.now(timezone.utc).replace(microsecond=0)
        done = call("code-better", "add", unit, "decision", "--by", "c", stdin={**WAITING, "deadline": "+10m"})
        self.assertEqual(done[0], 0, done)
        (line,) = lines_of(unit / "decisions.jsonl")
        stored = datetime.strptime(line["deadline"], records.TIME).replace(tzinfo=timezone.utc)
        self.assertTrue(timedelta(minutes=10) <= stored - before <= timedelta(minutes=10, seconds=30), line)

    def test_s6_a_folder_entry_is_created_exclusively_and_retries_on_the_next_number(self):
        board = self.board()
        (board / "questions" / "Q-ana-2.json").write_text("{}")
        # the next number is found by looking in the folder; a file that appears after that look is skipped
        original = records._before_write
        calls = []

        def appear(unit, relative):
            calls.append(relative)
            if len(calls) == 1:
                (unit.path / "questions" / "Q-ana-3.json").write_text("{}")

        with mock.patch.object(records, "_before_write", appear):
            done = call("research-better", "add", board, "question", "--by", "ana", stdin=QUESTION)
        self.assertEqual((done[0], done[1].strip()), (0, "Q-ana-4"), done)
        self.assertEqual(calls, ["questions/Q-ana-3.json", "questions/Q-ana-4.json"])
        self.assertEqual(json.loads((board / "questions" / "Q-ana-4.json").read_text())["id"], "Q-ana-4")
        self.assertIs(records._before_write, original)

    def test_s7_id_is_accepted_only_for_chosen_names_and_not_for_a_type_of_the_unit(self):
        unit = self.architect()
        perspective = example("architect-better-examples.json", "perspectives.jsonl")
        done = call(
            "architect-better", "add", unit, "perspective", "--by", "architect", "--id", "security", stdin=perspective
        )
        self.assertEqual(done[:2], (0, "security\n"), done)
        self.assertEqual(lines_of(unit / "perspectives.jsonl")[0]["id"], "security")
        done = call("architect-better", "add", unit, "decision", "--by", "architect", "--id", "x", stdin={})
        self.assertEqual(done[0], 1)
        self.assertIn("--id", done[2])
        done = call(
            "architect-better", "add", unit, "perspective", "--by", "architect", "--id", "design", stdin=perspective
        )
        self.assertEqual(done[0], 1)
        self.assertIn("record type", done[2])
        done = call("architect-better", "add", unit, "perspective", "--by", "architect", stdin=perspective)
        self.assertEqual(done[0], 1)
        self.assertIn("--id is missing", done[2])
        done = call(
            "architect-better", "add", unit, "perspective", "--by", "architect", "--id", "security", stdin=perspective
        )
        self.assertEqual(done[0], 1)
        self.assertIn("already exists", done[2])
        done = call(
            "architect-better", "add", unit, "perspective", "--by", "architect", "--id", "../x", stdin=perspective
        )
        self.assertEqual(done[0], 1)

    def test_s10_add_and_set_refuse_every_conversation_type(self):
        unit = self.code_change()
        (unit / "conversation.jsonl").write_text("")
        for name in ("reply", "comment", "answer", "status", "note"):
            for verb in ("add", "set"):
                args = ("add", unit, name, "--by", "c") if verb == "add" else ("set", unit, name)
                done = call("code-better", *args, stdin={})
                self.assertEqual(done[0], 1, (verb, name))
                self.assertIn("page commands", done[2])
        self.assertEqual((unit / "conversation.jsonl").read_text(), "")

    def test_s70_add_on_an_existing_single_record_file_refuses_and_names_set(self):
        board = self.board()
        done = call("research-better", "add", board, "brief", "--by", "c", stdin=BOARD_HEAD)
        self.assertEqual(done[0], 1)
        self.assertIn(f"use set {board.relative_to(self.repo)} brief", done[2].replace(str(self.repo) + "/", ""))
        unit = self.architect()
        design_ = example("architect-better-examples.json", "design.json")
        first = call("architect-better", "add", unit, "design", "--by", "architect", stdin=design_)
        self.assertEqual(first[0], 0, first)
        again = call("architect-better", "add", unit, "design", "--by", "architect", stdin=design_)
        self.assertEqual(again[0], 1, (first, again))
        self.assertIn("already exists", again[2])

    def test_s71_by_defaults_to_for_and_for_is_checked_before_a_path_is_built(self):
        unit = self.code_change()
        self.task(unit)
        call("code-better", "add", unit, "card", "--for", "builder-1", "--by", "coordinator", stdin=CARD)
        done = call("code-better", "add", unit, "start", "--for", "builder-1", stdin={"text": "go"})
        self.assertEqual(done[0], 0, done)
        self.assertEqual(lines_of(unit / "logs" / "builder-1.jsonl")[0]["by"], "builder-1")
        done = call(
            "code-better", "add", unit, "start", "--for", "builder-1", "--by", "coordinator", stdin={"text": "go"}
        )
        self.assertEqual(lines_of(unit / "logs" / "builder-1.jsonl")[1]["by"], "coordinator")
        for bad in ("../x", "A", "a b", "", "a_b", "a/b"):
            done = call("code-better", "add", unit, "start", "--for", bad, stdin={"text": "go"})
            self.assertEqual(done[0], 1, bad)
        self.assertEqual(sorted(p.name for p in (unit / "logs").iterdir()), ["builder-1.card.json", "builder-1.jsonl"])
        self.assertEqual(call("code-better", "add", unit, "start", stdin={"text": "go"})[0], 1)  # no --for
        self.assertEqual(
            call("code-better", "add", unit, "decision", "--for", "a", stdin=DECISION)[0], 1
        )  # --for unused

    def test_a_per_agent_single_record_file_is_named_by_for(self):
        unit = self.code_change()
        self.task(unit)
        done = call("code-better", "add", unit, "card", "--for", "builder-1", "--by", "coordinator", stdin=CARD)
        self.assertEqual(done[0], 0, done)
        self.assertTrue((unit / "logs" / "builder-1.card.json").is_file())
        again = call("code-better", "add", unit, "card", "--for", "builder-1", "--by", "coordinator", stdin=CARD)
        self.assertEqual(again[0], 1)
        self.assertIn("builder-1 exists already", again[2])

    def test_s31_other_refusals_name_the_unit_the_reason_and_the_next_command(self):
        unit = self.code_change()
        bare = self.unit(".code/bare")
        bare.mkdir()
        done = call("code-better", "add", bare, "decision", "--by", "c", stdin=DECISION)
        self.assertEqual(done[0], 1)
        self.assertRegex(done[2], r"^code-better: .code/bare: .+\. run create ")
        done = call("code-better", "add", unit, "decision", stdin=DECISION)
        self.assertEqual(done[0], 1)
        self.assertRegex(done[2], r"^code-better: \.code/x: .+\. \S")

    def test_s12_a_bad_line_elsewhere_is_a_warning_and_stays_as_it_was(self):
        unit = self.code_change()
        call("code-better", "add", unit, "decision", "--by", "c", stdin=DECISION)
        stale = {"type": "decision", "at": "2026-11-23T00:00:00Z"}
        with open(unit / "decisions.jsonl", "a") as file:
            file.write(json.dumps(stale) + "\n")
        before = (unit / "decisions.jsonl").read_bytes()
        done = call(
            "code-better", "add", unit, "progress", "--by", "c", stdin={"about": {"type": "change"}, "text": "t"}
        )
        self.assertEqual(done[0], 0, done)
        self.assertEqual((unit / "decisions.jsonl").read_bytes(), before)
        done = call("code-better", "add", unit, "decision", "--by", "c", stdin=DECISION)
        self.assertEqual(done[:2], (0, "D2\n"), done)
        self.assertIn("warning: ", done[2])
        self.assertIn("decisions.jsonl:2", done[2])
        self.assertTrue((unit / "decisions.jsonl").read_bytes().startswith(before))

    def test_s11_a_file_that_changed_between_the_read_and_the_write_gives_exit_4_and_no_write(self):
        unit = self.code_change()
        call("code-better", "add", unit, "decision", "--by", "c", stdin=DECISION)
        target = unit / "decisions.jsonl"

        def other_writer(_unit, relative):
            with open(target, "a") as file:
                file.write(json.dumps({"type": "decision", "at": "x"}) + "\n")

        before = target.read_bytes()
        with mock.patch.object(records, "_before_write", other_writer):
            done = call("code-better", "add", unit, "decision", "--by", "c", stdin=DECISION)
        self.assertEqual(done[0], 4, done)
        self.assertIn("busy: the file changed while I worked; run the command again", done[2])
        self.assertEqual(target.read_bytes()[: len(before)], before)
        self.assertEqual(len(target.read_bytes().splitlines()), 2)  # only the other writer's line

    def test_s11_a_single_file_that_appears_between_the_read_and_the_write_is_busy(self):
        unit = self.architect()
        design_ = example("architect-better-examples.json", "design.json")

        def appears(unit_, relative):
            (unit_.path / "design.json").write_text("{}")

        with mock.patch.object(records, "_before_write", appears):
            done = call("architect-better", "add", unit, "design", "--by", "architect", stdin=design_)
        self.assertEqual(done[0], 4, done)
        self.assertEqual((unit / "design.json").read_text(), "{}")

    def test_a_file_without_a_final_newline_is_not_joined_to_the_new_line(self):
        unit = self.code_change()
        call("code-better", "add", unit, "decision", "--by", "c", stdin=DECISION)
        path = unit / "decisions.jsonl"
        path.write_text(path.read_text().rstrip("\n"))
        done = call("code-better", "add", unit, "decision", "--by", "c", stdin=DECISION)
        self.assertEqual(done[:2], (0, "D2\n"), done)
        self.assertEqual(len(lines_of(path)), 2)

    def test_a_lone_surrogate_is_refused_not_a_crash(self):
        unit = self.code_change()
        done = call(
            "code-better", "add", unit, "decision", "--by", "c", stdin=json.dumps({**DECISION, "asked": "\ud800"})
        )
        self.assertEqual(done[0], 1, done)
        self.assertFalse((unit / "decisions.jsonl").exists())

    def test_every_verb_refuses_a_symlinked_target_and_a_unit_of_another_skill(self):
        unit = self.code_change()
        elsewhere = self.repo / "elsewhere.jsonl"
        elsewhere.write_text("")
        os.symlink(elsewhere, unit / "decisions.jsonl")
        for args in (("add", unit, "decision", "--by", "c"), ("add", unit, "decision", "--by", "c")):
            self.assertEqual(call("code-better", *args, stdin=DECISION)[0], 1)
        self.assertEqual(elsewhere.read_text(), "")
        arch = self.unit(".architect/a")
        arch.mkdir(parents=True)
        (arch / "architect.json").write_text("{}")
        done = call("code-better", "add", arch, "decision", "--by", "c", stdin=DECISION)
        self.assertEqual(done[0], 1)
        self.assertIn("architect-better", done[2])

    def test_an_add_guard_can_refuse_by_type_and_sees_the_target(self):
        unit = self.code_change()
        seen = []

        def guard(ctx):
            seen.append((ctx.type, ctx.path, ctx.exists, ctx.for_agent, ctx.by, ctx.record["type"]))
            raise paths.refusal(ctx.unit.label, "no card for this log", "add the card first")

        with mock.patch.dict(records.ADD_GUARDS, {"code-better": [(("start",), guard)]}):
            done = call("code-better", "add", unit, "start", "--for", "b-1", stdin={"text": "go"})
            self.assertEqual(done[0], 1)
            self.assertIn("no card for this log", done[2])
            self.assertEqual(seen, [("start", "logs/b-1.jsonl", False, "b-1", "b-1", "start")])
            self.assertEqual(call("code-better", "add", unit, "decision", "--by", "c", stdin=DECISION)[0], 0)
        self.assertFalse((unit / "logs" / "b-1.jsonl").exists())


class Follow(Repo):
    """Follow-ups after the review of T2."""

    def corrupt_first_line(self, path, **change):
        records_ = lines_of(path)
        records_[0].update(change)
        Path(path).write_text(jsonl(*records_))

    def test_a_pointer_to_a_line_that_fails_its_schema_in_the_same_file_blocks_the_write(self):
        unit = self.code_change()
        done = call(
            "code-better", "add", unit, "problem", "--by", "c", stdin={"about": {"type": "change"}, "text": "CI"}
        )
        self.assertEqual(done[:2], (0, "P1\n"), done)
        self.corrupt_first_line(unit / "progress.jsonl", nope=1)
        before = snapshot(unit)
        done = call("code-better", "add", unit, "resolved", "--by", "c", stdin={"to": "P1", "text": "fixed"})
        self.assertEqual(done[0], 1, done)
        self.assertRegex(
            done[2],
            r"^code-better: \.code/x: it points to P1, whose line fails its schema\. Fix that line, then run the command again\n$",
        )
        self.assertEqual(snapshot(unit), before)
        # a record that does not point to it is still added, with the warning
        done = call(
            "code-better", "add", unit, "progress", "--by", "c", stdin={"about": {"type": "change"}, "text": "t"}
        )
        self.assertEqual(done[0], 0, done)

    def test_a_pointer_to_a_line_that_fails_its_schema_in_another_file_blocks_add_and_set(self):
        unit = self.code_change()
        call("code-better", "add", unit, "task", "--by", "c", stdin=TASK)
        self.corrupt_first_line(unit / "tasks.jsonl", status="bogus")
        pointing = {**DECISION, "about": {"type": "task", "task": "T1"}}
        before = snapshot(unit)
        done = call("code-better", "add", unit, "decision", "--by", "c", stdin=pointing)
        self.assertEqual(done[0], 1, done)
        self.assertIn("it points to T1, whose line fails its schema", done[2])
        self.assertEqual(snapshot(unit), before)
        # the same through set: a good decision patched to point to the bad task
        (unit / "tasks.jsonl").write_text(jsonl(*[{**r, "status": "todo"} for r in lines_of(unit / "tasks.jsonl")]))
        self.assertEqual(call("code-better", "add", unit, "decision", "--by", "c", stdin=DECISION)[0], 0)
        self.corrupt_first_line(unit / "tasks.jsonl", status="bogus")
        done = call("code-better", "set", unit, "D1", stdin={"about": {"type": "task", "task": "T1"}})
        self.assertEqual(done[0], 1, done)
        self.assertIn("it points to T1, whose line fails its schema", done[2])
        # the same in a folder without git, reached through a symlinked path: the unit and the pointer agree on paths
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "real").mkdir()
            (Path(tmp) / "link").symlink_to(Path(tmp) / "real")
            loose = Path(tmp) / "link" / ".code" / "x"
            self.assertEqual(call("code-better", "create", loose, "--by", "c", stdin=CODE_HEAD)[0], 0)
            call("code-better", "add", loose, "task", "--by", "c", stdin=TASK)
            self.corrupt_first_line(loose / "tasks.jsonl", status="bogus")
            done = call("code-better", "add", loose, "decision", "--by", "c", stdin=pointing)
            self.assertEqual(done[0], 1, done)
            self.assertIn("it points to T1, whose line fails its schema", done[2])

    def test_a_pointer_to_an_old_format_line_does_not_block(self):
        unit = self.code_change()
        old = {"type": "decision", "at": "2026-11-01T10:00:00Z", "by": "board", "id": "D3", "asked": "q?"}
        old.update({"default": "a", "deadline": "2026-11-01T10:00:00Z", "status": "pending"})
        (unit / "decisions.jsonl").write_text(jsonl(old))
        spec = {
            **example("code-better-examples.json", "spec.jsonl", 1),
            "source": {"type": "decision", "decision": "D3"},
        }
        done = call("code-better", "add", unit, "spec", "--by", "c", stdin=spec)
        self.assertEqual(done[:2], (0, "S1\n"), done)
        self.assertEqual(done[2], "")

    def test_a_single_record_that_appears_after_the_check_is_never_overwritten(self):
        unit = self.code_change()
        self.task(unit)

        def appears(unit_, relative, stat):
            (unit_.path / "logs" / "b-1.card.json").write_text('{"other": "writer"}')

        with mock.patch.object(records, "_still", appears):
            done = call("code-better", "add", unit, "card", "--for", "b-1", "--by", "c", stdin=CARD)
        self.assertEqual(done[0], 4, done)
        self.assertIn("busy: the file changed while I worked", done[2])
        self.assertEqual((unit / "logs" / "b-1.card.json").read_text(), '{"other": "writer"}')

    def test_empty_stdin_is_accepted_only_by_set_with_unset(self):
        unit = self.code_change()
        call("code-better", "add", unit, "decision", "--by", "c", stdin={**WAITING, "default": "A"})
        before = snapshot(unit)
        for args in (("set", unit, "D1"), ("add", unit, "decision", "--by", "c")):
            for text in ("", "  \n"):
                done = call("code-better", *args, stdin=text)
                self.assertEqual(done[0], 1, (args, done))
                self.assertIn("pass the fields as one JSON object on stdin", done[2])
        done = call("code-better", "create", self.unit(".code/e"), "--by", "c", stdin="")
        self.assertEqual(done[0], 1)
        self.assertIn("pass the fields as one JSON object on stdin", done[2])
        self.assertFalse(self.unit(".code/e").exists())
        self.assertEqual(snapshot(unit), before)
        done = call("code-better", "set", unit, "D1", "--unset", "default", stdin="")
        self.assertEqual(done[0], 1)  # a waiting decision needs its default: the unset is checked, not skipped
        self.assertIn("default", done[1])

    def test_a_refused_name_carries_the_unit_in_one_place(self):
        unit = self.code_change()
        for args in (
            ("add", unit, "start", "--for", "../x"),
            ("add", unit, "decision", "--by", "user"),
            ("set", unit, "card", "--for", "A b"),
        ):
            done = call("code-better", *args, stdin=DECISION)
            self.assertEqual(done[0], 1, args)
            self.assertRegex(done[2], r"^code-better: \.code/x: ", args)
        done = call("code-better", "create", self.unit(".code/y"), "--by", "Bad", stdin=CODE_HEAD)
        self.assertRegex(done[2], r"^code-better: \.code/y: 'Bad'", done)


class Set(Repo):
    def decided(self, unit, **fields):
        done = call("code-better", "add", unit, "decision", "--by", "coordinator", stdin={**DECISION, **fields})
        self.assertEqual(done[0], 0, done)
        return done[1].strip()

    def test_s8_set_merges_fields_keeps_the_stamps_and_every_other_line_byte_for_byte(self):
        unit = self.code_change()
        self.decided(unit)
        self.decided(unit)
        self.decided(unit)
        path = unit / "decisions.jsonl"
        before = path.read_bytes().split(b"\n")
        done = call("code-better", "set", unit, "D2", stdin={"decision": "B"})
        self.assertEqual(done[:2], (0, "D2\n"), done)
        after = path.read_bytes().split(b"\n")
        self.assertEqual((after[0], after[2], after[3]), (before[0], before[2], before[3]))
        old, new = json.loads(before[1]), json.loads(after[1])
        self.assertEqual(
            {k: v for k, v in new.items() if k != "decision"}, {k: v for k, v in old.items() if k != "decision"}
        )
        self.assertEqual(new["decision"], "B")
        self.assertEqual(list(new), list(old))
        for stamped in ("at", "by", "id", "type"):
            done = call("code-better", "set", unit, "D2", stdin={stamped: "x" if stamped != "type" else "task"})
            self.assertEqual(done[0], 1, stamped)
        self.assertEqual(path.read_bytes().split(b"\n")[1], after[1])

    def test_s8_set_by_type_changes_a_single_record_file_and_a_folder_entry(self):
        board = self.board()
        done = call("research-better", "set", board, "brief", "--by", "coordinator", stdin={"status": "stopped"})
        self.assertEqual(done[0], 0, done)
        self.assertEqual(json.loads((board / "brief.json").read_text())["status"], "stopped")
        call("research-better", "add", board, "question", "--by", "ana", stdin=QUESTION)
        done = call("research-better", "set", board, "Q-ana-1", stdin={"status": "in progress", "owner": "ana"})
        self.assertEqual(done[0], 0, done)
        self.assertEqual(json.loads((board / "questions" / "Q-ana-1.json").read_text())["status"], "in progress")
        self.assertEqual(call("research-better", "check", board)[0], 0)
        unit = self.code_change()
        call("code-better", "add", unit, "task", "--by", "coordinator", stdin=TASK)
        call("code-better", "add", unit, "card", "--for", "b-1", "--by", "coordinator", stdin=CARD)
        self.assertEqual(call("code-better", "set", unit, "card", stdin={"branch": "c"})[0], 1)  # needs --for
        done = call("code-better", "set", unit, "card", "--for", "b-1", stdin={"branch": "c"})
        self.assertEqual(done[0], 0, done)
        self.assertEqual(json.loads((unit / "logs" / "b-1.card.json").read_text())["branch"], "c")

    def test_s9_null_is_stored_where_the_schema_allows_it_and_otherwise_removes_the_field(self):
        unit = self.code_change()
        call("code-better", "add", unit, "decision", "--by", "c", stdin={**WAITING, "deadline": "+10m"})
        done = call(
            "code-better",
            "set",
            unit,
            "D1",
            stdin={"status": "decided", "decision": "A", "default": None, "deadline": None},
        )
        self.assertEqual(done[0], 0, done)
        (line,) = lines_of(unit / "decisions.jsonl")
        self.assertNotIn("default", line)
        self.assertNotIn("deadline", line)
        call("code-better", "add", unit, "decision", "--by", "c", stdin={**WAITING, "default": "A", "deadline": "+10m"})
        done = call("code-better", "set", unit, "D2", stdin={"default": None, "deadline": None})
        self.assertEqual(done[0], 0, done)
        two = lines_of(unit / "decisions.jsonl")[1]
        self.assertEqual((two["default"], two["deadline"]), (None, None))

    def test_s9_unset_removes_a_field(self):
        unit = self.code_change()
        call("code-better", "add", unit, "decision", "--by", "c", stdin=WAITING)
        done = call("code-better", "set", unit, "D1", "--unset", "default", stdin={})
        self.assertEqual(done[0], 1)  # a required field of a waiting decision
        done = call(
            "code-better",
            "set",
            unit,
            "D1",
            "--unset",
            "default",
            "--unset",
            "deadline",
            stdin={"status": "decided", "decision": "A"},
        )
        self.assertEqual(done[0], 0, done)
        (line,) = lines_of(unit / "decisions.jsonl")
        self.assertEqual((line["status"], "default" in line, "deadline" in line), ("decided", False, False))

    def test_s2_set_that_makes_the_record_invalid_writes_nothing(self):
        unit = self.code_change()
        self.decided(unit)
        before = snapshot(unit)
        for patch in ({"status": "bogus"}, {"status": "waiting"}, {"nope": 1}, {"asked": None}):
            done = call("code-better", "set", unit, "D1", stdin=patch)
            self.assertEqual(done[0], 1, patch)
            self.assertRegex(done[1], r"decisions\.jsonl:1: ")
            self.assertEqual(snapshot(unit), before)

    def test_s63_set_refuses_bad_stdin_and_an_absolute_deadline(self):
        unit = self.code_change()
        call("code-better", "add", unit, "decision", "--by", "c", stdin=WAITING)
        for text in ("nope", "[]"):
            self.assertEqual(call("code-better", "set", unit, "D1", stdin=text)[0], 1)
        done = call("code-better", "set", unit, "D1", stdin={"deadline": "2030-01-01T00:00:00Z"})
        self.assertEqual(done[0], 1)
        done = call("code-better", "set", unit, "D1", stdin={"deadline": "+5m"})
        self.assertEqual(done[0], 0, done)
        self.assertTrue(lines_of(unit / "decisions.jsonl")[0]["deadline"].endswith("Z"))

    def test_s69_set_looks_only_in_its_own_units_files_never_a_nested_unit(self):
        unit = self.code_change()
        audit = self.unit(".code/audit/2026-11-22")
        done = call(
            "code-better", "create", audit, "--by", "auditor", stdin={"goal": "g", "commit": "abc", "not_read": None}
        )
        self.assertEqual(done[0], 0, done)
        finding = {**example("code-better-examples.json", "audit/<date>/findings.jsonl"), "evidence_ids": []}
        added = call("code-better", "add", audit, "finding", "--by", "auditor", stdin=finding)
        self.assertEqual(added[:2], (0, "A1\n"), added)
        done = call("code-better", "set", unit, "A1", stdin={"cost": "d"})
        self.assertEqual(done[0], 1)
        self.assertIn("no record with id 'A1'", done[2])
        done = call("code-better", "set", audit, "A1", stdin={"cost": "d"})
        self.assertEqual(done[0], 0, done)
        # the audit's own files do not appear among the change's types
        self.assertEqual(call("code-better", "add", unit, "finding", "--by", "c", stdin=finding)[0], 1)

    def test_set_with_an_unknown_id_or_a_type_with_many_records_says_what_to_do(self):
        unit = self.code_change()
        self.decided(unit)
        done = call("code-better", "set", unit, "D9", stdin={"decision": "B"})
        self.assertEqual(done[0], 1)
        self.assertIn("no record with id 'D9'", done[2])
        done = call("code-better", "set", unit, "decision", stdin={"decision": "B"})
        self.assertEqual(done[0], 1)
        self.assertIn("by its id", done[2])
        done = call("code-better", "set", unit, "card", "--for", "x", stdin={})
        self.assertEqual(done[0], 1)
        self.assertIn("use add", done[2])

    def test_s11_set_gives_exit_4_when_the_file_changed_and_writes_nothing(self):
        unit = self.code_change()
        self.decided(unit)
        path = unit / "decisions.jsonl"

        def other_writer(_unit, relative):
            os.utime(path, ns=(1, 1))

        before = path.read_bytes()
        with mock.patch.object(records, "_before_write", other_writer):
            done = call("code-better", "set", unit, "D1", stdin={"decision": "B"})
        self.assertEqual(done[0], 4, done)
        self.assertEqual(path.read_bytes(), before)

    def test_s12_set_keeps_a_bad_line_unchanged_and_warns_about_it(self):
        unit = self.code_change()
        self.decided(unit)
        with open(unit / "decisions.jsonl", "a") as file:
            file.write("{broken\n")
        done = call("code-better", "set", unit, "D1", stdin={"decision": "B"})
        self.assertEqual(done[0], 0, done)
        self.assertIn("decisions.jsonl:2", done[2])
        self.assertEqual((unit / "decisions.jsonl").read_text().splitlines()[1], "{broken")

    def test_set_does_not_find_an_id_that_may_hide_behind_an_unparsable_line_without_saying_so(self):
        unit = self.code_change()
        (unit / "decisions.jsonl").write_text("{broken\n")
        done = call("code-better", "set", unit, "D1", stdin={"decision": "B"})
        self.assertEqual(done[0], 1)
        self.assertIn("does not parse", done[2])

    def test_a_set_that_changes_nothing_writes_nothing(self):
        unit = self.code_change()
        self.decided(unit)
        os.utime(unit / "decisions.jsonl", ns=(5, 5))
        done = call("code-better", "set", unit, "D1", stdin={"decision": "A"})
        self.assertEqual(done[0], 0)
        self.assertEqual((unit / "decisions.jsonl").stat().st_mtime_ns, 5)


class Layout(unittest.TestCase):
    def test_every_unit_kind_maps_each_type_to_one_file_and_ids_are_declared_for_the_counted_types(self):
        for name, skill in SKILLS.items():
            docs = schema.docs_for(skill.package)
            for kind in skill.kinds:
                unit = paths.Unit(Path("/x") / kind.folder / "u", Path("/x"), kind, skill)
                lay = records.layout(unit, docs)
                self.assertTrue(lay.forms or lay.conversation, (name, kind.kind))
                self.assertNotIn(kind.head_type, lay.conversation)
                for label, form in lay.forms.items():
                    self.assertFalse(set(lay.conversation) & {label}, (name, label))
                    self.assertTrue(form.pattern.endswith((".json", ".jsonl")), (name, label))
                if kind.head and kind.head_type in docs_types(docs):
                    self.assertEqual(lay.forms[kind.head_type].pattern, kind.head, (name, kind.kind))

    def test_a_nested_units_files_are_not_the_outer_units_and_the_audit_has_its_own(self):
        skill = SKILLS["code-better"]
        docs = schema.docs_for(skill.package)
        change, audit = skill.kinds
        outer = records.layout(paths.Unit(Path("/x/.code/u"), Path("/x"), change, skill), docs)
        inner = records.layout(paths.Unit(Path("/x/.code/audit/d"), Path("/x"), audit, skill), docs)
        self.assertNotIn("finding", outer.forms)
        self.assertEqual(inner.forms["finding"].pattern, "findings.jsonl")
        self.assertEqual(inner.forms["audit"].pattern, "audit.json")
        self.assertEqual(outer.forms["card"].pattern, "logs/*.card.json")
        self.assertTrue(outer.forms["card"].per_agent and outer.forms["start"].per_agent)
        self.assertTrue(
            records.layout(
                paths.Unit(
                    Path("/x/.research/b"), Path("/x"), SKILLS["research-better"].kinds[0], SKILLS["research-better"]
                ),
                schema.docs_for("research"),
            )
            .forms["claim"]
            .folder
        )


def docs_types(docs):
    return {t for doc in docs.values() for t in records._types_of(doc)}


class Safety(Repo):
    def test_s25_no_verb_writes_outside_the_unit(self):
        outside = self.repo / "other"
        outside.mkdir()
        (outside / "keep.txt").write_text("keep")
        (self.repo / "README.md").write_text("readme")
        before = snapshot(self.repo)
        exclude_before = self.exclude()
        unit = self.code_change()
        after_create = snapshot(self.repo)
        inside = {k for k in after_create if k.startswith(".code/x/")}
        self.assertEqual({k: v for k, v in after_create.items() if k not in inside}, before)
        self.assertEqual(self.exclude(), exclude_before)
        steps = [
            ("add", unit, "decision", "--by", "c"),
            ("add", unit, "progress", "--by", "c"),
            ("add", unit, "task", "--by", "c"),
            ("add", unit, "card", "--for", "b-1", "--by", "c"),
            ("add", unit, "start", "--for", "b-1"),
            ("set", unit, "D1"),
            ("set", unit, "code"),
            ("set", unit, "card", "--for", "b-1"),
        ]
        stdins = [
            DECISION,
            {"about": {"type": "change"}, "text": "t"},
            TASK,
            CARD,
            {"text": "go"},
            {"decision": "B"},
            {"goal": "g2"},
            {"branch": "z"},
        ]
        for step, stdin in zip(steps, stdins, strict=True):
            done = call("code-better", *step, stdin=stdin)
            self.assertEqual(done[0], 0, (step, done))
        now = snapshot(self.repo)
        self.assertEqual({k: v for k, v in now.items() if not k.startswith(".code/x/")}, before)
        self.assertEqual(self.exclude(), exclude_before)
        # a refused add changes nothing, inside or out
        frozen = snapshot(self.repo)
        call("code-better", "add", unit, "decision", "--by", "c", stdin={})
        self.assertEqual(snapshot(self.repo), frozen)


class Concurrency(Repo):
    def test_twenty_parallel_adds_into_one_board_give_distinct_ids_and_valid_files(self):
        board = self.board()
        agents = ["ana", "bob", "ana", "ana"]

        def one(index):
            result = run(
                "research-better",
                "add",
                str(board),
                "question",
                "--by",
                agents[index % 4],
                stdin=json.dumps(QUESTION),
                cwd=self.repo,
            )
            return result

        with ThreadPoolExecutor(max_workers=20) as pool:
            results = list(pool.map(one, range(20)))
        for result in results:
            self.assertEqual(result.returncode, 0, result.stderr)
        ids = [r.stdout.strip() for r in results]
        self.assertEqual(len(set(ids)), 20, ids)
        files = sorted(p.name for p in (board / "questions").iterdir())
        self.assertEqual(files, sorted(f"{i}.json" for i in ids))
        checked = run("research-better", "check", str(board), cwd=self.repo)
        self.assertEqual(checked.returncode, 0, checked.stdout)
        for path in (board / "questions").iterdir():
            self.assertEqual(json.loads(path.read_text())["id"], path.stem)
        self.assertFalse([p for p in (board / "questions").iterdir() if p.name.endswith(".tmp")])


class Examples(Repo):
    """Every example line of the code-better format page, added through `add` in file order into a change that holds
    what the examples point to: the requirement Q1 and decisions D1-D3 of its architect design, specs S1-S8, tasks
    T1-T3. `add` accepts each one. Not added here: the code.json line (a head,
    written by `create`), the decisions.jsonl lines (the "answered on the page" one points to a page event this unit does
    not hold) and audit/* (another unit kind); the old test skipped them too."""

    def add(self, skill, unit, label, fields, *more):
        done = call(skill, "add", unit, label, "--by", "coordinator", *more, stdin=fields)
        self.assertEqual(done[0], 0, done)

    def supporting(self):
        design = self.architect()
        request = {"type": "request", "sentence": "Add a dashboard that shows each agent's task, mode and state."}
        quality = {"kind": "quality", "text": "Show a question within 2 seconds.", "source": request}
        decision = {"title": "t", "drivers": ["Q1"], "chosen": "a", "rejected": [{"option": "b", "why": "c"}]}
        spec = {"statement": "s", "source": {"type": "request", "sentence": "x"}, "checked_by": "c"}
        self.add("architect-better", design, "requirement", quality)
        for _ in range(3):
            self.add("architect-better", design, "decision", {**decision, "drawback": "d"})
        self.add("architect-better", design, "spec", {**spec, "source": {"type": "requirement", "requirement": "Q1"}})
        unit = self.unit(".code/x")
        head = {**CODE_HEAD, "design": {"type": "architect", "folder": ".architect/a"}}
        done = call("code-better", "create", unit, "--by", "coordinator", stdin=head)
        self.assertEqual(done[0], 0, done)
        for label, fields, count in (("spec", spec, 7), ("task", TASK, 3)):
            for _ in range(count):
                self.add("code-better", unit, label, fields)
        return unit

    def test_every_example_line_is_accepted_by_add(self):
        data = json.loads((FIXTURES / "code-better-examples.json").read_text())
        unit = self.supporting()
        for name, entries in data.items():
            if name in ("code.json", "decisions.jsonl") or name.startswith("audit/"):
                continue
            for entry in entries:
                record = json.loads(entry["line"])
                label, by = record.pop("type"), record.pop("by")
                for stamped in ("at", "id"):
                    record.pop(stamped, None)
                args = ["add", unit, label, "--by", by]
                if name == "logs/<agent>.card.json":
                    args += ["--for", f"{record['role']}-t3"]
                elif name == "logs/<agent>.jsonl":
                    args += ["--for", by]
                with self.subTest(name=name, title=entry["title"]):
                    done = call("code-better", *args, stdin=record)
                    self.assertEqual(done[0], 0, done)


class Sweep(Repo):
    """For every record type of every skill's units: what `add` refuses, whatever the type."""

    def types(self):
        found = []
        for name, skill in SKILLS.items():
            docs = schema.docs_for(skill.package)
            for kind in skill.kinds:
                unit = paths.Unit(Path("/x") / kind.folder / "u", Path("/x"), kind, skill)
                lay = records.layout(unit, docs)
                for label, form in sorted(lay.forms.items()):
                    found.append((name, kind, label, form))
        return found

    def make(self, name, kind):
        heads = {
            "code-better": CODE_HEAD if kind.kind == "change" else {"goal": "g", "commit": "c", "not_read": None},
            "research-better": BOARD_HEAD,
        }
        unit = self.unit(f"{kind.folder}/sweep")
        if unit.exists():
            return unit
        if name in heads:
            done = call(name, "create", unit, "--by", "coordinator", stdin=heads[name])
            self.assertEqual(done[0], 0, done)
        else:
            unit.mkdir(parents=True)
            (unit / kind.head).write_text("{}")
        return unit

    def args(self, name, unit, label, form):
        args = ["add", unit, label]
        if form.id and form.id.get("from") == "caller":
            args += ["--id", "chosen-name"]
        agent = form.per_agent or bool(form.id and form.id.get("agent"))
        return args + (["--for", "agent-1"] if agent else ["--by", "agent-1"])

    def test_every_type_refuses_stamped_fields_bad_stdin_and_an_unknown_field_without_writing(self):
        for name, kind, label, form in sweep.cases(self.types(), key=[lambda c: c[0], lambda c: c[3].pattern]):
            with self.subTest(skill=name, kind=kind.kind, type=label):
                unit = self.make(name, kind)
                head = snapshot(unit) if form.single and not form.per_agent and unit.exists() else None
                before = snapshot(unit)
                for stdin in ({"at": "x"}, {"by": "x"}, {"id": "x"}, "{nope", "[1]", {"type": "other"}):
                    done = call(name, *self.args(name, unit, label, form), stdin=stdin)
                    self.assertEqual(done[0], 1, (stdin, done))
                done = call(name, *self.args(name, unit, label, form), stdin={"zzz_unknown": 1})
                self.assertIn(done[0], (1,), done)
                self.assertEqual(snapshot(unit), before)
                del head
                self.assertNotEqual(done[0], 5)

    def test_every_type_is_refused_in_a_unit_of_another_skill(self):
        types = [c for c in self.types() if c[0] == "code-better" and c[1].kind == "change"]
        arch = self.unit(".architect/a")
        arch.mkdir(parents=True)
        (arch / "architect.json").write_text("{}")
        for name, _kind, label, form in sweep.cases(types, key=lambda c: c[3].pattern):
            done = call(name, *self.args(name, arch, label, form), stdin={})
            self.assertEqual(done[0], 1, (label, done))
            self.assertIn("architect-better", done[2])


if __name__ == "__main__":
    unittest.main()
