"""Check the live architecture page's folder format and agent commands."""

import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
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
        value = [json.loads(line) for line in path.read_text().splitlines()]
        fn(value)
        path.write_text("".join(json.dumps(record) + "\n" for record in value))

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
        self.assertIn('data-p="Security"', view["containers"]["after"])
        self.assertNotIn('data-p="Security"', view["containers"]["before"])
        self.assertIn('id="flow1-after-step-s6"', view["flows"][0]["versions"]["after"])
        self.assertIn('data-p="Security"', view["flows"][0]["versions"]["after"])
        self.browser.assert_not_called()

    def test_check_and_serve_accept_minimal_folder(self):
        for name in architect.FILES:
            if name.endswith(".jsonl"):
                (self.folder / name).unlink()
        path = self.folder / "design.json"
        design = json.loads(path.read_text())
        for key in ("title", "summary", "scope", "accepted"):
            design.pop(key)
        path.write_text(json.dumps(design))
        (self.folder / "request.md").write_text("# Design title\nFollow-up.")
        self.assertIn("Valid change folder", self.command("check"))
        view = architect.model(architect.read_folder(self.folder))
        self.assertEqual(view["title"], "Design title")
        self.assertEqual(view["accepted"], [])
        self.assertEqual(view["summary"], "")
        self.assertEqual(view["scope"], "")
        (self.folder / "request.md").write_text("")
        self.assertEqual(architect.model(architect.read_folder(self.folder))["title"], self.folder.name)
        with (
            patch.object(architect.http.server, "ThreadingHTTPServer") as server,
            patch.object(architect.page, "stop_like_ctrl_c"),
        ):
            server.return_value.__enter__.return_value.server_address = ("127.0.0.1", 12345)
            self.command("serve", "--no-browser")

    def test_review_fingerprints_and_reruns(self):
        path = self.folder / "reviews.jsonl"
        path.unlink()
        design_path = self.folder / "design.json"
        design = json.loads(design_path.read_text())
        self.command("review", "--perspectives", "Security")
        first = json.loads(path.read_text())
        node = next(n for n in design["containers"]["nodes"] if n["id"] == "server")
        self.assertEqual(
            first["hashes"]["box:server"], hashlib.sha256(json.dumps(node, sort_keys=True).encode()).hexdigest()
        )
        self.assertEqual(set(first["changed"]), set(first["hashes"]))
        self.assertEqual(first["labels"]["box:server"], node["label"])
        self.assertEqual(first["labels"].keys(), first["hashes"].keys())
        view = architect.model(architect.read_folder(self.folder))
        self.assertEqual(view["since"], [])
        self.assertEqual(view["rerun"], ["Observability"])
        self.assertEqual(
            self.render_javascript(view, "reviewSummary([], data.rerun)"),
            "Observability runs again: not reviewed yet.",
        )
        node["detail"] = "New details"
        design_path.write_text(json.dumps(design))
        view = architect.model(architect.read_folder(self.folder))
        self.assertEqual(view["since"], ["box:server"])
        self.assertEqual(view["rerun"], ["Security", "Observability"])
        self.command("review", "--perspectives", "Security", "Observability")
        last = json.loads(path.read_text().splitlines()[-1])
        self.assertEqual(last["changed"], ["box:server"])
        self.assertEqual(set(last["hashes"]), set(first["hashes"]))
        self.assertEqual(architect.model(architect.read_folder(self.folder))["rerun"], [])

    def test_unchanged_example_does_not_rerun_an_earlier_perspective(self):
        view = architect.model(architect.read_folder(self.folder))
        self.assertEqual(view["since"], [])
        self.assertEqual(view["rerun"], [])
        self.assertEqual(
            self.render_javascript(view, "reviewSummary([], data.rerun)"), "Nothing changed since the review."
        )

    def test_reruns_findings_since_each_perspectives_last_review(self):
        path = self.folder / "design.json"
        design = json.loads(path.read_text())
        server = next(node for node in design["containers"]["nodes"] if node["id"] == "server")
        server["detail"] = "Revised server"
        path.write_text(json.dumps(design))
        view = architect.model(architect.read_folder(self.folder))
        self.assertEqual(view["rerun"], ["Security"])

        self.command("review", "--perspectives", "Observability")
        view = architect.model(architect.read_folder(self.folder))
        self.assertEqual(view["rerun"], ["Security"])
        self.assertEqual(view["since"], ["box:server"])

    def test_changed_part_without_findings_reruns_all_applicable_perspectives(self):
        path = self.folder / "design.json"
        design = json.loads(path.read_text())
        user = next(node for node in design["containers"]["nodes"] if node["id"] == "user")
        user["detail"] = "New user details"
        path.write_text(json.dumps(design))
        view = architect.model(architect.read_folder(self.folder))
        self.assertEqual(view["since"], ["box:user"])
        self.assertEqual(view["rerun"], ["Security", "Observability"])

    def test_removed_part_keeps_review_label_and_reruns_its_perspective(self):
        path = self.folder / "design.json"
        data = architect.read_folder(self.folder)
        label = data["parts"]["edge:e3"]["label"]
        design = json.loads(path.read_text())
        design["containers"]["edges"] = [edge for edge in design["containers"]["edges"] if edge["id"] != "e3"]
        path.write_text(json.dumps(design))
        view = architect.model(architect.read_folder(self.folder))
        self.assertEqual(view["since"], ["edge:e3"])
        self.assertEqual(view["change_labels"]["edge:e3"], label)
        self.assertEqual(view["rerun"], ["Security"])
        self.assertEqual(
            self.render_javascript(view, "reviewSummary(data.since.map(key => data.change_labels[key]), data.rerun)"),
            f"Changed since the review: {label}. Security runs again.",
        )
        self.assertIn(
            label,
            self.render_javascript(
                view, "perspectiveTables(data.perspectives, data.findings, data.parts, true, data.removed_labels)"
            ),
        )
        self.command("review", "--perspectives", "Security")
        last = architect.read_folder(self.folder)["reviews"][-1]
        self.assertEqual(last["changed"], ["edge:e3"])
        self.assertNotIn("edge:e3", last["hashes"])

    def test_named_and_numbered_flow_references_resolve_to_one_part(self):
        path = self.folder / "design.json"
        design = json.loads(path.read_text())
        design["flows"][0]["id"] = "Read"
        path.write_text(json.dumps(design))
        view = architect.model(architect.read_folder(self.folder))
        self.assertEqual(view["parts"]["step:Read/s6"], view["parts"]["step:flow1/s6"])
        self.update("findings.jsonl", lambda rows: rows[0].update(parts=["step:Read/missing"]))
        with self.assertRaisesRegex(
            ValueError, r"use box:<id>, edge:<id>, step:<flow id>/<step id> \(flow ids: .*Read"
        ):
            architect.read_folder(self.folder)

    def test_removed_step_accepts_its_historical_numbered_alias(self):
        path = self.folder / "design.json"
        design = json.loads(path.read_text())
        flow = design["flows"][0]
        flow["id"] = "Read"
        path.write_text(json.dumps(design))
        self.command("review", "--perspectives", "Security", "Observability")
        flow["steps"] = [step for step in flow["steps"] if step["id"] != "s6"]
        path.write_text(json.dumps(design))

        view = architect.model(architect.read_folder(self.folder))
        self.assertEqual(view["since"], ["step:Read/s6"])
        self.assertEqual(view["rerun"], ["Security"])
        self.assertEqual(view["removed_labels"]["step:flow1/s6"], view["change_labels"]["step:Read/s6"])

    def test_check_collects_errors_across_files(self):
        (self.folder / "request.md").unlink()
        (self.folder / "design.json").write_text("{")
        self.update("findings.jsonl", lambda rows: rows[0].update(confirmed="false"))
        self.update("spec.jsonl", lambda rows: rows[1].update(checked_by=[]))
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()) as output:
            self.command("check")
        for error in (
            "request.md:1:",
            "design.json:1:",
            "findings.jsonl:1: confirmed: expected bool",
            "spec.jsonl:2: checked_by: expected str",
        ):
            self.assertIn(error, output.getvalue())

    def test_reader_loads_every_contract_file(self):
        data = architect.read_folder(self.folder)
        for name in architect.FILES:
            with self.subTest(name=name):
                raw = (self.folder / name).read_text()
                key = Path(name).stem
                if name.endswith(".jsonl"):
                    self.assertTrue(data[key])
                    self.assertEqual(data[key], [json.loads(line) for line in raw.splitlines()])
                elif name == "design.json":
                    self.assertEqual(data[key], json.loads(raw))
                else:
                    self.assertEqual(data[key], raw)

    def test_reader_keeps_unicode_line_separators_inside_a_record(self):
        path = self.folder / "spec.jsonl"
        path.write_text(path.read_text().replace("Inspect the server", "Inspect\u2028the server"))
        self.assertEqual(
            architect.read_folder(self.folder)["spec"][1]["checked_by"], "Inspect\u2028the server bind address."
        )

    def test_check_reports_invalid_diagram_render_input(self):
        path = self.folder / "design.json"
        design = json.loads(path.read_text())
        design["containers"]["edges"][0]["label"] = 42
        path.write_text(json.dumps(design))
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()) as output:
            self.command("check")
        self.assertIn("design.json:1:", output.getvalue())

    def test_unreviewed_folder_omits_findings_controls_and_badges(self):
        (self.folder / "reviews.jsonl").unlink()
        view = architect.model(architect.read_folder(self.folder))
        self.assertEqual(view["reviews"], [])
        self.assertNotIn('class="mark"', view["containers"]["after"])
        html = self.render_javascript(view, "controls(data.perspectives, data.reviews.at(-1))")
        self.assertIn('aria-label="State"', html)
        self.assertNotIn('aria-label="Findings"', html)

    def test_perspective_table_marks_unconfirmed_findings(self):
        view = architect.model(architect.read_folder(self.folder))
        html = self.render_javascript(view, "perspectiveTables(data.perspectives, data.findings, data.parts, true)")
        self.assertEqual(html.count('<span class="chip guess">Unconfirmed</span>'), 1)
        self.assertIn("Dashboard page to dashboard.py: POST /rpc (Flows, step 2c)", html)
        self.assertIn("Coordinator agent to dashboard.py: wait ends with the answer (Flows, step 2d)", html)

    def test_thread_comment_lookup_works_before_any_rendered_hook(self):
        event = {"id": "C1", "type": "comment", "on": {"id": "target"}, "text": "Original"}
        edited = {**event, "text": "Edited"}
        deleted = {"type": "delete", "to": "C1"}
        result = self.render_javascript(
            {"events": [event, edited, deleted]},
            """JSON.stringify([
              threadComment(data.events.slice(0, 1), 'C1'),
              threadComment(data.events.slice(0, 2), 'C1'),
              threadComment(data.events, 'C1')
            ])""",
        )
        self.assertEqual(json.loads(result), [event, edited, None])

    def render_javascript(self, view, expression):
        result = subprocess.run(
            [
                "node",
                "-e",
                """
                const vm = require('node:vm');
                const fs = require('node:fs');
                const data = JSON.parse(fs.readFileSync(0, 'utf8'));
                const source = fs.readFileSync(process.argv[1], 'utf8');
                const context = {data, fetch: () => new Promise(() => {}),
                  document: {querySelector: () => ({}), getElementById: id => id === 'target' ? {} : null}};
                vm.runInNewContext(source, context);
                process.stdout.write(vm.runInNewContext(process.argv[2], context));
                """,
                str(SCRIPTS / "architect.js"),
                expression,
            ],
            input=json.dumps(view),
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout

    def test_editing_a_requirement_changes_its_confirmation_fingerprint(self):
        def wording():
            view = architect.model(architect.read_folder(self.folder))
            return next(req["wording"] for req in view["requirements"] if req["id"] == "Q1")

        before = wording()
        self.update(
            "requirements.jsonl",
            lambda reqs: next(req for req in reqs if req["id"] == "Q1").update(text="A" * 6000),
        )
        after = wording()
        self.assertNotEqual(before, after)
        self.assertEqual(len(after), 64)

    def test_check_reports_bad_record_with_file_and_line(self):
        cases = [
            ("requirements.jsonl", {"kind": "Responsiveness"}, "unknown requirement kind"),
            ("perspectives.jsonl", {"applies": "true"}, "applies: expected bool"),
            ("findings.jsonl", {"handled_by": 42}, "handled_by: expected string or null"),
            ("findings.jsonl", {"confirmed": 1}, "confirmed: expected bool"),
            ("reviews.jsonl", {"hashes": {"box:server": "wrong"}}, "hashes: invalid"),
            ("reviews.jsonl", {"changed": ["box:missing"]}, "unknown changed part 'box:missing'"),
            ("decisions.jsonl", {"drivers": ["missing"]}, "unknown driver 'missing'"),
            ("spec.jsonl", {"checked_by": []}, "checked_by: expected str"),
        ]
        for name, change, message in cases:
            with self.subTest(name=name):
                file = self.folder / name
                self.update(name, lambda rows, change=change: rows[1].update(change))
                with self.assertRaises(SystemExit) as error, contextlib.redirect_stderr(io.StringIO()) as output:
                    self.command("check")
                self.assertEqual(error.exception.code, 2)
                self.assertIn(f"{name}:2: {message}", output.getvalue())
                shutil.copyfile(SCRIPTS / "example" / name, file)

    def test_reader_rejects_unknown_finding_part(self):
        self.update("findings.jsonl", lambda rows: rows[0]["parts"].append("edge:e3+step:flow1/missing"))
        with self.assertRaisesRegex(ValueError, "findings.jsonl:1: unknown part 'step:flow1/missing'"):
            architect.read_folder(self.folder)

    def test_reader_rejects_source_outside_change(self):
        self.update(
            "requirements.jsonl",
            lambda reqs: reqs[0].update(source={"type": "file", "file": "../outside.md", "symbol": "name"}),
        )
        with self.assertRaisesRegex(ValueError, "requirements.jsonl:1: invalid source path"):
            architect.read_folder(self.folder)

    def test_pending_and_status_follow_review_requests(self):
        conv = architect.conversation(self.folder)
        conv.append(
            {
                "type": "approve",
                "by": "user",
                "id": "A1",
                "again": False,
                "perspectives": ["security"],
                "changes": [],
                "text": "Design approved",
            }
        )
        self.assertIn('"id": "A1"', self.command("pending"))
        self.assertIn("Marked working: A1", self.command("status", "working", "A1"))
        self.command("reply", "Checking the server.", "--to", "A1")
        item = next(json.loads(line) for line in self.command("pending").splitlines() if '"id": "A1"' in line)
        self.assertEqual(item["status"], "working")
        self.assertEqual(item["thread"][0]["text"], "Checking the server.")
        self.command("status", "done", "A1")
        self.assertNotIn('"id": "A1"', self.command("pending"))

    def test_serve_refuses_to_write_into_the_example(self):
        with self.assertRaisesRegex(ValueError, "use a copy"):
            architect.serve(SCRIPTS / "example", 0, False)

    def test_writing_commands_refuse_the_example(self):
        for command in (
            ["wait", "--timeout", "0"],
            ["reply", "Text"],
            ["status", "working", "A1"],
            ["review", "--perspectives", "Security"],
        ):
            with (
                self.subTest(command=command[0]),
                patch.object(architect, "HERE", self.folder.parent.resolve() / "skill" / "scripts"),
                contextlib.redirect_stderr(io.StringIO()) as output,
            ):
                with self.assertRaises(SystemExit) as error:
                    architect.main([command[0], str(self.folder), *command[1:]])
                self.assertEqual(error.exception.code, 2)
                self.assertIn(
                    "serve writes conversation files; use a copy of the change folder outside skills/",
                    output.getvalue(),
                )

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
