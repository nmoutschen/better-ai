"""design-better as a unit: `create`, `check`, `set`, `render`, `serve` and the page's events, from src/better_ai/design/.

Run with `python3 -m unittest tests.test_design_unit`. No test opens a browser.
"""

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import better  # noqa: E402

SKILL = "design-better"
HEAD = {
    "title": "Pay screen",
    "question": "Which one?",
    "widths": ["1280x800", "375"],
    "versions": [{"label": "A", "file": "a.html"}, {"label": "B", "file": "b.html"}],
}


def run(repo, *args, stdin=None):
    return better.run(SKILL, *args, stdin=stdin, cwd=repo, env={"PYTHONUNBUFFERED": "1"})


def make_repo(root: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    folder = root / ".design" / "pay"
    folder.mkdir(parents=True)
    (folder / "a.html").write_text('<h1 id="a">A</h1><img src="p.png"><link rel="stylesheet" href="s.css">')
    (folder / "b.html").write_text("<h1>B</h1><a href='other.html'>x</a>")
    (folder / "s.css").write_text("body{background:url(p.png)}")
    (folder / "p.png").write_bytes(b"\x89PNG-not-really")
    (folder / "brief.md").write_text("# Brief\n")
    return folder


class Unit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.folder = make_repo(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def create(self, head=None):
        return run(self.root, "create", ".design/pay", "--by", "designer", stdin=json.dumps(head or HEAD))

    def test_create_writes_the_head_and_keeps_the_agents_files(self):
        before = {p.name: p.read_bytes() for p in self.folder.iterdir()}
        done = self.create()
        self.assertEqual(done.returncode, 0, done.stderr)
        head = json.loads((self.folder / "canvas.json").read_text())
        self.assertEqual((head["type"], head["by"], head["title"]), ("canvas", "designer", "Pay screen"))
        self.assertRegex(head["at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        for name, data in before.items():
            self.assertEqual((self.folder / name).read_bytes(), data)
        self.assertEqual(run(self.root, "check", ".design/pay").returncode, 0)

    def test_create_refuses_a_second_time_and_a_bad_head(self):
        self.assertEqual(self.create().returncode, 0)
        self.assertEqual(self.create().returncode, 1)

    def test_check_names_each_problem_of_the_versions(self):
        cases = {
            "versions/1/label": {"versions": [{"label": "A", "file": "a.html"}, {"label": "A", "file": "b.html"}]},
            "versions/0/file": {"versions": [{"label": "A", "file": "nope.html"}]},
            "widths[0]": {"widths": ["wide"]},
            "versions": {"versions": []},
        }
        for field, change in cases.items():
            with self.subTest(field=field):
                done = self.create({**HEAD, **change})
                self.assertEqual(done.returncode, 1)
                self.assertIn(field, done.stdout + done.stderr)
                self.assertFalse((self.folder / "canvas.json").exists())
        both = {"versions": [{"label": "A", "file": "a.html", "address": "https://example.com/"}]}
        self.assertEqual(self.create({**HEAD, **both}).returncode, 1)
        outside = {"versions": [{"label": "A", "file": "../x.html"}]}
        self.assertEqual(self.create({**HEAD, **outside}).returncode, 1)

    def test_a_version_may_not_be_index_html_which_render_writes(self):
        (self.folder / "index.html").write_text("<p>my own page</p>")
        head = {**HEAD, "versions": [{"label": "A", "file": "index.html"}, {"label": "B", "file": "b.html"}]}
        done = self.create(head)
        self.assertEqual(done.returncode, 1)
        self.assertIn("index.html is the compare page render writes", done.stdout + done.stderr)
        # set and check refuse it too, and render never overwrites the file
        self.create()
        done = run(self.root, "set", ".design/pay", "canvas", stdin=json.dumps({"versions": head["versions"]}))
        self.assertEqual(done.returncode, 1)
        (self.folder / "canvas.json").write_text(
            json.dumps({"type": "canvas", "at": better.AFTER_CUTOFF, "by": "x", **head})
        )
        self.assertEqual(run(self.root, "check", ".design/pay").returncode, 1)
        done = run(self.root, "render", ".design/pay")
        self.assertEqual(done.returncode, 1)
        self.assertIn("index.html", done.stderr)
        self.assertEqual((self.folder / "index.html").read_text(), "<p>my own page</p>")

    def test_a_version_whose_name_differs_from_index_html_only_by_case_is_refused(self):
        # On a case-insensitive file system (macOS by default) Index.html and index.html are one file.
        for name in ("Index.html", "INDEX.HTML"):
            with self.subTest(name=name):
                head = {**HEAD, "versions": [{"label": "A", "file": name}, {"label": "B", "file": "b.html"}]}
                done = self.create(head)
                self.assertEqual(done.returncode, 1)
                self.assertIn("index.html is the compare page render writes", done.stdout + done.stderr)

    def test_a_version_may_not_be_a_state_file_of_the_live_page_in_any_case(self):
        for name in ("conversation.jsonl", "Conversation.JSONL", ".server", ".Conversation-Seen"):
            with self.subTest(name=name):
                head = {**HEAD, "versions": [{"label": "A", "file": name}, {"label": "B", "file": "b.html"}]}
                done = self.create(head)
                self.assertEqual(done.returncode, 1)
                self.assertIn("one of the live page's own files", done.stdout + done.stderr)
                self.assertFalse((self.folder / "canvas.json").exists())

    def test_a_symlinked_version_is_refused_by_check_as_render_refuses_it(self):
        (self.folder / "link.html").symlink_to(self.folder / "a.html")
        head = {**HEAD, "versions": [{"label": "A", "file": "link.html"}, {"label": "B", "file": "b.html"}]}
        done = self.create(head)
        self.assertEqual(done.returncode, 1)
        self.assertIn("is a symlink: copy the file into the unit", done.stdout + done.stderr)
        self.create()
        (self.folder / "canvas.json").write_text(
            json.dumps({"type": "canvas", "at": better.AFTER_CUTOFF, "by": "x", **head})
        )
        self.assertEqual(run(self.root, "check", ".design/pay").returncode, 1)

    def test_render_over_malformed_heads_never_shows_a_traceback(self):
        heads = [
            "[]",
            "not json",
            "",
            '{"versions": 5, "widths": "x", "title": 3}',
            '{"versions": [5, {"label": 1}, {"label": "A", "file": 5}, {"label": "B", "file": "../x"}, {"label": "C"}]}',
            r'{"versions": [{"label": "A\ud800", "file": "a\ud800.html"}], "title": "\ud800", "question": "\ud800"}',
            '{"versions": [{"label": "A", "file": "' + "a/" * 300 + 'x.html"}]}',
            "[" * 50000,
        ]
        for text in heads:
            with self.subTest(head=text[:40]):
                (self.folder / "canvas.json").write_text(text)
                done = run(self.root, "render", ".design/pay")
                self.assertNotIn("Traceback", done.stderr)
                self.assertLess(done.returncode, 5, done.stderr)

    def test_set_canvas_changes_the_versions(self):
        self.create()
        (self.folder / "c.html").write_text("<p>C</p>")
        versions = [*HEAD["versions"], {"label": "C", "file": "c.html"}]
        done = run(self.root, "set", ".design/pay", "canvas", stdin=json.dumps({"versions": versions}))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len(json.loads((self.folder / "canvas.json").read_text())["versions"]), 3)

    def test_render_writes_one_file_with_the_data_and_prints_its_path(self):
        self.create()
        done = run(self.root, "render", ".design/pay")
        self.assertEqual(done.returncode, 0, done.stderr)
        page = self.folder / "index.html"
        self.assertEqual(Path(done.stdout.strip()).resolve(), page.resolve())
        text = page.read_text()
        data = json.loads(re.search(r'id="page-data">(.*?)</script>', text, re.S).group(1))
        self.assertEqual([v["label"] for v in data["versions"]], ["A", "B"])
        self.assertEqual(
            [(s["w"], s["h"], s["name"]) for s in data["sizes"]], [(1280, 800, "Desktop"), (375, 700, "Mobile")]
        )
        self.assertIn("data:image/png;base64,", data["versions"][0]["srcdoc"])  # p.png is embedded
        self.assertIn("data:text/css", data["versions"][0]["srcdoc"])
        self.assertIn("href='other.html'", data["versions"][1]["srcdoc"])  # a link to another page stays
        self.assertNotIn('src="/', text)  # no served path: the file stands alone
        self.assertNotIn('href="/page.css"', text)

    def test_render_warns_about_an_address_and_a_link_it_cannot_embed(self):
        (self.folder / "a.html").write_text('<img src="missing.png">')
        self.create(
            {**HEAD, "versions": [{"label": "A", "file": "a.html"}, {"label": "B", "address": "https://example.com/x"}]}
        )
        done = run(self.root, "render", ".design/pay")
        self.assertEqual(done.returncode, 0)
        self.assertIn("missing.png", done.stderr)
        self.assertIn("example.com", done.stderr)

    def test_a_script_in_a_version_cannot_end_the_page_data(self):
        (self.folder / "a.html").write_text("<script>alert(1)</script><p>&amp;</p>")
        self.create()
        run(self.root, "render", ".design/pay")
        text = (self.folder / "index.html").read_text()
        data = text.split('id="page-data">', 1)[1].split("</script>", 1)[0]
        self.assertNotIn("<", data)

    def test_render_without_a_head_says_how_to_make_one(self):
        done = run(self.root, "render", ".design/pay")
        self.assertEqual(done.returncode, 1)
        self.assertIn("create", done.stderr)

    def test_the_skill_has_render_and_the_shared_verbs_only(self):
        done = run(self.root, "--help")
        for verb in ("create", "add", "set", "check", "serve", "wait", "reply", "status", "pending", "render"):
            self.assertIn(verb, done.stdout)
        self.assertNotRegex(done.stdout, r"(?m)^    show\b")


class Script(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_canvas_js_is_valid_javascript_and_has_no_decide(self):
        path = Path(__file__).resolve().parent.parent / "src" / "better_ai" / "design" / "canvas.js"
        self.assertEqual(subprocess.run(["node", "--check", str(path)], capture_output=True).returncode, 0)
        text = path.read_text()
        self.assertNotIn("'decide'", text)
        self.assertIn("pageApprove", text)


class Served(unittest.TestCase):
    """`serve` on a real unit: the page, its data and revision, what the page may send, and the conversation verbs."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.folder = make_repo(self.root)
        done = run(self.root, "create", ".design/pay", "--by", "designer", stdin=json.dumps(HEAD))
        self.assertEqual(done.returncode, 0, done.stderr)
        env = {**os.environ, "BETTER_AI_SKILL": SKILL, "PYTHONUNBUFFERED": "1"}
        self.server = subprocess.Popen(
            better.command("serve", ".design/pay", "--no-browser"),
            cwd=self.root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self.url = re.search(r"http://\S+/", self.server.stdout.readline()).group(
            0
        )  # printed as it happens, on a pipe too

    def tearDown(self):
        self.server.terminate()
        self.server.stdout.close()
        self.server.wait(timeout=20)
        self.tmp.cleanup()

    def get(self, path):
        with urllib.request.urlopen(self.url + path, timeout=10) as r:
            return r.read().decode()

    def send(self, method, params):
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        headers = {"Content-Type": "application/json", "Origin": self.url.rstrip("/")}
        request = urllib.request.Request(self.url + "rpc", data=json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(request, timeout=10) as r:
            return json.loads(r.read())

    def test_the_page_its_data_and_its_assets(self):
        page = self.get("")
        self.assertIn('src="/canvas.js"', page)
        self.assertIn('"approve"', page)
        self.assertNotIn("Pay screen", page)  # the unit's words are data, never markup
        data = json.loads(self.get("data"))
        self.assertEqual(data["title"], "Pay screen")
        self.assertEqual(data["versions"][0]["label"], "A")
        self.assertIn("function boot", self.get("canvas.js"))
        self.assertIn(".approval", self.get("canvas.css"))
        with self.assertRaises(urllib.error.HTTPError) as refused:
            self.get("a.html")  # a version's file is not served: only the fixed table is
        refused.exception.close()

    def test_the_revision_follows_the_head_and_the_version_files(self):
        first = self.get("rev")
        self.assertEqual(self.get("rev"), first)
        (self.folder / "a.html").write_text("<p>changed</p>")
        second = self.get("rev")
        self.assertNotEqual(second, first)
        head = {**HEAD, "title": "New"}
        os.unlink(self.folder / "canvas.json")
        run(self.root, "create", ".design/pay", "--by", "designer", stdin=json.dumps(head))
        self.assertNotEqual(self.get("rev"), second)

    def test_what_the_page_may_send(self):
        on = {"version": "A", "screen": "1280x800", "target": {"selector": "#a"}, "spot": {"fx": 0.5, "fy": 0.5}}
        self.assertEqual(self.send("comment", {"id": "c1", "n": 1, "text": "bigger", "on": on})["result"], "saved")
        self.assertEqual(self.send("verdict", {"version": "A", "verdict": "up"})["result"], "saved")
        approval = {"id": "ap1", "option": "A", "label": "Build A", "carries": ["c1"], "text": None}
        self.assertEqual(self.send("approve", approval)["result"], "saved")
        self.assertEqual(self.send("decide", {**approval, "id": "d1"})["error"]["code"], -32601)  # decide is gone
        self.assertEqual(self.send("approve", {"id": "ap2", "option": "A"})["error"]["code"], -32602)

    ON = {"version": "A", "screen": "1280x800", "target": {"selector": "#a"}, "spot": {"fx": 0.5, "fy": 0.5}}
    EVENTS = {
        "comment": {"id": "c1-x", "n": 1, "text": "too small", "on": ON},
        "note": {"id": "m-x", "text": "hi", "to": None},
        "verdict": {"version": "A", "verdict": "up"},
        "approve": {"id": "ap-x", "option": "A", "label": "Build A", "carries": ["c1-x"], "text": None},
        "delete": {"to": "c1-x"},
        "accept": {"to": "c1-x"},
        "reopen": {"to": "c1-x", "text": "still wrong"},
    }

    def log(self):
        return [json.loads(x) for x in (self.folder / "conversation.jsonl").read_text().splitlines()]

    def test_every_method_the_page_sends_has_a_valid_event_that_is_saved_as_the_users(self):
        for method, params in self.EVENTS.items():
            answer = self.send(method, params)
            self.assertEqual(answer.get("result"), "saved", f"{method}: {answer}")
        events = self.log()
        self.assertEqual([e["type"] for e in events], list(self.EVENTS))
        self.assertEqual({e["by"] for e in events}, {"user"})
        self.assertTrue(all(re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$", e["at"]) for e in events))
        self.assertEqual(run(self.root, "check", ".design/pay").returncode, 0)

    def test_the_log_is_conversation_jsonl_only_and_valid_with_the_agents_replies(self):
        for method, params in self.EVENTS.items():
            self.send(method, params)
        self.assertEqual(run(self.root, "reply", ".design/pay", "--to", "m-x", stdin="seen it").returncode, 0)
        self.assertEqual(run(self.root, "status", ".design/pay", "done", "m-x").returncode, 0)
        done = run(self.root, "status", ".design/pay", "accepted", "m-x", "--text", stdin="fine")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(run(self.root, "check", ".design/pay").returncode, 0)
        for old in ("answers.jsonl", ".answers-seen"):
            self.assertFalse((self.folder / old).exists())

    def test_a_comment_with_no_text_and_no_verdict_is_refused_naming_the_verdict(self):
        answer = self.send("comment", {**self.EVENTS["comment"], "text": None})
        self.assertEqual(answer["error"]["code"], -32602)
        self.assertIn("verdict", answer["error"]["message"])
        self.assertFalse((self.folder / "conversation.jsonl").exists())

    def test_a_verdict_only_comment_is_saved(self):
        thumbs = {**self.EVENTS["comment"], "id": "c2-x", "text": None, "verdict": "up"}
        self.assertEqual(self.send("comment", thumbs).get("result"), "saved")

    def test_a_page_supplied_by_is_rejected(self):
        answer = self.send("note", {**self.EVENTS["note"], "by": "agent"})
        self.assertEqual(answer["error"]["code"], -32602)
        self.assertIn("by", answer["error"]["message"])
        self.assertFalse((self.folder / "conversation.jsonl").exists())

    def test_a_reused_comment_id_is_a_new_version_of_the_comment(self):
        first = self.EVENTS["comment"]
        self.send("comment", first)
        self.send("comment", {**first, "text": "edited"})
        self.assertEqual([e["id"] for e in self.log()], [first["id"]] * 2)
        out = run(self.root, "pending", ".design/pay").stdout
        shown = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
        self.assertEqual([(e["id"], e["text"]) for e in shown], [(first["id"], "edited")])

    def test_sigterm_ends_the_server_and_removes_its_address(self):
        self.assertTrue((self.folder / ".server").exists())
        self.server.send_signal(signal.SIGTERM)
        self.server.wait(timeout=20)
        self.assertFalse((self.folder / ".server").exists())

    def test_the_agent_answers_and_tracks_with_the_shared_verbs(self):
        self.send("note", {"id": "m1", "text": "hello", "to": None})
        waited = run(self.root, "wait", ".design/pay", "--timeout", "10")
        self.assertEqual(json.loads(waited.stdout.splitlines()[0])["id"], "m1")
        self.assertEqual(run(self.root, "reply", ".design/pay", "--to", "m1", stdin="done it").returncode, 0)
        self.assertEqual(run(self.root, "status", ".design/pay", "done", "m1").returncode, 0)
        self.assertEqual(run(self.root, "pending", ".design/pay").returncode, 0)
        done = run(self.root, "status", ".design/pay", "accepted", "m1", "--text", stdin="good")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(run(self.root, "check", ".design/pay").returncode, 0)

    def test_a_head_that_holds_anything_is_still_answered(self):
        heads = [
            "[]",
            "not json",
            '{"versions": 5, "widths": "x", "title": 3}',
            '{"versions": [5, {"label": 1}, {"label": "A", "file": 5}, {"label": "B", "file": "../x"}, {"label": "C"}]}',
            r'{"versions": [{"label": "A\ud800", "file": "a\ud800.html"}], "title": "\ud800"}',
        ]
        for text in heads:
            with self.subTest(head=text):
                (self.folder / "canvas.json").write_text(text)
                self.assertIsInstance(json.loads(self.get("data")), dict)
                self.assertIsInstance(self.get("rev"), str)

    def test_a_head_that_is_gone_is_an_error_the_page_shows(self):
        os.unlink(self.folder / "canvas.json")
        data = json.loads(self.get("data"))
        self.assertIn("create", data["error"])


class Events(unittest.TestCase):
    """The page's log: an `approve` is checked; a `decide` from before the cutoff is old format, one after it is wrong."""

    def log(self, event):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = make_repo(root)
            run(root, "create", ".design/pay", "--by", "designer", stdin=json.dumps(HEAD))
            (folder / "conversation.jsonl").write_text(json.dumps(event) + "\n")
            return run(root, "check", ".design/pay")

    DECIDE = {
        "type": "decide",
        "by": "user",
        "id": "d1",
        "option": "A",
        "label": "Build A",
        "carries": [],
        "text": None,
    }

    def test_an_old_decide_is_a_notice_not_an_error(self):
        done = self.log({**self.DECIDE, "at": "2026-11-01T10:00:00Z"})
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("format", done.stdout)

    def test_a_new_decide_is_refused(self):
        self.assertEqual(self.log({**self.DECIDE, "at": better.AFTER_CUTOFF}).returncode, 1)

    def test_an_approve_is_accepted(self):
        event = {**self.DECIDE, "type": "approve", "at": better.AFTER_CUTOFF}
        self.assertEqual(self.log(event).returncode, 0)


if __name__ == "__main__":
    unittest.main()
