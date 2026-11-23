"""The data behind code-better's task timeline: the round and fix records, the task title limit, the time a task's
status changed, and the git activity of each task's branch (design: .design/code-better-board/design.md, D1–D4)."""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from better import run as better  # noqa: E402
from test_dashboard_formats import card, change, check, check_record, load, log, task, write  # noqa: E402

AT = "2026-11-21T10:00:00Z"


def round_record(task_id="T1", **more):
    return {
        "type": "round",
        "at": AT,
        "by": "coordinator",
        "task": task_id,
        "round": 1,
        "verifier": "verifier-t1",
        "findings": [{"text": "Empty export writes no header row", "blocking": True}],
        **more,
    }


def fix_record(task_id="T1", **more):
    return {"type": "fix", "at": AT, "by": "coordinator", "task": task_id, "text": "renamed the flag", **more}


def git(cwd, *args, env=None):
    full = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
        **(env or {}),
    }
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True, env=full)


def iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


class RoundAndFixRecords(unittest.TestCase):
    def test_a_round_and_a_fix_validate(self):
        self.assertEqual(check_record(round_record(), ["rounds.schema.json"]), [])
        self.assertEqual(check_record(fix_record(), ["rounds.schema.json"]), [])

    def test_a_round_needs_its_findings_each_with_text_and_blocking(self):
        self.assertNotEqual(check_record(round_record(findings=[]), ["rounds.schema.json"]), [])
        self.assertNotEqual(check_record(round_record(findings=[{"text": "x"}]), ["rounds.schema.json"]), [])
        self.assertNotEqual(check_record(round_record(round=0), ["rounds.schema.json"]), [])

    def test_a_round_for_a_task_that_does_not_exist_is_dangling(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            write(folder, "rounds.jsonl", [round_record("T9"), fix_record("T8")])
            found = [(e.line, e.field) for e in check(folder)]
            self.assertIn((1, "task"), found)
            self.assertIn((2, "task"), found)

    def test_add_writes_a_round_to_rounds_jsonl(self):
        with tempfile.TemporaryDirectory() as d:
            change(Path(d))
            fields = {k: v for k, v in round_record().items() if k not in ("type", "at", "by")}
            done = better(
                "code-better", "add", ".code/c", "round", "--by", "coordinator", stdin=json.dumps(fields), cwd=d
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            line = json.loads((Path(d) / ".code/c/rounds.jsonl").read_text().splitlines()[0])
            self.assertEqual((line["type"], line["round"], line["findings"][0]["blocking"]), ("round", 1, True))


class TaskTitle(unittest.TestCase):
    def test_a_title_of_40_characters_passes_and_41_is_refused(self):
        self.assertEqual(check_record(task("T1", task="x" * 40), ["tasks.schema.json"]), [])
        self.assertIn("task", [f for f, _ in check_record(task("T1", task="x" * 41), ["tasks.schema.json"])])

    def test_add_refuses_a_long_title(self):
        with tempfile.TemporaryDirectory() as d:
            change(Path(d))
            fields = {k: v for k, v in task("T2", task="y" * 41).items() if k not in ("type", "at", "by", "id")}
            done = better(
                "code-better", "add", ".code/c", "task", "--by", "coordinator", stdin=json.dumps(fields), cwd=d
            )
            self.assertNotEqual(done.returncode, 0)
            self.assertIn("task", done.stdout + done.stderr)


class StatusTime(unittest.TestCase):
    def test_set_stamps_status_at_when_the_status_changes_and_only_then(self):
        with tempfile.TemporaryDirectory() as d:
            change(Path(d), tasks=[task("T1", status="building")])
            path = Path(d) / ".code/c/tasks.jsonl"
            done = better("code-better", "set", ".code/c", "T1", stdin='{"status": "verifying"}', cwd=d)
            self.assertEqual(done.returncode, 0, done.stderr)
            first = json.loads(path.read_text())
            self.assertRegex(first.get("status_at", ""), r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
            self.assertEqual(first["at"], AT)  # the record's own time stays the time it was added
            done = better("code-better", "set", ".code/c", "T1", stdin='{"check": "uv run pytest -k upload"}', cwd=d)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(json.loads(path.read_text())["status_at"], first["status_at"])

    def test_status_at_is_stamped_by_the_command_not_given(self):
        self.assertEqual(check_record(task("T1", status_at=AT), ["tasks.schema.json"]), [])


class TimelineData(unittest.TestCase):
    def test_the_page_gets_rounds_fixes_and_the_earliest_time_of_the_change(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d), tasks=[task("T1", status="building")])
            write(folder, "rounds.jsonl", [round_record(), fix_record()])
            write(folder, "logs/builder-t1.card.json", [card("builder", "T1", at="2026-11-21T09:00:00Z")], as_json=True)
            write(folder, "logs/builder-t1.jsonl", [log("start", "builder-t1", at="2026-11-21T09:01:00Z")])
            shown = load(folder)
            self.assertEqual([r["round"] for r in shown["rounds"]], [1])
            self.assertEqual([f["text"] for f in shown["fixes"]], ["renamed the flag"])
            self.assertEqual(shown["start"], "2026-11-21T09:00:00Z")
            self.assertEqual(shown["agents"][0]["lines"][0]["at"], "2026-11-21T09:01:00Z")
            self.assertEqual(shown["agents"][0]["at"], "2026-11-21T09:00:00Z")  # when its card was added

    def test_git_activity_of_a_branch_comes_in_5_minute_buckets_since_its_card_with_uncommitted_changes(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            git(repo, "init", "-q", "-b", "main")
            (repo / "a.py").write_text("x = 1\n")
            git(repo, "add", "a.py")
            now = int(time.time())
            old = f"{now - 7200} +0000"  # the base is older than the card: only the task's own work counts
            git(repo, "commit", "-q", "-m", "base", env={"GIT_AUTHOR_DATE": old, "GIT_COMMITTER_DATE": old})
            card_at = now - 1800
            git(repo, "branch", "task/t1")
            tree = repo / ".claude-wt"
            git(repo, "worktree", "add", "-q", str(tree), "task/t1")
            (tree / "b.py").write_text("".join(f"line{i}\n" for i in range(10)))
            git(tree, "add", "b.py")
            stamp = str(now - 900)
            git(
                tree,
                "commit",
                "-q",
                "-m",
                "ten lines",
                env={"GIT_AUTHOR_DATE": f"{stamp} +0000", "GIT_COMMITTER_DATE": f"{stamp} +0000"},
            )
            (tree / "a.py").write_text("x = 1\ny = 2\nz = 3\n")  # two lines added, not committed
            os.utime(tree / "a.py", (now - 60, now - 60))
            folder = change(repo, tasks=[task("T1", status="building")])
            write(
                folder,
                "logs/builder-t1.card.json",
                [card("builder", "T1", branch="task/t1", at=iso(card_at))],
                as_json=True,
            )
            shown = load(folder)["git"]["task/t1"]
            buckets = dict((start, n) for start, n in shown["buckets"])
            self.assertEqual(buckets.get((now - 900) // 300 * 300), 10)
            self.assertEqual(buckets.get((now - 60) // 300 * 300), 2)
            self.assertEqual((shown["commits"], shown["added"], shown["removed"], shown["files"]), (1, 12, 0, 2))
            self.assertEqual(shown["last"], now - 60)

    def test_a_branch_git_cannot_read_has_no_git_data_and_no_error(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d), tasks=[task("T1", status="building")])
            write(folder, "logs/builder-t1.card.json", [card("builder", "T1", branch="no/such")], as_json=True)
            shown = load(folder)
            self.assertNotIn("no/such", shown["git"])
            self.assertEqual(shown["errors"], [])


if __name__ == "__main__":
    unittest.main()


class FoundByTheVerifier(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.now = int(time.time())
        old = f"{self.now - 7200} +0000"
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "a.py").write_text("x = 1\n")
        git(self.repo, "add", "a.py")
        git(self.repo, "commit", "-q", "-m", "base", env={"GIT_AUTHOR_DATE": old, "GIT_COMMITTER_DATE": old})

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_change_folder_is_not_the_tasks_work(self):
        from better_ai.code import activity

        records = self.repo / ".code" / "c"
        records.mkdir(parents=True)
        (records / "tasks.jsonl").write_text("".join("{}\n" for _ in range(50)))
        found = activity.branch_activity(self.repo, "main", self.now - 3600)
        self.assertEqual((found["files"], found["added"]), (0, 0))

    def test_a_commit_authored_before_the_card_does_not_count_after_a_rebase(self):
        from better_ai.code import activity

        authored, committed = f"{self.now - 3000} +0000", f"{self.now - 60} +0000"  # a rebase keeps the author date
        (self.repo / "b.py").write_text("y = 2\n")
        git(self.repo, "add", "b.py")
        git(
            self.repo,
            "commit",
            "-q",
            "-m",
            "older work",
            env={"GIT_AUTHOR_DATE": authored, "GIT_COMMITTER_DATE": committed},
        )
        found = activity.branch_activity(self.repo, "main", self.now - 1800)
        self.assertEqual((found["commits"], found["added"]), (0, 0))

    def test_add_refuses_a_typed_status_at(self):
        change(self.repo)
        fields = {k: v for k, v in task("T2", status_at=AT).items() if k not in ("type", "at", "by", "id")}
        done = better(
            "code-better", "add", ".code/c", "task", "--by", "coordinator", stdin=json.dumps(fields), cwd=self.repo
        )
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("status_at", done.stdout + done.stderr)
