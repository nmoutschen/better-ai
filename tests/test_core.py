"""Tests for the shared core of better.pyz in src/better_ai/: the command line and its exit codes, the paths rules, the
`check` verb, the shared decisions and conversation schemas, and the bundled resources."""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

import sweep  # noqa: E402
from better import SRC, call, run  # noqa: E402

from better_ai import _entry, architect, cli, code, design, paths, records, research, resources, schema, show, skill  # noqa: E402

SKILLS = {
    "architect-better": architect.SKILL,
    "code-better": code.SKILL,
    "design-better": design.SKILL,
    "research-better": research.SKILL,
    "show-better": show.SKILL,
}
OLD = "2026-11-01T10:00:00Z"  # before the cutoff of a source run


def stamp(minutes=0):
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).strftime(records.TIME)


def jsonl(*records):
    return "".join(json.dumps(r) + "\n" for r in records)


class Repo(unittest.TestCase):
    """A scratch git repository with one code-better change, `.code/x`."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(os.path.realpath(tmp.name)) / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.unit = self.repo / ".code" / "x"
        self.unit.mkdir(parents=True)
        self.write(
            "code.json",
            json.dumps(
                {
                    "type": "code",
                    "at": stamp(),
                    "by": "coordinator",
                    "goal": "g",
                    "design": {"type": "request", "text": "t"},
                    "mode": "coordinate",
                }
            ),
        )

    def write(self, name, text):
        path = self.unit / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def check(self, *args, unit=".code/x"):
        return run("code-better", "check", unit, *args, cwd=self.repo)


def decision(id="D1", status="decided", **fields):
    base = {"type": "decision", "at": stamp(), "by": "coordinator", "id": id, "raised_by": "coordinator"}
    base.update({"about": {"type": "change"}, "asked": "which?", "status": status})
    if status == "decided":
        base["decision"] = "this one"
    base.update(fields)
    return base


class Cli(unittest.TestCase):
    def test_s33_help_prints_the_skill_and_the_source_hash_and_lists_the_verbs(self):
        for name in SKILLS:
            result = run(name, "--help")
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.splitlines()[0], f"better.pyz {name} source")
            self.assertIn("check", result.stdout)
        self.assertIn("better.pyz code-better source", run("code-better", "check", "--help").stdout)

    def test_s28_an_unknown_verb_exits_2_and_lists_the_valid_ones(self):
        result = run("code-better", "nope")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid choice: 'nope'", result.stderr)
        self.assertIn("'check'", result.stderr)

    def test_s29_usage_errors_exit_2(self):
        self.assertEqual(run("code-better").returncode, 2)
        self.assertEqual(run("code-better", "check").returncode, 2)
        self.assertEqual(run("code-better", "check", "a", "b").returncode, 2)
        self.assertEqual(run("not-a-skill", "check", "a").returncode, 2)

    def test_s29_exit_codes_0_to_5_in_process(self):
        calls = {
            "ok": lambda args, run: None,
            "refused": mock.Mock(side_effect=paths.Refused("u: no. do this")),
            "slow": mock.Mock(side_effect=cli.TimedOut("nothing came")),
            "busy": mock.Mock(side_effect=cli.Busy("the file changed; run it again")),
            "bug": mock.Mock(side_effect=KeyError("oops")),
        }
        with mock.patch.object(cli, "VERBS", [cli.Verb(name, "x", function) for name, function in calls.items()]):
            codes = {name: call("code-better", name).returncode for name in calls}
        self.assertEqual(codes, {"ok": 0, "refused": 1, "slow": 3, "busy": 4, "bug": 5})

    def test_s30_an_internal_error_is_one_line_naming_the_skill_and_hash(self):
        def boom(args, run):
            raise ModuleNotFoundError("No module named 'gone'", name="gone")

        with mock.patch.object(cli, "VERBS", [cli.Verb("boom", "x", boom)]):
            done = call("code-better", "boom")
        self.assertEqual(done.returncode, 5)
        line = done.stderr.strip()
        self.assertTrue(line.startswith("bug in better.pyz code-better source: ModuleNotFoundError"), line)
        self.assertIn("(missing: gone)", line)
        parent = io.StringIO()
        with contextlib.redirect_stderr(parent):
            _entry.report_bug(
                "code-better", "h1", ImportError("cannot import name 'schema' from 'better_ai'", name="better_ai")
            )
        self.assertNotIn("(missing: better_ai)", parent.getvalue())
        self.assertTrue(line.endswith("set BETTER_AI_TRACEBACK=1 for the full trace"), line)

    def test_s30_an_import_error_in_the_package_is_still_the_bug_line_and_the_trace_comes_on_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "better_ai"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "cli.py").write_text("import module_that_is_not_in_the_zip\n", encoding="utf-8")
            boot = (
                "import sys; sys.path.insert(0, sys.argv.pop(1)); from better_ai._entry import main; sys.exit(main())"
            )
            entry = (SRC / "better_ai" / "_entry.py").read_text(encoding="utf-8")
            (package / "_entry.py").write_text(entry, encoding="utf-8")
            env = {**os.environ, "BETTER_AI_SKILL": "show-better"}
            plain = subprocess.run(
                [sys.executable, "-I", "-c", boot, tmp, "check", "x"], capture_output=True, text=True, env=env
            )
            traced = subprocess.run(
                [sys.executable, "-I", "-c", boot, tmp, "check", "x"],
                capture_output=True,
                text=True,
                env={**env, "BETTER_AI_TRACEBACK": "1"},
            )
        self.assertEqual(plain.returncode, 5)
        self.assertEqual(len(plain.stderr.splitlines()), 1)
        self.assertTrue(plain.stderr.startswith("bug in better.pyz show-better source: ModuleNotFoundError"))
        self.assertIn("(missing: module_that_is_not_in_the_zip)", plain.stderr)
        self.assertIn("set BETTER_AI_TRACEBACK=1 for the full trace", plain.stderr)
        self.assertNotIn("Traceback", plain.stderr)
        self.assertIn("Traceback", traced.stderr)

    def test_a_verb_registered_twice_is_a_bug_and_a_skill_only_verb_is_listed_for_that_skill_only(self):
        with mock.patch.object(cli, "VERBS", []):
            cli.verb("one", help="x")(lambda a, r: None)
            with self.assertRaises(ValueError):
                cli.verb("one", help="x", skills=("code-better",))(lambda a, r: None)
            cli.verb("two", help="x", skills=("show-better",))(lambda a, r: None)
            self.assertEqual([v.name for v in cli._verbs_of(show.SKILL)], ["one", "two"])
            self.assertEqual([v.name for v in cli._verbs_of(code.SKILL)], ["one"])

    def test_every_verb_a_skill_package_defines_is_registered_for_that_skill_only(self):
        # Importing every skill package in one process must not clash, and none of their verbs may leak to other skills.
        import importlib

        for one in SKILLS.values():
            importlib.import_module(f"better_ai.{one.package}")
        for v in cli.VERBS:
            module = getattr(v.run, "__module__", "")
            parts = module.split(".")
            if len(parts) > 1 and parts[1] in {s.package for s in SKILLS.values()}:
                owner = next(s.name for s in SKILLS.values() if s.package == parts[1])
                with self.subTest(verb=v.name, module=module):
                    self.assertEqual(v.skills, (owner,))

    def test_a_verb_from_a_skill_package_without_skills_is_refused(self):
        fn = lambda a, r: None  # noqa: E731
        fn.__module__ = "better_ai.code.somewhere"
        with mock.patch.object(cli, "VERBS", []), self.assertRaises(ValueError):
            cli.verb("x", help="x")(fn)


class Resources(unittest.TestCase):
    def test_every_skill_loads_its_schemas_and_names_only_registered_hooks(self):
        for name, one in SKILLS.items():
            with self.subTest(skill=name):
                docs = schema.docs_for(one.package)
                self.assertIn("base.schema.json", docs)
                self.assertIn("conversation.schema.json", docs)

    def test_a_skills_own_schema_replaces_a_shared_one_of_the_same_name(self):
        shared = schema.docs_for("code")["decisions.schema.json"]
        own = schema.docs_for("architect")["decisions.schema.json"]
        self.assertIn("raised_by", shared["required"])
        self.assertNotEqual(shared, own)

    def test_each_skill_exports_its_unit_kinds(self):
        for name, one in SKILLS.items():
            self.assertEqual(one.name, name)
            self.assertEqual(one.package, name.removesuffix("-better"))
            self.assertTrue(one.kinds)
            for kind in one.kinds:
                self.assertIsInstance(kind, skill.UnitKind)
                self.assertTrue(kind.folder.startswith(one.root))
        self.assertEqual({k.kind for k in code.SKILL.kinds}, {"change", "audit"})
        self.assertEqual(code.SKILL.reserved(".code"), {"audit"})
        # The tables that name the owner of a folder or head file, and the shared packages, are what the skills say.
        listed = json.loads(resources.read_text("skills.json"))
        self.assertEqual(
            {n: s["package"] for n, s in listed["skills"].items()}, {n: s.package for n, s in SKILLS.items()}
        )
        self.assertEqual(skill.OWNER_BY_ROOT, {s.root: n for n, s in SKILLS.items()})
        self.assertEqual(skill.OWNER_BY_HEAD, {k.head: n for n, s in SKILLS.items() for k in s.kinds})
        self.assertEqual(cli.SHARED_PACKAGES, {f[len("better_ai/") : -1] for f in listed["shared"] if f.endswith("/")})

    def test_bundled_files_are_read_by_name(self):
        self.assertEqual(json.loads(resources.read_text("architect/kinds.json"))[0]["name"], "person")
        self.assertFalse(resources.exists("_build.json"))
        info = resources.build_info({"BETTER_AI_SKILL": "show-better"})
        self.assertEqual((info.skill, info.package, info.hash), ("show-better", "show", "source"))
        # The cutoff is skills.json's, unless the environ given says another: never one that is written twice.
        self.assertEqual(info.cutoff, json.loads(resources.read_text("skills.json"))["format_cutoff"])
        pinned = {"BETTER_AI_SKILL": "show-better", "BETTER_AI_CUTOFF": "2026-01-01T00:00:00Z"}
        self.assertEqual(resources.build_info(pinned).cutoff, "2026-01-01T00:00:00Z")
        self.assertEqual(resources.cutoff({}), info.cutoff)


class Units(Repo):
    def resolve(self, argument, name="code-better", **options):
        return paths.resolve_unit(argument, SKILLS[name], **options)

    def refused(self, argument, text, name="code-better", **options):
        with self.assertRaises(paths.Refused) as caught:
            self.resolve(argument, name, **options)
        self.assertIn(text, str(caught.exception))

    def test_s19_a_unit_is_found_from_the_repository_top_level_not_the_working_directory(self):
        before = os.getcwd()
        self.addCleanup(os.chdir, before)
        sub = self.repo / "deep" / "er"
        sub.mkdir(parents=True)
        os.chdir(sub)
        self.assertEqual(self.resolve(str(self.unit)).path, self.unit)
        self.assertEqual(self.resolve("../../.code/x").path, self.unit)

    def test_s19_a_second_worktree_can_reach_the_main_checkouts_unit(self):
        (self.repo / "f").write_text("x", encoding="utf-8")
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t"}
        env["GIT_COMMITTER_EMAIL"] = "t@t"
        for args in (["add", "f"], ["commit", "-qm", "x"], ["worktree", "add", "-q", str(self.repo.parent / "wt")]):
            subprocess.run(["git", "-C", str(self.repo), *args], check=True, env=env, capture_output=True)
        self.assertEqual(
            run("code-better", "check", str(self.unit), cwd=self.repo.parent / "wt").returncode, 0, "main's unit"
        )

    def test_s19_paths_outside_the_skill_folder_slug_are_refused_before_anything_is_read(self):
        for argument in ("../../x", "/tmp/x", "x", ".code", ".code/x/y", "docs/x", ".code/audit"):
            with self.subTest(argument=argument):
                self.refused(os.path.join(self.repo, argument), "", creating=True)
        self.refused(str(self.repo / ".code" / "Bad_Slug"), "not a valid unit name")
        self.refused(str(self.repo / ".code" / "audit"), "reserved")
        self.assertEqual(
            self.resolve(str(self.repo / ".code" / "audit" / "2026-11-22"), creating=True).kind.kind, "audit"
        )

    def test_s19_a_unit_below_a_subfolder_of_the_repository_is_refused(self):
        sub = self.repo / "sub" / ".code" / "y"
        sub.mkdir(parents=True)
        self.refused(str(sub), "top of its repository")

    def test_s20_a_folder_without_the_skills_head_file_is_refused_naming_the_owner(self):
        self.refused(str(self.repo / ".code" / "missing"), "no such unit")
        empty = self.repo / ".code" / "empty"
        empty.mkdir()
        self.refused(str(empty), "no code.json here")
        (empty / "architect.json").write_text("{}", encoding="utf-8")
        self.refused(str(empty), "belongs to architect-better")
        self.refused(str(self.repo / ".architect" / "y"), "belongs to architect-better")
        self.assertEqual(self.resolve(str(empty), creating=True).slug, "empty")

    def test_s20_a_verb_on_another_skills_unit_is_refused_with_exit_1(self):
        (self.repo / ".architect" / "y").mkdir(parents=True)
        result = self.check(unit=".architect/y")
        self.assertEqual(result.returncode, 1)
        self.assertIn("code-better: .architect/y", result.stderr)
        self.assertIn("architect-better", result.stderr)

    def test_s21_target_refuses_a_path_that_leaves_the_unit_or_passes_a_symlink(self):
        unit = self.resolve(str(self.unit))
        for relative in ("../conversation.jsonl", "/etc/passwd", "a/../../b", "", "."):
            with self.subTest(relative=relative), self.assertRaises(paths.Refused):
                unit.target(relative)
        outside = self.repo / "outside"
        outside.mkdir()
        os.symlink(outside, self.unit / "logs")
        (outside / "a.jsonl").write_text("", encoding="utf-8")
        os.symlink(outside / "a.jsonl", self.unit / "tasks.jsonl")
        for relative in ("logs", "logs/a.jsonl", "tasks.jsonl"):
            with self.subTest(relative=relative), self.assertRaises(paths.Refused) as caught:
                unit.target(relative)
            self.assertIn("symlink", str(caught.exception))
        with self.assertRaises(paths.Refused):
            paths.append_line(unit, "tasks.jsonl", b"{}\n")
        with self.assertRaises(paths.Refused):
            paths.write_atomic(unit, "logs/b.json", b"{}")
        self.assertEqual(sorted(p.name for p in outside.iterdir()), ["a.jsonl"])
        self.assertEqual((outside / "a.jsonl").read_text(), "")

    def test_s21_a_symlinked_unit_or_skill_folder_is_refused(self):
        real = self.repo / "real"
        real.mkdir()
        (real / "code.json").write_text("{}", encoding="utf-8")
        os.symlink(real, self.repo / ".code" / "linked")
        self.refused(str(self.repo / ".code" / "linked"), "symlink")

    def test_s22_names_that_become_paths_are_checked_before_a_path_is_built(self):
        for bad in ("../x", "A", "a b", "", "a/b", "-a", "1a", "a_b", "a\n"):
            with self.subTest(bad=bad), self.assertRaises(paths.Refused):
                paths.check_agent(bad)
        for bad in ("a\n", "x/y", ""):
            with self.subTest(slug=bad), self.assertRaises(paths.Refused):
                paths.check_slug(bad)
        for bad in ("../x", "user", "user\n", "A", ""):
            with self.subTest(by=bad), self.assertRaises(paths.Refused):
                paths.check_by(bad)
        self.assertEqual(paths.check_by("builder-t1"), "builder-t1")
        self.assertEqual(paths.check_slug("a-1"), "a-1")
        with self.assertRaises(paths.Refused):
            paths.check_pattern("T1x", r"T\d+", "id")

    def test_s23_files_are_written_through_exclusive_temp_files_and_nofollow_opens(self):
        unit = self.resolve(str(self.unit))
        paths.write_atomic(unit, "a.json", b'{"a": 1}')
        paths.write_atomic(unit, "a.json", b'{"a": 2}')
        self.assertEqual(paths.read_bytes(unit, "a.json"), b'{"a": 2}')
        self.assertEqual([p.name for p in self.unit.iterdir() if p.name.endswith(".tmp")], [])
        paths.append_line(unit, "l.jsonl", b"{}")
        paths.append_line(unit, "l.jsonl", b"{}\n")
        self.assertEqual(paths.read_bytes(unit, "l.jsonl"), b"{}\n{}\n")
        paths.create_exclusive(unit, "e.json", b"1")
        with self.assertRaises(FileExistsError):
            paths.create_exclusive(unit, "e.json", b"2")
        paths.make_folder(unit, "q/r")
        self.assertTrue((self.unit / "q" / "r").is_dir())

    def test_s23_a_symlink_planted_at_a_state_file_or_a_temp_path_is_not_followed(self):
        unit = self.resolve(str(self.unit))
        victim = self.repo / "victim"
        victim.write_text("keep", encoding="utf-8")
        for name in (".server", ".conversation-seen"):
            os.symlink(victim, self.unit / name)
            with self.assertRaises(paths.Refused):
                paths.write_state(unit, name, b"x")
            with self.assertRaises(paths.Refused):
                paths.read_bytes(unit, name)
        with mock.patch.object(paths.secrets, "token_hex", return_value="fixed"):
            os.symlink(victim, self.unit / ".t.json.fixed.tmp")
            with self.assertRaises(paths.Refused):
                paths.write_atomic(unit, "t.json", b"x")
        self.assertEqual(victim.read_text(), "keep")
        self.assertFalse((self.unit / "t.json").exists())

    def test_the_exclude_line_is_added_once_and_never_rewritten(self):
        unit = self.resolve(str(self.unit))
        exclude = self.repo / ".git" / "info" / "exclude"
        exclude.write_text("keep-me", encoding="utf-8")
        self.assertEqual(paths.add_exclude(unit, ".code/"), "added")
        self.assertEqual(paths.add_exclude(unit, ".code/"), "present")
        self.assertEqual(exclude.read_text(encoding="utf-8"), "keep-me\n.code/\n")

    def test_the_exclude_step_is_skipped_outside_a_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            unit = paths.resolve_unit(os.path.join(os.path.realpath(tmp), ".code", "z"), code.SKILL, creating=True)
            os.makedirs(unit.path)
            self.assertTrue(paths.add_exclude(unit, ".code/").startswith("skipped"))
            self.assertEqual(unit.root, Path(os.path.realpath(tmp)))


class Check(Repo):
    def test_a_symlinked_record_file_is_an_error_in_check_as_add_refuses_it(self):
        # L4: one rule in every reader. add and set refuse a symlinked record file; check must not read through it.
        outside = self.repo / "elsewhere.jsonl"
        outside.write_text(jsonl(decision()), encoding="utf-8")
        (self.unit / "decisions.jsonl").symlink_to(outside)
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("decisions.jsonl:1: (file): is a symlink", result.stdout)

    def test_a_reader_says_why_a_file_could_not_be_shown(self):
        from better_ai import paths

        self.assertEqual(paths.reason(paths.Refused("x.jsonl: is a symlink")), "x.jsonl: is a symlink")
        self.assertEqual(paths.reason(ValueError("secret detail")), "ValueError")

    def test_s68_a_hand_written_valid_record_is_accepted(self):
        self.write("decisions.jsonl", jsonl(decision()))
        self.write("tasks.jsonl", "")
        result = self.check()
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_an_invalid_record_is_one_line_and_exit_1(self):
        self.write("decisions.jsonl", jsonl(decision(status="waiting")))
        result = self.check()
        self.assertEqual(result.returncode, 1)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 2, lines)
        self.assertRegex(lines[0], r"^\.code/x/decisions\.jsonl:1: default: required when status is \"waiting\"$")

    def test_s36_an_at_more_than_five_minutes_ahead_is_an_error_with_the_skew_in_the_line(self):
        self.write("decisions.jsonl", jsonl(decision(at=stamp(7)), decision("D2", at=stamp(4))))
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertRegex(
            result.stdout.strip(),
            r"^\.code/x/decisions\.jsonl:1: at: [78] min ahead of this machine's clock \(\d\d:\d\dZ\): "
            r"clock skew or a typed time$",
        )

    def test_s35_each_old_decision_shape_before_the_cutoff_is_reported_not_failed(self):
        old_code = decision(at=OLD, status="waiting")
        old_code_answered = decision("D2", at=OLD, status="answered", answer={"type": "chat", "text": "yes"})
        old_research = {"type": "decision", "at": OLD, "by": "board", "id": "D3", "asked": "q?", "default": "a"}
        old_research.update({"deadline": OLD, "status": "pending"})
        defaulted = dict(old_research, id="D4", status="default")
        changed = dict(old_research, id="D5", status="changed", answer={"type": "chat", "text": "b"})
        self.write("decisions.jsonl", jsonl(old_code, old_code_answered, old_research, defaulted, changed))
        self.write("tasks.jsonl", "")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 5)
        for number, line in enumerate(lines, 1):
            self.assertEqual(
                line,
                f".code/x/decisions.jsonl:{number}: (format): written in the format before this change: kept as is, "
                "not converted",
            )

    def test_s35_the_same_shape_written_after_the_cutoff_is_an_error(self):
        self.write("decisions.jsonl", jsonl(decision(status="waiting")))
        self.assertEqual(self.check().returncode, 1)
        late = {"type": "decision", "at": stamp(), "by": "b", "id": "D1", "asked": "q", "default": "a"}
        late.update({"deadline": stamp(), "status": "pending"})
        self.write("decisions.jsonl", jsonl(late))
        self.assertEqual(self.check().returncode, 1)

    def test_s35_an_old_line_that_is_wrong_in_its_own_way_is_still_an_error(self):
        self.write("decisions.jsonl", jsonl(decision(at=OLD, status="waiting", nonsense=1)))
        self.assertEqual(self.check().returncode, 1)

    def test_a_unit_that_is_not_there_is_refused_with_the_command_to_run(self):
        result = self.check(unit=".code/nope")
        self.assertEqual(result.returncode, 1)
        self.assertIn("run create .code/nope", result.stderr)


STATES = {
    "default": (None, "text", "null"),
    "deadline": (None, "time", "null"),
    "answer": (None, "chat"),
    "decision": (None, "text"),
}
VALUES = {
    "default": {"text": "keep going", "null": None},
    "deadline": {"time": "2026-12-01T10:00:00Z", "null": None},
    "answer": {"chat": {"type": "chat", "text": "yes"}},
    "decision": {"text": "this one"},
}


def expected_ok(status, state):
    """The table of design.md Data, written out once more."""
    default, deadline, answer, decision_ = (state[k] for k in ("default", "deadline", "answer", "decision"))
    if status == "waiting":
        return default and deadline and not answer and not decision_
    if status == "defaulted":
        return default == "text" and deadline == "time" and not answer and not decision_
    if status == "answered":
        return default and deadline and answer and not decision_
    return decision_ and not (default or deadline or answer)


def combinations():
    out = [{}]
    for name, states in STATES.items():
        out = [{**o, name: s} for o in out for s in states]
    return out


class Decisions(Repo):
    def problems(self, record):
        docs = schema.docs_for("code")
        return schema.validate_instance(record, docs["decisions.schema.json"], docs)

    def test_s48_every_status_requires_and_rejects_exactly_the_fields_of_the_table(self):
        cases = [(s, c) for s in ("waiting", "defaulted", "answered", "decided") for c in combinations()]
        for status, state in sweep.cases(cases, key=lambda case: (case[0], expected_ok(*case))):
            record = decision(status=status)
            record.pop("decision", None)
            for name, label in state.items():
                if label is not None:
                    record[name] = VALUES[name][label]
            with self.subTest(status=status, state=state):
                self.assertEqual(not self.problems(record), bool(expected_ok(status, state)), record)

    def test_s48_about_takes_task_change_and_board_and_a_task_must_resolve_in_the_unit(self):
        for about in ({"type": "change"}, {"type": "board"}):
            self.assertEqual(self.problems(decision(about=about)), [])
        self.assertTrue(self.problems(decision(about={"type": "unit"})))
        self.assertTrue(self.problems(decision(about={"type": "task"})))
        self.write("decisions.jsonl", jsonl(decision(about={"type": "task", "task": "T9"})))
        self.assertIn("dangling", self.check().stdout)
        self.write("tasks.jsonl", jsonl(task("T9")))
        self.assertNotIn("decisions.jsonl", self.check().stdout)

    def test_s48_a_task_pointer_fails_on_a_research_board_which_has_no_tasks_file(self):
        board = self.repo / ".research" / "b"
        board.mkdir(parents=True)
        (board / "brief.json").write_text(
            json.dumps({"type": "brief", "at": stamp(), "by": "lead", "question": "q?"}), encoding="utf-8"
        )
        (board / "decisions.jsonl").write_text(jsonl(decision(about={"type": "task", "task": "T1"})), encoding="utf-8")
        result = run("research-better", "check", ".research/b", cwd=self.repo)
        self.assertIn("dangling: tasks.jsonl does not exist", result.stdout)

    def answer_event(self, **fields):
        event = {"type": "answer", "at": stamp(), "by": "user", "id": "m1", "decision": "D1", "text": "yes"}
        event.update({"default": False})
        event.update(fields)
        return event

    def answered(self, event="m1"):
        return decision(status="answered", default=None, deadline=None, answer={"type": "page", "event": event})

    def test_s50_a_page_answer_must_point_to_the_users_answer_event_for_this_decision(self):
        reply = {"type": "reply", "at": stamp(), "by": "coordinator", "id": "m2", "text": "ok", "to": None}
        cases = {
            "the user's answer for this decision": ([self.answer_event()], "m1", True),
            "a reply": ([reply], "m2", False),
            "another decision's answer": ([self.answer_event(decision="D2")], "m1", False),
            "a missing event": ([self.answer_event()], "m9", False),
            "no conversation": ([], "m1", False),
        }
        for name, (events, event, ok) in cases.items():
            with self.subTest(name):
                self.write("decisions.jsonl", jsonl(self.answered(event)))
                self.write("tasks.jsonl", "")
                (self.unit / "conversation.jsonl").unlink(missing_ok=True)
                if events:
                    self.write("conversation.jsonl", jsonl(*events))
                result = self.check()
                self.assertEqual(result.returncode, 0 if ok else 1, result.stdout)

    def test_the_answer_event_type_is_in_the_shared_conversation_schema(self):
        docs = schema.docs_for("show")
        self.assertEqual(schema.validate_instance(self.answer_event(), docs["conversation.schema.json"], docs), [])
        bad = self.answer_event(by="coordinator")
        self.assertTrue(schema.validate_instance(bad, docs["conversation.schema.json"], docs))

    def test_architect_better_keeps_its_own_decision_records(self):
        docs = schema.docs_for("architect")
        self.assertNotIn("raised_by", docs["decisions.schema.json"]["required"])


def task(id):
    return {
        "type": "task",
        "at": stamp(),
        "by": "coordinator",
        "id": id,
        "task": "t",
        "requirements": [],
        "status": "todo",
    }


def id_rules(node):
    """Every `x-id` declaration anywhere in the schemas."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from [value] if key == "x-id" else id_rules(value)
    elif isinstance(node, list):
        for value in node:
            yield from id_rules(value)


class Declarations(unittest.TestCase):
    def test_every_id_declaration_has_a_valid_shape_and_the_hooks_the_schemas_name_exist(self):
        for name, one in SKILLS.items():
            with self.subTest(skill=name):
                docs = schema.docs_for(one.package)
                for rule in id_rules(docs):
                    self.assertTrue(
                        {"prefix"} <= set(rule) or {"prefix_by", "map"} <= set(rule) or rule == {"from": "caller"}
                    )

    def test_a_malformed_x_id_or_x_old_format_is_a_schema_error(self):
        for bad in ({"x-id": {}}, {"x-id": {"prefix": ""}}, {"x-old-format": {}}, {"x-old-format": [1]}):
            with self.subTest(bad=bad), self.assertRaises(schema.SchemaError):
                schema._audit({"type": "object", **bad}, "t")


if __name__ == "__main__":
    unittest.main()
