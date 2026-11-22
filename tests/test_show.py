"""Tests for show-better's package: `create`, `set`, `check` (the digest), `render` in every format, and the live page.

The text, Markdown, screen-reader and page outputs are compared with golden files in `tests/fixtures/show/`, made by
the old `show.py` from the same spec (every kind of slide and template): the move into the package changed none of
them. The live page runs as a real server, as the agent runs it: `serve`, the user sends, `wait`, `reply`, `status`
and `pending`.
"""

import copy
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))
from better import run  # noqa: E402

from better_ai import page, resources  # noqa: E402
from better_ai import show as package  # noqa: E402

GOLD = HERE / "fixtures" / "show"
SKILL = "show-better"
UNIT = ".show/deck"
SPEC = json.loads((GOLD / "all-kinds.spec.json").read_text())
FIELDS = {k: v for k, v in SPEC.items() if k not in ("at", "by")}  # what `create` is given: it stamps `at` and `by`
AT = "2026-11-22T10:00:00Z"
SMALL = {
    "type": "slides",
    "title": "The answer is yes.",
    "question": "Why?",
    "panels": [{"headline": "The slide states one clear point.", "source": "test", "kind": "text", "body": ["One."]}],
}


def repository(root: str) -> str:
    subprocess.run(["git", "init", "-q", root], check=True)
    return root


def better(cwd: str, *args: str, stdin: str | None = None):
    return run(SKILL, *args, stdin=stdin, cwd=cwd)


def made(cwd: str, fields: dict = FIELDS, unit: str = UNIT):
    done = better(cwd, "create", unit, "--by", "tester", stdin=json.dumps(fields))
    assert done.returncode == 0, done.stdout + done.stderr
    return Path(cwd, unit)


class Commands(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = repository(self.tmp.name)

    def test_create_stamps_the_spec_and_keeps_the_unit_out_of_git(self):
        unit = made(self.cwd)
        head = json.loads((unit / "spec.json").read_text())
        self.assertEqual((head["type"], head["by"]), ("slides", "tester"))
        self.assertRegex(head["at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertIn(".show/", Path(self.cwd, ".git", "info", "exclude").read_text())

    def test_create_refuses_a_spec_that_holds_at_or_by(self):
        done = better(self.cwd, "create", UNIT, "--by", "tester", stdin=json.dumps(SPEC))
        self.assertEqual(done.returncode, 1)
        self.assertIn("'at'", done.stderr)

    def test_set_slides_changes_the_spec_and_set_spec_is_not_a_record(self):
        made(self.cwd, SMALL)
        done = better(self.cwd, "set", UNIT, "slides", stdin=json.dumps({"title": "The answer is no."}))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("THE ANSWER IS NO.", better(self.cwd, "render", UNIT, "--format", "text").stdout)
        self.assertEqual(better(self.cwd, "set", UNIT, "spec", stdin="{}").returncode, 1)

    def test_check_prints_the_digest_exactly_as_show_py_did(self):
        made(self.cwd)
        done = better(self.cwd, "check", UNIT)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(done.stdout, (GOLD / "all-kinds.digest.txt").read_text())
        self.assertIn("warning: 26 panels: more than 12", done.stderr)

    def test_render_prints_each_text_format_exactly_as_show_py_did(self):
        made(self.cwd)
        cases = {
            "text": ["--format", "text"],
            "md": ["--format", "md"],
            "ascii": ["--format", "text", "--ascii"],
            "sr": ["--format", "text", "--screen-reader"],
            "w40": ["--format", "text", "--width", "40"],
        }
        for name, flags in cases.items():
            with self.subTest(name):
                done = better(self.cwd, "render", UNIT, *flags)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(done.stdout, (GOLD / f"all-kinds.{name}.txt").read_text())

    def test_render_writes_the_page_inside_the_unit_and_prints_where(self):
        unit = made(self.cwd)
        done = better(self.cwd, "render", UNIT)
        self.assertEqual(done.returncode, 0, done.stderr)
        page_file = unit / "page.html"
        self.assertEqual(done.stdout.strip(), f"wrote {page_file.resolve()}")
        text = page_file.read_text()
        stage = re.search(r'<div class="stage">(.*)</div>\s*</main>', text, re.S).group(1)
        self.assertEqual(stage, (GOLD / "all-kinds.stage.html").read_text())
        self.assertIn('<body class="static">', text)
        self.assertNotIn('id="page-config"', text)  # opened as a file: the slides, without the conversation
        self.assertEqual(sorted(p.name for p in unit.iterdir()), ["page.html", "spec.json"])

    def test_render_refuses_flags_that_do_not_go_together(self):
        made(self.cwd, SMALL)
        for flags in (["--screen-reader"], ["--format", "md", "--screen-reader"]):
            with self.subTest(flags):
                done = better(self.cwd, "render", UNIT, *flags)
                self.assertEqual(done.returncode, 1)
                self.assertIn("--screen-reader works with --format text", done.stderr)
        self.assertEqual(better(self.cwd, "render", UNIT, "--format", "pdf").returncode, 2)
        self.assertEqual(better(self.cwd, "render", UNIT, "--out", "x.html").returncode, 2)

    def test_a_spec_the_drawing_refuses_is_reported_and_nothing_is_written(self):
        deep = {"label": "e", "value": 1}
        for name in "dcba":
            deep = {"label": name, "children": [deep]}
        panel = {"headline": "The slide states one clear point.", "source": "t", "kind": "tree", "root": deep}
        unit = made(self.cwd, {**SMALL, "panels": [panel]})
        for args in (("check", UNIT), ("render", UNIT), ("render", UNIT, "--format", "text")):
            with self.subTest(args):
                done = better(self.cwd, *args)
                self.assertEqual(done.returncode, 1)
                self.assertRegex(done.stdout, r"^\.show/deck/spec\.json:1: .*levels", done.stdout)
        self.assertFalse((unit / "page.html").exists())

    def test_a_shape_error_is_named_by_field_and_prints_no_digest(self):
        bad = {**SMALL, "panels": [{**SMALL["panels"][0], "kind": "bars", "items": [{"label": "a"}]}]}
        unit = made(self.cwd, SMALL)
        (unit / "spec.json").write_text(json.dumps({**json.loads((unit / "spec.json").read_text()), **bad}))
        done = better(self.cwd, "check", UNIT)
        self.assertEqual(done.returncode, 1)
        self.assertIn(".show/deck/spec.json:1: panels[0].items[0].value: required", done.stdout)
        self.assertNotIn("TITLE:", done.stdout)

    def test_a_spec_from_before_at_and_by_is_the_old_format_and_still_works(self):
        unit = Path(self.cwd, UNIT)
        unit.mkdir(parents=True)
        old = {k: v for k, v in SMALL.items() if k != "type"}  # from before `type` existed too
        (unit / "spec.json").write_text(json.dumps(old))
        done = better(self.cwd, "check", UNIT)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("(format): written in the format before this change: kept as is, not converted", done.stdout)
        self.assertIn("TITLE: The answer is yes.", done.stdout)
        self.assertEqual(better(self.cwd, "render", UNIT).returncode, 0)
        self.assertIn("THE ANSWER IS YES.", better(self.cwd, "render", UNIT, "--format", "text").stdout)
        # and it can be changed: `set` with the type the spec says it has
        done = better(self.cwd, "set", UNIT, "slides", stdin=json.dumps({"type": "slides", "title": "A new answer."}))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("A NEW ANSWER.", better(self.cwd, "render", UNIT, "--format", "text").stdout)

    def test_the_checks_across_the_panels_still_apply_to_an_old_format_spec(self):
        unit = Path(self.cwd, UNIT)
        unit.mkdir(parents=True)
        edge = {"from": "a", "to": "zzz", "label": "causes"}
        concept = {
            "headline": "The slide states one clear point.",
            "source": "t",
            "kind": "concept",
            "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
            "edges": [edge],
        }
        (unit / "spec.json").write_text(json.dumps({**SMALL, "panels": [concept]}))
        done = better(self.cwd, "check", UNIT)
        self.assertEqual(done.returncode, 1)
        self.assertIn("panels[0].edges[0].to: names no node id", done.stdout)

    def test_a_spec_after_the_format_change_needs_type_at_and_by(self):
        unit = Path(self.cwd, UNIT)
        unit.mkdir(parents=True)
        (unit / "spec.json").write_text(json.dumps({**SMALL, "at": "2999-01-01T00:00:00Z", "by": "a"}))
        done = better(self.cwd, "check", UNIT)
        self.assertEqual(done.returncode, 1)  # a time ahead of the clock
        (unit / "spec.json").write_text(json.dumps({**SMALL, "at": "2026-11-22T10:00:00Z"}))
        done = better(self.cwd, "check", UNIT)
        self.assertEqual(done.returncode, 1)
        self.assertIn("by: required", done.stdout)


class LivePage(unittest.TestCase):
    """The unit served as a real page: what it sends, what the agent reads, and what the agent answers."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = repository(self.tmp.name)
        self.unit = made(self.cwd, SMALL)
        env = {**os.environ, "BETTER_AI_SKILL": SKILL}
        from better import command

        self.server = subprocess.Popen(
            [*command("serve", UNIT, "--no-browser")],
            cwd=self.cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for _ in range(100):
            if (self.unit / ".server").exists():
                break
            time.sleep(0.1)
        self.base = (self.unit / ".server").read_text().strip().rstrip("/")
        self.addCleanup(self.stop)

    def stop(self):
        if self.server.poll() is None:
            self.server.send_signal(signal.SIGTERM)  # as a harness ends a command
        self.server.communicate(timeout=10)

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=5) as r:
            return r.status, r.read().decode()

    def send(self, method, params):
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        headers = {"Content-Type": "application/json", "Origin": self.base}
        request = urllib.request.Request(self.base + "/rpc", data=json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(request, timeout=5) as r:
            return json.loads(r.read())

    def test_the_shell_carries_the_pages_files_and_nothing_else_is_served(self):
        status, shell = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn('<link href="/show.css" rel="stylesheet">', shell)
        self.assertIn('<script src="/show.js"></script>', shell)
        self.assertIn('<div class="stage"></div>', shell)  # the slides come from /data
        for path in ("/show.js", "/show.css", "/page.js", "/page.css"):
            self.assertEqual(self.get(path)[0], 200, path)
        for path in ("/spec.json", "/page.html", "/../spec.json", "/show.html"):
            with self.assertRaises(urllib.error.HTTPError, msg=path) as caught:
                self.get(path)
            self.assertEqual(caught.exception.code, 404, path)

    def test_data_is_the_slides_drawn_from_the_spec_and_rev_follows_the_spec(self):
        data = json.loads(self.get("/data")[1])
        self.assertEqual((data["title"], data["question"], data["lang"]), ("The answer is yes.", "Why?", "en"))
        self.assertEqual(data["slides"].count('<section class="slide'), 2)  # the opening slide and the panel
        _, before = self.get("/rev")
        done = better(self.cwd, "set", UNIT, "slides", stdin=json.dumps({"title": "The answer is no."}))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertNotEqual(self.get("/rev")[1], before)
        self.assertEqual(json.loads(self.get("/data")[1])["title"], "The answer is no.")

    def test_a_spec_that_fails_its_checks_is_shown_as_its_errors(self):
        text = json.loads((self.unit / "spec.json").read_text())
        text["panels"][0]["kind"] = "bars"
        (self.unit / "spec.json").write_text(json.dumps(text))
        data = json.loads(self.get("/data")[1])
        self.assertTrue(data["errors"])
        self.assertNotIn("slides", data)

    def test_the_user_sends_and_the_agent_waits_replies_marks_and_lists(self):
        slide = {"on": {"slide": 1, "part": None}}
        self.assertEqual(self.send("note", {"id": "m1", "text": "hi", "to": None, **slide})["result"], "saved")
        agent = ("-I",)
        self.assertEqual(agent, ("-I",))
        done = better(self.cwd, "wait", UNIT, "--timeout", "10")
        self.assertEqual(json.loads(done.stdout.splitlines()[0])["id"], "m1", done.stdout + done.stderr)
        done = better(self.cwd, "reply", UNIT, "--to", "m1", stdin="ok")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(better(self.cwd, "status", UNIT, "done", "m1").returncode, 0)
        self.assertEqual(better(self.cwd, "pending", UNIT).stdout.strip(), "0 not done.")
        done = better(self.cwd, "status", UNIT, "accepted", "m1", "--text", stdin="good")
        self.assertEqual(done.returncode, 0, done.stderr)
        log = [json.loads(x) for x in (self.unit / "conversation.jsonl").read_text().splitlines()]
        self.assertEqual([e["type"] for e in log][-1], "accepted")

    def test_the_pages_events_are_accepted_and_what_its_schema_forbids_is_refused(self):
        comment = {
            "id": "c1",
            "n": 1,
            "text": "which source?",
            "on": {"slide": 2, "part": "headline", "headline": "H", "target": {}, "spot": {"fx": 0.1, "fy": 0.2}},
        }
        for method, params in (
            ("comment", comment),
            ("note", {"id": "m1", "text": "hi", "to": None, "on": {"slide": 2, "part": "Does it arrive?"}}),
            ("delete", {"to": "c1"}),
            ("accept", {"to": "c1"}),
            ("reopen", {"to": "c1", "text": "still wrong"}),
        ):
            with self.subTest(method):
                self.assertEqual(self.send(method, params).get("result"), "saved")
        refused = self.send("comment", {**comment, "on": {"part": "headline"}})
        self.assertEqual(refused["error"]["code"], -32602)
        self.assertIn("slide", refused["error"]["message"])
        self.assertEqual(
            self.send("note", {"id": "m2", "text": "x", "to": None, "by": "agent"})["error"]["code"], -32602
        )
        self.assertEqual(self.send("answer", {"id": "a1", "text": "x"})["error"]["code"], -32601)  # no decisions here
        types = [json.loads(x)["type"] for x in (self.unit / "conversation.jsonl").read_text().splitlines()]
        self.assertEqual(types, ["comment", "note", "delete", "accept", "reopen"])
        done = better(self.cwd, "check", UNIT)  # the log is valid next to the spec
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_ending_the_server_removes_the_address(self):
        self.stop()
        self.assertFalse((self.unit / ".server").exists())


class OnceAndRegistry(unittest.TestCase):
    def test_serve_once_answers_one_request_and_exits(self):
        with tempfile.TemporaryDirectory() as d:
            repository(d)
            unit = made(d, SMALL)
            from better import command

            env = {**os.environ, "BETTER_AI_SKILL": SKILL}
            server = subprocess.Popen(
                command("serve", UNIT, "--no-browser", "--once"),
                cwd=d,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            line = server.stdout.readline()
            url = re.search(r"http://\S+/", line).group(0)
            with urllib.request.urlopen(url, timeout=5) as r:
                self.assertEqual(r.status, 200)
            self.assertEqual(server.wait(timeout=10), 0)
            self.assertFalse((unit / ".server").exists())

    def test_the_page_is_registered_with_bundled_files_and_the_events_of_pins_and_accept(self):
        spec = page.spec_of(package.SKILL)
        self.assertEqual(set(spec.sendable()), {"note", "comment", "delete", "accept", "reopen"})
        self.assertEqual(set(spec.tracked()), {"note", "comment"})
        for name in ("show/main.html", "show/show.js", "show/show.css", "show/page.html"):
            self.assertTrue(resources.exists(name), name)

    def test_the_skill_text_names_the_head_type_set_takes(self):
        for name in ("SKILL.md", "formats/spec.md"):
            text = (ROOT / "skills" / "show-better" / name).read_text()
            self.assertIn("better.pyz set .show/", text)
            self.assertNotRegex(text, r"better\.pyz set \.show/\S+ spec\b")


def whole_numbers(spec):
    """Each place of a spec that holds a whole number, as (the path to its holder, its key)."""
    found, pending = [], [(spec, ())]
    while pending:
        item, path = pending.pop()
        pairs = item.items() if isinstance(item, dict) else enumerate(item) if isinstance(item, list) else ()
        for key, child in pairs:
            if isinstance(child, int) and not isinstance(child, bool):
                found.append((path, key))
            else:
                pending.append((child, (*path, key)))
    return found


class NeverRaises(unittest.TestCase):
    """Whatever a unit holds, the commands answer with lines and an exit code, never a traceback or a bug line."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = repository(self.tmp.name)

    def unit_with(self, spec_text: str, log: str | None = None) -> Path:
        unit = Path(self.cwd, UNIT)
        unit.mkdir(parents=True, exist_ok=True)
        (unit / "spec.json").write_text(spec_text, encoding="utf-8")
        if log is not None:
            (unit / "conversation.jsonl").write_text(log, encoding="utf-8")
        return unit

    def test_a_lone_surrogate_anywhere_in_a_spec_is_a_spec_error(self):
        import sweep

        places = []
        pending = [(SPEC, ())]
        while pending:
            item, path = pending.pop()
            pairs = item.items() if isinstance(item, dict) else enumerate(item) if isinstance(item, list) else ()
            for key, child in pairs:
                places.append((path, key, isinstance(child, str)))
                pending.append((child, (*path, key)))
        for path, key, is_text in sweep.cases(places, key=lambda p: (p[1] if isinstance(p[1], str) else "n", p[2])):
            changed = copy.deepcopy(SPEC)
            holder = changed
            for step in path:
                holder = holder[step]
            if is_text:
                holder[key] = holder[key] + "\ud800"
            elif isinstance(holder, dict):
                holder["\ud800"] = 1
            else:
                continue
            with self.subTest(place=(*path, key)):
                self.unit_with(json.dumps(changed))
                done = better(self.cwd, "check", UNIT)
                self.assertEqual(done.returncode, 1, done.stderr[-300:])
                self.assertNotIn("bug in better.pyz", done.stderr)

    def test_a_deeply_nested_spec_or_log_is_an_answer_not_a_traceback(self):
        for depth in (300, 950, 5000):
            for nested in ("[" * depth + "]" * depth, '{"a":' * depth + "1" + "}" * depth):
                panel = {"headline": "A clear point here.", "kind": "text", "body": ["x"]}
                where = {"document": "@@", "title": "T", "panels": [panel]}
                text = json.dumps({"type": "slides", "at": AT, "by": "a", **where}).replace('"@@"', nested)
                log = '{"type":"note","id":"m-1","text":' + nested + "}\n"
                with self.subTest(depth=depth, shape=nested[:2]):
                    self.unit_with(text, log)
                    for args in (
                        ("check", UNIT),
                        ("render", UNIT),
                        ("render", UNIT, "--format", "text"),
                        ("pending", UNIT),
                    ):
                        done = better(self.cwd, *args)
                        self.assertNotIn("Traceback", done.stderr)
                        self.assertNotIn("bug in better.pyz", done.stderr, args)

    def test_the_files_of_a_unit_that_are_not_what_they_should_be(self):
        for name, content in (("not json", "{"), ("binary", "\x00\xff"), ("empty", ""), ("a list", "[]")):
            with self.subTest(name):
                self.unit_with(content)
                for args in (("check", UNIT), ("render", UNIT), ("render", UNIT, "--format", "md")):
                    done = better(self.cwd, *args)
                    self.assertEqual(done.returncode, 1, (args, done.stdout, done.stderr))
                    self.assertNotIn("bug in better.pyz", done.stderr)

    def test_a_spec_that_check_accepts_with_a_whole_number_made_a_float_renders(self):
        for path, key in whole_numbers(SPEC):
            if path[:1] == ("at",) or key in ("at", "by"):
                continue
            changed = copy.deepcopy(SPEC)
            holder = changed
            for step in path:
                holder = holder[step]
            holder[key] = float(holder[key])
            with self.subTest(place=(*path, key)):
                self.unit_with(json.dumps(changed))
                if better(self.cwd, "check", UNIT).returncode == 0:  # check accepts it: the renderer must take it
                    for flags in ((), ("--format", "text")):
                        done = better(self.cwd, "render", UNIT, *flags)
                        self.assertEqual(done.returncode, 0, done.stderr[-300:])


class Scripts(unittest.TestCase):
    def test_the_javascript_parses(self):
        node = subprocess.run(["node", "--version"], capture_output=True)
        if node.returncode:
            self.skipTest("node is not installed")
        done = subprocess.run(
            ["node", "--check", str(ROOT / "src/better_ai/show/show.js")], capture_output=True, text=True
        )
        self.assertEqual(done.returncode, 0, done.stderr)


if __name__ == "__main__":
    unittest.main()
