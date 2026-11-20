"""Check the live architecture page's folder format and agent commands."""

import contextlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "architect-better" / "scripts"
SPEC = importlib.util.spec_from_file_location("architect", SCRIPTS / "architect.py")
architect = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(architect)


class Architect(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name) / "change"
        shutil.copytree(SCRIPTS / "example", self.folder)
        shutil.copyfile(ROOT / "PRINCIPLES.md", self.folder / "PRINCIPLES.md")
        source = Path("skills/code-better/scripts/page.py")
        (self.folder / source.parent).mkdir(parents=True)
        shutil.copyfile(ROOT / source, self.folder / source)
        browser = patch.object(architect.webbrowser, "open")
        self.browser = browser.start()
        self.addCleanup(browser.stop)

    def command(self, name, *args):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            architect.main([name, str(self.folder), *args])
        return output.getvalue()

    def update(self, name, fn):
        path = self.folder / name
        value = json.loads(path.read_text())
        fn(value)
        path.write_text(json.dumps(value))

    def test_shared_page_files_match_design_better(self):
        shared = ROOT / "skills" / "design-better" / "scripts"
        for name in ("page.py", "page.css", "page.js"):
            with self.subTest(name=name):
                self.assertEqual((SCRIPTS / name).read_bytes(), (shared / name).read_bytes())

    def test_check_accepts_example_and_renders_both_states_and_all_flows(self):
        self.assertIn("Valid change folder", self.command("check"))
        data = architect.read_folder(self.folder)
        view = architect.model(data)
        self.assertEqual(data["requirements"][0]["source"]["sentence"], view["requirements"][0]["text"])
        self.assertEqual(set(view["containers"]), {"before", "after"})
        self.assertEqual(len(view["flows"]), len(data["design"]["flows"]))
        self.assertIn('data-p="security"', view["containers"]["after"])
        self.assertNotIn('data-p="security"', view["containers"]["before"])
        self.assertIn('id="flow1-after-step-s6"', view["flows"][0]["versions"]["after"])
        self.assertIn('data-p="security"', view["flows"][0]["versions"]["after"])
        self.browser.assert_not_called()

    def test_unreviewed_folder_renders_without_finding_badges(self):
        def clear_review(data):
            del data["review"]
            for perspective in data["perspectives"]:
                perspective["findings"].clear()

        self.update("perspectives.json", clear_review)
        view = architect.model(architect.read_folder(self.folder))
        self.assertNotIn("review", view["perspectives"])
        self.assertNotIn('class="mark"', view["containers"]["after"])

    def test_editing_a_requirement_changes_its_confirmation_fingerprint(self):
        def wording():
            view = architect.model(architect.read_folder(self.folder))
            return next(req["wording"] for req in view["requirements"] if req["id"] == "Q1")

        before = wording()
        self.update(
            "requirements.json",
            lambda reqs: next(req for req in reqs if req["id"] == "Q1").update(text="A" * 6000),
        )
        after = wording()
        self.assertNotEqual(before, after)
        self.assertEqual(len(after), 64)

    def test_check_rejects_unknown_driver(self):
        self.update("decisions.json", lambda data: data[0]["drivers"].append("missing"))
        with self.assertRaises(SystemExit) as error, contextlib.redirect_stderr(io.StringIO()) as output:
            self.command("check")
        self.assertEqual(error.exception.code, 2)
        self.assertIn("decisions.json: D1: unknown driver", output.getvalue())

    def test_reader_rejects_unknown_finding_part(self):
        self.update(
            "perspectives.json", lambda data: data["perspectives"][0]["findings"][0]["parts"][0].append("step:x")
        )
        with self.assertRaisesRegex(ValueError, "perspectives.json: T1: unknown"):
            architect.read_folder(self.folder)

    def test_reader_rejects_source_outside_change(self):
        self.update("requirements.json", lambda reqs: reqs[0].update(source={"file": "../outside.md"}))
        with self.assertRaisesRegex(ValueError, "requirements.json: invalid source path"):
            architect.read_folder(self.folder)

    def test_pending_and_status_follow_review_requests(self):
        conv = architect.conversation(self.folder)
        conv.append({"action": "approve", "id": "A1", "perspectives": ["security"]})
        self.assertIn('"id": "A1"', self.command("pending"))
        self.assertIn("Marked working: A1", self.command("status", "working", "A1"))
        self.command("reply", "Checking the server.", "--to", "A1")
        item = next(json.loads(line) for line in self.command("pending").splitlines() if '"id": "A1"' in line)
        self.assertEqual(item["status"], "working")
        self.assertEqual(item["thread"][0]["text"], "Checking the server.")
        self.command("status", "done", "A1")
        self.assertNotIn('"id": "A1"', self.command("pending"))

    def test_serve_uses_browser_only_when_requested(self):
        for open_browser in (False, True):
            with self.subTest(open_browser=open_browser):
                self.browser.reset_mock()
                with (
                    patch.object(architect.http.server, "ThreadingHTTPServer") as server,
                    patch.object(architect.page, "stop_like_ctrl_c"),
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    server.return_value.__enter__.return_value.server_address = ("127.0.0.1", 12345)
                    options = [] if open_browser else ["--no-browser"]
                    self.command("serve", *options)
                self.assertEqual(self.browser.call_count, int(open_browser))
                self.assertFalse(architect.conversation(self.folder).address.exists())
