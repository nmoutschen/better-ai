"""design-better as a unit: `create`, `check`, `set`, `render`, `serve` and the page's events, from src/better_ai/design/.

Run with `python3 -m unittest tests.test_design_unit`. No test opens a browser.
"""

import contextlib
import json
import os
import re
import shutil
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


GIT = tempfile.TemporaryDirectory()  # one `git init`, copied into each repository


def setUpModule():
    subprocess.run(["git", "init", "-q", GIT.name], check=True)


def tearDownModule():
    GIT.cleanup()


def run(repo, *args, stdin=None):
    """The command in this process; `better.run` starts one only where a test needs a process. Where the unit is served,
    it runs as the page's own agent: a chat agent may not write there."""
    env = {}
    with contextlib.suppress(OSError, ValueError, KeyError):
        env["BETTER_PAGE_SESSION"] = json.loads((Path(repo) / ".design" / "pay" / ".driver").read_text())["session"]
    return better.call(SKILL, *args, stdin=stdin, cwd=repo, env=env)


def make_repo(root: Path) -> Path:
    shutil.copytree(Path(GIT.name) / ".git", root / ".git")
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

    def test_a_version_may_not_be_a_file_the_page_owns_in_any_case(self):
        # On a case-insensitive file system (macOS by default) Index.html and index.html are one file.
        names = {
            "Index.html": "index.html is the compare page render writes",
            "INDEX.HTML": "index.html is the compare page render writes",
            "conversation.jsonl": "one of the live page's own files",
            "Conversation.JSONL": "one of the live page's own files",
            ".server": "one of the live page's own files",
            ".driver": "one of the live page's own files",
            ".Driver.Log": "one of the live page's own files",
        }
        for name, reason in names.items():
            with self.subTest(name=name):
                head = {**HEAD, "versions": [{"label": "A", "file": name}, {"label": "B", "file": "b.html"}]}
                done = self.create(head)
                self.assertEqual(done.returncode, 1)
                self.assertIn(reason, done.stdout + done.stderr)
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
        done = better.run(SKILL, "render", ".design/pay", cwd=self.root)  # the one process of the unit's verbs
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
        for verb in ("create", "add", "set", "check", "serve", "reply", "status", "pending", "render"):
            self.assertIn(verb, done.stdout)
        self.assertNotRegex(done.stdout, r"(?m)^    show\b")


class Script(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_canvas_js_is_valid_javascript_and_has_no_decide(self):
        path = Path(__file__).resolve().parent.parent / "src" / "better_ai" / "design" / "canvas.js"
        self.assertEqual(subprocess.run(["node", "--check", str(path)], capture_output=True).returncode, 0)
        text = path.read_text()
        self.assertNotIn("'decide'", text)
        self.assertIn("pageApprovalPanel", text)  # the Approve… panel is page.js's, shared with architect-better
        self.assertIn("pagePinCss", text)  # the frame's pin colours are page.css's table


def serve(root: Path) -> tuple:
    """A `serve` on the unit .design/pay of `root`: its address and the secret of a paired tab."""
    return better.serve_page(SKILL, root / ".design" / "pay", "--linger", "0.2", cwd=root)


def stop(root: Path):
    better.stop_page(root / ".design" / "pay")


class Served(unittest.TestCase):
    """`serve` on a real unit: the page, its data and revision, what the page may send, and the conversation verbs.
    One server serves the class; each test starts from the unit as `create` left it."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.folder = make_repo(cls.root)
        done = run(cls.root, "create", ".design/pay", "--by", "designer", stdin=json.dumps(HEAD))
        assert done.returncode == 0, done.stderr
        cls.files = {p.name: p.read_bytes() for p in cls.folder.iterdir()}
        cls.url, cls.token = serve(cls.root)

    @classmethod
    def tearDownClass(cls):
        stop(cls.root)
        cls.tmp.cleanup()

    def setUp(self):
        for path in self.folder.iterdir():
            if path.name not in self.files and not path.name.startswith((".driver", ".server", ".page", ".gitignore")):
                path.unlink()
        for name, data in self.files.items():
            (self.folder / name).write_bytes(data)

    def get(self, path):
        with urllib.request.urlopen(
            urllib.request.Request(self.url + path, headers=better.page_headers(self.token)), timeout=10
        ) as r:
            return r.read().decode()

    def send(self, method, params):
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        headers = {"Content-Type": "application/json", **better.page_headers(self.token, self.url.rstrip("/"))}
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
        self.assertIn(".seg button.ico", self.get("canvas.css"))
        self.assertIn(".approval", self.get("page.css"))  # the Approve… panel is shared
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

    def test_what_the_page_may_not_send_is_refused_and_a_verdict_alone_is_a_comment(self):
        silent = self.send("comment", {**self.EVENTS["comment"], "text": None})
        self.assertEqual(silent["error"]["code"], -32602)
        self.assertIn("verdict", silent["error"]["message"])  # a comment with no text and no verdict
        approval = {"id": "ap1", "option": "A", "label": "Build A", "carries": ["c1"], "text": None}
        self.assertEqual(self.send("decide", {**approval, "id": "d1"})["error"]["code"], -32601)  # decide is gone
        self.assertEqual(self.send("approve", {"id": "ap2", "option": "A"})["error"]["code"], -32602)
        self.assertFalse((self.folder / "conversation.jsonl").exists())
        thumbs = {**self.EVENTS["comment"], "id": "c2-x", "text": None, "verdict": "up"}
        self.assertEqual(self.send("comment", thumbs).get("result"), "saved")  # a verdict alone is a comment

    def test_a_message_the_agent_posts_without_to_can_be_closed_with_status(self):
        """Issue #120: such a message waited at the bottom of the page for good. A report now carries its own done status
        (D13), and the agent can still mark it done with status."""
        self.assertEqual(run(self.root, "reply", ".design/pay", stdin="Which size first?").returncode, 0)
        started = next(e["id"] for e in self.log() if e["type"] == "reply")
        done = run(self.root, "status", ".design/pay", "done", started, "--read", "0")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual((self.log()[-1]["type"], self.log()[-1]["to"]), ("status", started))

    def test_a_reused_comment_id_is_a_new_version_of_the_comment(self):
        first = self.EVENTS["comment"]
        self.send("comment", first)
        self.send("comment", {**first, "text": "edited"})
        self.assertEqual([e["id"] for e in self.log()], [first["id"]] * 2)
        out = run(self.root, "pending", ".design/pay").stdout
        shown = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
        self.assertEqual([(e["id"], e["text"]) for e in shown], [(first["id"], "edited")])

    def test_a_head_that_holds_anything_or_is_gone_is_still_answered(self):
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
        os.unlink(self.folder / "canvas.json")  # gone: an error the page shows
        self.assertIn("create", json.loads(self.get("data"))["error"])


class Events(unittest.TestCase):
    """The page's log: an `approve` is checked; a `decide` from before the cutoff is old format, one after it is wrong."""

    def check(self, event):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = make_repo(root)
            run(root, "create", ".design/pay", "--by", "designer", stdin=json.dumps(HEAD))
            (folder / "conversation.jsonl").write_text(json.dumps(event) + "\n")
            return run(root, "check", ".design/pay")

    def test_a_decide_is_old_format_before_the_cutoff_and_wrong_after_it_and_an_approve_is_accepted(self):
        decide = {
            "type": "decide",
            "by": "user",
            "id": "d1",
            "option": "A",
            "label": "Build A",
            "carries": [],
            "text": None,
        }
        old = self.check({**decide, "at": "2026-11-01T10:00:00Z"})
        self.assertEqual(old.returncode, 0, old.stdout)
        self.assertIn("format", old.stdout)  # a notice, not an error
        self.assertEqual(self.check({**decide, "at": better.AFTER_CUTOFF}).returncode, 1)
        approve = {**decide, "type": "approve", "at": better.AFTER_CUTOFF}
        self.assertEqual(self.check(approve).returncode, 0)


if __name__ == "__main__":
    unittest.main()
