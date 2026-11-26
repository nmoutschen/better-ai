"""Check the live architecture page's payload and the architect-better commands: review, specs, register, render, serve
and the conversation verbs, on a copy of the fixture change folder."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import architect_records as rec  # noqa: E402
from better import call as better_call  # noqa: E402
from better import run as better_run  # noqa: E402

from better_ai import page, schema  # noqa: E402
from better_ai.architect import commands, diagram, model  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "src" / "better_ai" / "architect"
SKILL = "architect-better"

# The review summary the page shows for the perspectives that run again, by name.
RERUN_SUMMARY = "reviewSummary([], {}, data.rerun.map(id => nameOf(data.perspectives, id)))"


class Architect(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        self.folder = rec.example_folder(self.repo)
        self.unit = rec.unit_of(self.folder)
        browser = mock.patch.object(page.webbrowser, "open", return_value=True)
        self.browser = browser.start()
        self.addCleanup(browser.stop)

    def command(self, name, *args, stdin=None):
        code, out, err = rec.run_cli(name, str(self.folder), *args, stdin=stdin)
        self.assertEqual(code, 0, err)
        return out

    def update(self, name, fn):
        path = self.folder / name
        value = [json.loads(line) for line in path.read_text().splitlines()]
        fn(value)
        path.write_text("".join(json.dumps(record) + "\n" for record in value))

    def load(self):
        return model.load(self.unit)

    def read(self):
        return model.read_folder(self.unit)

    def test_check_accepts_example_and_renders_both_states_and_all_flows(self):
        self.assertEqual(rec.run_cli("check", str(self.folder)), (0, "", ""))
        data = self.read()
        view = model.model(data)
        self.assertEqual(data["requirements"][0]["source"]["sentence"], view["requirements"][0]["text"])
        self.assertEqual(set(view["containers"]), {"before", "after"})
        self.assertEqual(len(view["flows"]), len(data["design"]["flows"]))
        self.assertIn('data-p="security"', view["containers"]["after"])
        self.assertNotIn('data-p="security"', view["containers"]["before"])
        self.assertIn('id="flow1-after-step-s6"', view["flows"][0]["versions"]["after"])
        self.assertIn('data-p="security"', view["flows"][0]["versions"]["after"])
        self.assertEqual(view["errors"], [])
        self.browser.assert_not_called()

    def test_check_and_load_accept_a_minimal_folder(self):
        for name in model.FILES:
            if name.endswith(".jsonl"):
                (self.folder / name).unlink()
        (self.folder / "conversation.jsonl").unlink()
        path = self.folder / "architect.json"
        meta = json.loads(path.read_text())
        meta.update(request={"text": "Follow-up.", "from": {"type": "chat"}}, title="Design title")
        meta.update(summary="", scope="", accepted=[])
        path.write_text(json.dumps(meta))
        self.assertEqual(rec.run_cli("check", str(self.folder)), (0, "", ""))
        view = model.model(self.read())
        self.assertEqual(view["title"], "Design title")
        self.assertEqual(view["accepted"], [])
        self.assertEqual(view["summary"], "")
        self.assertEqual(view["scope"], "")
        path.unlink()
        # without the head file the folder is no unit: the page keeps what it can show, and says what is missing
        view = model.load(self.unit)
        self.assertEqual(view["title"], self.folder.name)
        self.assertEqual([e["file"] for e in view["errors"]], ["architect.json"])

    def test_review_fingerprints_and_reruns(self):
        path = self.folder / "reviews.jsonl"
        path.unlink()
        design_path = self.folder / "design.json"
        design = json.loads(design_path.read_text())
        self.command("review", "--perspectives", "security")
        first = json.loads(path.read_text())
        node = next(n for n in design["containers"]["nodes"] if n["id"] == "server")
        self.assertEqual(first["hashes"]["box:server"], schema.fingerprint(node, drop=()))
        self.assertEqual(set(first["changed"]), set(first["hashes"]))
        self.assertEqual(first["labels"]["box:server"], node["label"])
        self.assertEqual(first["labels"].keys(), first["hashes"].keys())
        self.assertEqual(first["by"], "architect")
        view = model.model(self.read())
        self.assertEqual(view["since"], [])
        # A review written before the shared fingerprint holds the earlier form of each part's: it still matches.
        nodes = {f"box:{n['id']}": n for n in design["containers"]["nodes"]}
        stored = {**first, "hashes": {**first["hashes"], "box:server": model.stored_fingerprint(nodes["box:server"])}}
        path.write_text(json.dumps(stored) + "\n")
        self.assertEqual(model.model(self.read())["since"], [])
        path.write_text(json.dumps(first) + "\n")
        self.assertEqual(view["rerun"], ["observability"])
        self.assertEqual(
            self.render_javascript(view, RERUN_SUMMARY),
            "Observability runs again: not reviewed yet.",
        )
        node["detail"] = "New details"
        design_path.write_text(json.dumps(design))
        view = model.model(self.read())
        self.assertEqual(view["since"], ["box:server"])
        self.assertEqual(view["rerun"], ["security", "observability"])
        self.command("review", "--perspectives", "security", "observability")
        last = json.loads(path.read_text().splitlines()[-1])
        self.assertEqual(last["changed"], ["box:server"])
        self.assertEqual(set(last["hashes"]), set(first["hashes"]))
        self.assertEqual(model.model(self.read())["rerun"], [])
        self.assertEqual(rec.run_cli("check", str(self.folder)), (0, "", ""))

    def test_a_change_to_the_design_document_or_a_requirement_makes_the_review_due_again(self):
        document = self.repo / "docs" / "designs" / "ex" / "design.md"
        document.parent.mkdir(parents=True)
        document.write_text("# Ex\n\nIntro.\n\n## Command contract\n\nOld.\n\n```\n## not a heading\n```\n")
        meta = self.folder / "architect.json"
        meta.write_text(json.dumps({**json.loads(meta.read_text()), "document": {"file": "docs/designs/ex/design.md"}}))
        self.command("review", "--perspectives", "security", "observability")
        last = self.read()["reviews"][-1]
        self.assertEqual(
            {key for key in last["texts"] if key.startswith("section:")},
            {"section:(start)", "section:Command contract"},
        )
        self.assertIn("requirement:F1", last["texts"])
        view = model.model(self.read())
        self.assertEqual((view["since"], view["rerun"]), ([], []))

        document.write_text(document.read_text().replace("Old.", "New.") + "\n## CI\n\nRuns the tests.\n")
        self.update("requirements.jsonl", lambda reqs: reqs[0].update(text="A new wording."))
        view = model.model(self.read())
        self.assertEqual(view["since"], ["requirement:F1", "section:Command contract", "section:CI"])
        self.assertEqual(view["rerun"], ["security", "observability"])
        self.assertEqual(view["removed"], [])
        self.assertEqual(
            self.render_javascript(
                view, "reviewSummary(data.since, data.change_labels, ['Security', 'Observability'])"
            ),
            "Changed since the review: Requirement F1, Design section Command contract, Design section CI. "
            "Security, Observability run again.",
        )
        self.command("review", "--perspectives", "security", "observability")
        view = model.model(self.read())
        self.assertEqual((view["since"], view["rerun"]), ([], []))
        self.assertEqual(rec.run_cli("check", str(self.folder)), (0, "", ""))

        meta.write_text(json.dumps({**json.loads(meta.read_text()), "document": {"file": "../design.md"}}))
        code, out, _ = rec.run_cli("check", str(self.folder))
        self.assertEqual(code, 1)
        self.assertIn("architect.json:1: document.file: invalid source path", out)

    def test_review_appends_after_a_file_that_lacks_its_final_newline(self):
        path = self.folder / "reviews.jsonl"
        path.write_text(path.read_text().rstrip("\n"))
        before = len(path.read_text().splitlines())
        self.command("review", "--perspectives", "security")
        self.assertEqual(len(path.read_text().splitlines()), before + 1)
        self.assertEqual(rec.run_cli("check", str(self.folder)), (0, "", ""))

    def test_unchanged_example_does_not_rerun_an_earlier_perspective(self):
        view = model.model(self.read())
        self.assertEqual(view["since"], [])
        self.assertEqual(view["rerun"], [])
        self.assertEqual(self.render_javascript(view, RERUN_SUMMARY), "Nothing changed since the review.")

    def test_reruns_findings_since_each_perspectives_last_review(self):
        path = self.folder / "design.json"
        design = json.loads(path.read_text())
        server = next(node for node in design["containers"]["nodes"] if node["id"] == "server")
        server["detail"] = "Revised server"
        path.write_text(json.dumps(design))
        self.assertEqual(model.model(self.read())["rerun"], ["security"])

        self.command("review", "--perspectives", "observability")
        view = model.model(self.read())
        self.assertEqual(view["rerun"], ["security"])
        self.assertEqual(view["since"], ["box:server"])

    def test_changed_part_without_findings_reruns_all_applicable_perspectives(self):
        path = self.folder / "design.json"
        design = json.loads(path.read_text())
        user = next(node for node in design["containers"]["nodes"] if node["id"] == "user")
        user["detail"] = "New user details"
        path.write_text(json.dumps(design))
        view = model.model(self.read())
        self.assertEqual(view["since"], ["box:user"])
        self.assertEqual(view["rerun"], ["security", "observability"])

    def test_removed_part_keeps_review_label_and_reruns_its_perspective(self):
        path = self.folder / "design.json"
        label = self.read()["parts"]["edge:e3"]["label"]
        design = json.loads(path.read_text())
        design["containers"]["edges"] = [edge for edge in design["containers"]["edges"] if edge["id"] != "e3"]
        path.write_text(json.dumps(design))
        view = model.model(self.read())
        self.assertEqual(view["since"], ["edge:e3"])
        self.assertEqual(view["change_labels"]["edge:e3"], label)
        self.assertEqual(view["rerun"], ["security"])
        self.assertEqual(
            self.render_javascript(view, "reviewSummary(data.since, data.change_labels, ['Security'])"),
            f"Changed since the review: {label}. Security runs again.",
        )
        self.assertIn(
            label,
            self.render_javascript(
                view, "perspectiveTables(data.perspectives, data.findings, data.parts, true, data.removed_labels)"
            ),
        )
        self.command("review", "--perspectives", "security")
        last = self.read()["reviews"][-1]
        self.assertEqual(last["changed"], ["edge:e3"])
        self.assertNotIn("edge:e3", last["hashes"])

    def test_many_changes_give_counts_and_fold_the_full_list(self):
        path = self.folder / "design.json"
        design = json.loads(path.read_text())
        for node in design["containers"]["nodes"]:
            node["detail"] = "Revised"
        for flow in design["flows"]:
            for step in flow["steps"]:
                step["label"] = "Revised step"
        removed = self.read()["parts"]["edge:e3"]["label"]
        design["containers"]["edges"] = [edge for edge in design["containers"]["edges"] if edge["id"] != "e3"]
        path.write_text(json.dumps(design))
        view = model.model(self.read())
        boxes = sum(key.startswith("box:") for key in view["since"])
        steps = sum(key.startswith("step:") for key in view["since"])
        self.assertEqual(len(view["since"]), boxes + steps + 1)
        self.assertEqual(
            self.render_javascript(view, "reviewSummary(data.since, data.change_labels, ['Security'], data.removed)"),
            f"{len(view['since'])} parts changed since the review: {boxes} boxes, 1 arrow, {steps} steps in 2 flows. "
            "1 of them removed. Security runs again.",
        )
        folded = self.render_javascript(view, "changeList(data.since, data.change_labels, data.removed)")
        self.assertIn(f"<summary>All {len(view['since'])} changes</summary>", folded)
        self.assertEqual(folded.count("<li>"), len(view["since"]))
        self.assertIn(removed + ' <span class="muted">(removed)</span>', folded)

    def test_few_changes_are_listed_without_a_fold(self):
        path = self.folder / "design.json"
        design = json.loads(path.read_text())
        design["containers"]["nodes"][0]["detail"] = "Revised"
        path.write_text(json.dumps(design))
        view = model.model(self.read())
        self.assertEqual(self.render_javascript(view, "changeList(data.since, data.change_labels, data.removed)"), "")

    def test_check_collects_errors_across_files(self):
        (self.folder / "design.json").write_text("{")
        self.update("findings.jsonl", lambda rows: rows[0].update(confirmed="false"))
        self.update("spec.jsonl", lambda rows: rows[1].update(checked_by=[]))
        code, out, _ = rec.run_cli("check", str(self.folder))
        self.assertEqual(code, 1)
        for error in (
            "design.json:1:",
            "findings.jsonl:1: confirmed: expected boolean, got string",
            "spec.jsonl:2: checked_by: expected string, got array",
        ):
            self.assertIn(error, out)

    def test_reader_loads_every_contract_file(self):
        data = self.read()
        for name in model.FILES:
            with self.subTest(name=name):
                raw = (self.folder / name).read_text()
                key = Path(name).stem
                if name.endswith(".jsonl"):
                    self.assertTrue(data[key])
                    self.assertEqual(data[key], [json.loads(line) for line in raw.splitlines()])
                elif name == "design.json":
                    design = json.loads(raw)
                    self.assertEqual(data["design"], {"containers": design["containers"], "flows": design["flows"]})
                else:
                    self.assertEqual(data["architect"], json.loads(raw))
        self.assertEqual(data["errors"], [])

    def test_reader_keeps_unicode_line_separators_inside_a_record(self):
        path = self.folder / "spec.jsonl"
        path.write_text(path.read_text().replace("Inspect the server", "Inspect the server"))
        self.assertEqual(self.read()["spec"][1]["checked_by"], "Inspect the server bind address.")

    def test_check_reports_invalid_diagram_render_input(self):
        path = self.folder / "design.json"
        design = json.loads(path.read_text())
        design["containers"]["edges"][0]["label"] = 42
        path.write_text(json.dumps(design))
        code, out, _ = rec.run_cli("check", str(self.folder))
        self.assertEqual(code, 1)
        self.assertIn("design.json:1: containers", out)

    def test_check_reports_a_reference_to_a_missing_box(self):
        path = self.folder / "design.json"
        design = json.loads(path.read_text())
        design["containers"]["edges"][0]["to"] = "nowhere"
        path.write_text(json.dumps(design))
        data = self.load()
        self.assertIn(
            "design.json:1: containers.edges[0].to: Edge 'e1': to references missing 'nowhere'", self.errors(data)
        )
        self.assertEqual(data["flows"], [])
        self.assertEqual(data["containers"], {"before": "", "after": ""})

    def test_unreviewed_folder_omits_findings_controls_and_badges(self):
        (self.folder / "reviews.jsonl").unlink()
        view = model.model(self.read())
        self.assertEqual(view["reviews"], [])
        self.assertNotIn('class="mark"', view["containers"]["after"])
        html = self.render_javascript(view, "controls(data.perspectives, data.reviews.at(-1))")
        self.assertIn('aria-label="State"', html)
        self.assertNotIn('aria-label="Findings"', html)

    def test_perspective_table_marks_unconfirmed_findings(self):
        view = model.model(self.read())
        html = self.render_javascript(view, "perspectiveTables(data.perspectives, data.findings, data.parts, true)")
        self.assertEqual(html.count('<span class="chip plain">Unconfirmed</span>'), 1)
        self.assertIn("Dashboard page to dashboard.py: POST /rpc (Flows, step 2c)", html)
        self.assertIn("Coordinator agent to dashboard.py: wait ends with the answer (Flows, step 2d)", html)

    def test_requirements_are_grouped_by_kind_and_sorted_by_id_number(self):
        def shuffle(records):
            f1 = records[0]
            records.reverse()
            records.extend(
                {**f1, "id": ident, "kind": kind, "text": f"Requirement {ident}."}
                for ident, kind in (("F10", "functional"), ("C11", "constraint"), ("F8", "functional"))
            )

        self.update("requirements.jsonl", shuffle)
        view = model.model(self.read())
        self.assertEqual(view["errors"], [])
        self.assertEqual(
            [req["id"] for req in view["requirements"]],
            ["F1", "F2", "F3", "F4", "F8", "F10", "Q1", "Q2", "Q3", "C1", "C2", "C11"],
        )
        # A record whose id is not valid goes after the valid ones, whatever its kind.
        self.update("requirements.jsonl", lambda reqs: reqs.insert(0, {**reqs[0], "id": "F-1"}))
        view = model.model(self.read())
        self.assertEqual(view["requirements"][-1]["id"], "(line 1)")
        self.assertEqual(view["requirements"][0]["id"], "F1")

    def test_a_flow_the_change_removes_is_drawn_in_both_states_and_marked_removed(self):
        path = self.folder / "design.json"
        design = json.loads(path.read_text())
        design["flows"][0]["in"] = ["before"]
        path.write_text(json.dumps(design))
        flow = model.model(self.read())["flows"][0]
        self.assertEqual((flow["new"], flow["removed"]), (False, True))
        self.assertTrue(flow["versions"]["before"])
        self.assertIn("REMOVED", flow["versions"]["after"])

    def test_a_requirement_source_is_shown_as_words_and_no_link_to_an_endpoint(self):
        view = model.model(self.read())
        html = self.render_javascript(view, "requirementRows(data.requirements).join('')")
        self.assertIn("LISTEN_GAP", html)
        self.assertNotIn("/source", html)

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
                const context = {data, fetch: () => new Promise(() => {}),
                  document: {querySelector: () => ({}), getElementById: id => id === 'target' ? {} : null}};
                vm.createContext(context);
                for (const file of [process.argv[1], process.argv[2]]) vm.runInContext(fs.readFileSync(file, 'utf8'), context);
                process.stdout.write(vm.runInContext(process.argv[3], context));
                """,
                str(PACKAGE.parent / "page" / "page.js"),
                str(PACKAGE / "page.js"),
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
            view = model.model(self.read())
            return next(req["wording"] for req in view["requirements"] if req["id"] == "Q1")

        before = wording()
        self.update(
            "requirements.jsonl",
            lambda reqs: next(req for req in reqs if req["id"] == "Q1").update(text="A" * 6000),
        )
        after = wording()
        self.assertNotEqual(before, after)
        self.assertEqual(len(after), 64)

    def errors(self, data):
        return [f"{e['file']}:{e['line']}: {e['field']}: {e['message']}" for e in data["errors"]]

    def test_check_reports_bad_record_with_file_and_line(self):
        cases = [
            ("requirements.jsonl", {"kind": "Responsiveness"}, "kind: must be one of"),
            ("perspectives.jsonl", {"applies": "true"}, "applies: expected boolean, got string"),
            ("findings.jsonl", {"handled_by": 42}, "handled_by: expected string, got integer"),
            ("findings.jsonl", {"confirmed": 1}, "confirmed: expected boolean, got integer"),
            ("reviews.jsonl", {"hashes": {"box:server": "wrong"}}, "hashes.box:server: must match"),
            ("reviews.jsonl", {"changed": ["box:missing"]}, "changed[0]: unknown changed part 'box:missing'"),
            ("decisions.jsonl", {"drivers": ["missing"]}, 'drivers[0]: dangling: "missing" is not a requirement'),
            ("spec.jsonl", {"checked_by": []}, "checked_by: expected string, got array"),
        ]
        for name, change, message in cases:
            with self.subTest(name=name, change=change):
                original = (self.folder / name).read_text()
                self.update(name, lambda rows, change=change: rows[1].update(change))
                code, out, _ = rec.run_cli("check", str(self.folder))
                self.assertEqual(code, 1)
                self.assertIn(f"{name}:2: {message}", out)
                (self.folder / name).write_text(original)

    def test_reader_rejects_unknown_finding_part(self):
        self.update("findings.jsonl", lambda rows: rows[0]["parts"].append("edge:e3+step:ask/missing"))
        errors = self.errors(self.load())
        self.assertEqual(len(errors), 1)
        self.assertIn("findings.jsonl:1: parts[1]: unknown part 'step:ask/missing'", errors[0])

    def test_reader_rejects_source_outside_change(self):
        self.update(
            "requirements.jsonl",
            lambda reqs: reqs[0].update(source={"type": "file", "file": "../outside.md", "symbol": "name"}),
        )
        errors = self.errors(self.load())
        self.assertEqual(len(errors), 1)
        self.assertIn("requirements.jsonl:1: source.file: invalid source path", errors[0])

    def conversation(self):
        return page.Conversation(self.unit, page.spec_of(self.unit.skill), page.load_docs(self.unit.skill))

    def test_pending_and_status_follow_review_requests(self):
        self.conversation().append(
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
        self.command("reply", "--to", "A1", "--state", "working", stdin="Checking the server.")
        self.assertNotIn('"id": "A1"', self.command("pending"))
        (item,) = self.conversation().delivery(recover_ids=frozenset({"A1"})).items
        self.assertEqual(item["status"], "working")
        self.assertEqual(item["thread"][0]["text"], "Checking the server.")
        self.command("status", "done", "A1")
        self.assertEqual(self.conversation().delivery(recover_ids=frozenset({"A1"})).items, [])

    def test_the_page_declares_the_capabilities_its_events_need(self):
        spec = page.spec_of(self.unit.skill)
        self.assertEqual(set(spec.capabilities), {"pins", "accept", "confirm", "approve"})
        self.assertEqual(set(spec.tracked()), {"note", "comment", "confirm", "approve"})
        self.assertEqual(spec.events, "architect-events.schema.json")
        self.assertEqual(spec.agent, "architect")

    def test_the_page_uses_the_shared_approve_and_not_its_own_copy(self):
        script = (PACKAGE / "page.js").read_text()
        self.assertIn("pageApprove(", script)
        self.assertNotIn("conversation.send('approve'", script)
        self.assertNotIn("Could not load the design", (PACKAGE / "page.html").read_text())  # the strips are shared
        for strip in ('class="offline"', 'class="unwatched"'):
            self.assertNotIn(strip, (PACKAGE / "page.html").read_text())

    # ------------------------------------------------------------ specs, register, render

    def test_specs_prints_the_generated_table_on_stdout_and_writes_nothing(self):
        before = sorted(p.relative_to(self.repo).as_posix() for p in self.repo.rglob("*") if ".git" not in p.parts)
        out = self.command("specs")
        self.assertEqual(out.splitlines()[0], commands.GENERATED)
        records = self.read()["spec"]
        self.assertIn(records[0]["statement"], out)
        after = sorted(p.relative_to(self.repo).as_posix() for p in self.repo.rglob("*") if ".git" not in p.parts)
        self.assertEqual(after, before)

    def test_register_writes_the_kinds_into_the_unit(self):
        out = self.command("register")
        self.assertIn(f"{self.unit.label}/register.html", out)
        text = (self.folder / "register.html").read_text()
        for kind in json.loads((PACKAGE / "kinds.json").read_text()):
            self.assertIn(f"<code>{kind['name']}</code>", text)
        self.assertEqual(rec.run_cli("check", str(self.folder)), (0, "", ""))  # not a record file

    def test_render_writes_the_page_and_the_before_and_after_svgs_inside_the_unit(self):
        out = self.command("render")
        self.assertIn("render/index.html", out)
        render = self.folder / "render"
        svgs = sorted(p.name for p in render.glob("*.svg"))
        design = self.read()["design"]
        self.assertEqual(svgs, sorted(diagram.drawings(design)))
        self.assertIn("containers-before.svg", svgs)
        self.assertIn("containers-after.svg", svgs)
        for name, svg in diagram.drawings(design).items():
            self.assertEqual((render / name).read_text(), svg + "\n")
        html = (render / "index.html").read_text()
        self.assertIn('id="page-data"', html)
        self.assertNotIn('<script src="/', html)  # scripts and styles are inline: it opens without a server
        self.assertNotIn('<link href="/', html)
        data = json.loads(re.search(r'id="page-data">(.*?)</script>', html, re.S).group(1))
        self.assertTrue(data["static"])
        self.assertEqual(data["title"], self.load()["title"])
        self.assertEqual(len(data["events"]), len((self.folder / "conversation.jsonl").read_text().splitlines()))
        self.assertEqual(rec.run_cli("check", str(self.folder)), (0, "", ""))

    def test_render_refuses_a_design_it_cannot_draw_and_writes_nothing(self):
        path = self.folder / "design.json"
        design = json.loads(path.read_text())
        design["containers"]["edges"][0]["to"] = "nowhere"
        path.write_text(json.dumps(design))
        code, _, err = rec.run_cli("render", str(self.folder))
        self.assertEqual(code, 1)
        self.assertIn("design.json:1: containers.edges[0].to", err)
        self.assertFalse((self.folder / "render").exists())

    def test_render_writes_only_inside_the_unit(self):
        before = {p for p in self.repo.rglob("*") if ".git" not in p.parts}
        self.command("render")
        self.command("register")
        new = {p for p in self.repo.rglob("*") if ".git" not in p.parts} - before
        self.assertTrue(new)
        for path in new:
            self.assertTrue(path.is_relative_to(self.folder), path)

    def test_render_refuses_a_symlinked_render_folder(self):
        outside = self.repo / "outside"
        outside.mkdir()
        (self.folder / "render").symlink_to(outside)
        code, _, err = rec.run_cli("render", str(self.folder))
        self.assertEqual(code, 1)
        self.assertIn("symlink", err)
        self.assertEqual(list(outside.iterdir()), [])

    # ------------------------------------------------------------ serving

    def serve(self, *flags):
        """`serve <unit> --once`: the address it printed, once the server is up, and the thread that runs it."""
        result = {}

        def go():
            result["done"] = rec.run_cli("serve", str(self.folder), "--once", *flags)

        thread = threading.Thread(target=go)
        thread.start()
        address = self.folder / ".server"
        for _ in range(100):
            if address.exists() and address.read_text().strip():
                break
            thread.join(0.1)
        return address.read_text().strip(), thread, result

    def test_serve_uses_the_browser_only_when_asked(self):
        for flags, opened in (((), 0), (("--no-browser",), 0), (("--open",), 1)):
            with self.subTest(flags=flags):
                self.browser.reset_mock()
                url, thread, result = self.serve(*flags)
                with urllib.request.urlopen(url, timeout=10) as response:
                    self.assertEqual(response.status, 200)
                thread.join(10)
                self.assertEqual(self.browser.call_count, opened)
                self.assertEqual(result["done"][0], 0, result["done"])
                self.assertFalse((self.folder / ".server").exists())

    def test_the_served_page_carries_the_shared_shell_and_its_own_main_section(self):
        url, thread, _ = self.serve()
        with urllib.request.urlopen(url, timeout=10) as response:
            html = response.read().decode()
        thread.join(10)
        self.assertIn('<script src="/page.js"></script>', html)
        self.assertIn('<script src="/architect.js"></script>', html)
        self.assertIn('<link href="/architect.css" rel="stylesheet">', html)
        self.assertIn('id="panel-containers"', html)
        self.assertIn('class="unwatched"', html)  # the shared strips, once
        self.assertEqual(html.count('class="unwatched"'), 1)

    def start_server(self):
        """`serve <unit>` as an agent runs it: the process, and the address once it is up."""
        process = subprocess.Popen(
            [*better_command(), "serve", str(self.folder), "--linger", "0.2"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=better_env(),
        )
        self.addCleanup(process.stdout.close)
        self.addCleanup(process.wait)
        self.addCleanup(process.terminate)
        for _ in range(100):
            if (self.folder / ".server").exists() and (self.folder / ".server").read_text().strip():
                break
            time.sleep(0.1)
        return (self.folder / ".server").read_text().strip()

    def test_the_served_files_are_the_fixed_table_and_the_old_endpoints_are_gone(self):
        url = self.start_server()

        def status(path):
            try:
                with urllib.request.urlopen(self.request(url + path), timeout=10) as response:
                    return response.status, response.read()
            except urllib.error.HTTPError as error:
                error.close()
                return error.code, b""

        for path in ("page.js", "page.css", "architect.js", "architect.css", "data", "rev"):
            self.assertEqual(status(path)[0], 200, path)
        for path in ("source?file=request", "design.json", "architect.py", "schemas/design.schema.json"):
            self.assertEqual(status(path)[0], 404, path)
        data = json.loads(status("data")[1])
        self.assertEqual(data["title"], self.load()["title"])
        self.assertIn("listening", data)

    def test_a_page_event_the_schema_refuses_is_not_written(self):
        """An `approve` event the events schema refuses is not written."""
        url = self.start_server()

        before = (self.folder / "conversation.jsonl").read_text()
        bad = self.post(url, "approve", {"id": "a9", "perspectives": ["security"], "changes": [], "text": "t"})
        self.assertIn("error", bad)
        self.assertEqual((self.folder / "conversation.jsonl").read_text(), before)

    # What the page sends, by method, as page.js sends it (the server adds type, by and at).
    SENT = {
        "comment": {"id": "c1-x", "n": 1, "text": "unclear", "on": {"id": "req-F1", "title": "F1", "key": "k"}},
        "note": {"id": "m-x", "text": "hi", "to": None},
        "approve": {"id": "approval-x", "again": False, "perspectives": ["security"], "changes": [], "text": "ok"},
        "confirm": {"id": "confirm-x", "requirement": "F1", "wording": "abc", "text": "Confirmed requirement F1."},
        "delete": {"to": "c1-x"},
        "accept": {"to": "c1-x"},
    }

    def request(self, url, body=None, headers=None):
        """A request with the page token `serve` left in the unit, as the page sends it."""
        token = (self.folder / ".server-token").read_text().strip()
        return urllib.request.Request(url, body, {**(headers or {}), "X-Page-Token": token})

    def post(self, url, method, params):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        headers = {"Content-Type": "application/json", "Origin": url.rstrip("/")}
        with urllib.request.urlopen(self.request(url + "rpc", body, headers), timeout=10) as response:
            return json.loads(response.read())

    def test_an_architect_note_with_on_and_a_confirm_without_wording_are_refused(self):
        url = self.start_server()
        before = (self.folder / "conversation.jsonl").read_text()
        on = self.post(url, "note", {**self.SENT["note"], "on": {"id": "x", "title": "t"}})
        self.assertEqual(on["error"]["code"], -32602)
        self.assertIn("on", on["error"]["message"])
        confirm = self.post(url, "confirm", {"id": "confirm-y", "requirement": "F1", "text": "t"})
        self.assertIn("wording", confirm["error"]["message"])
        self.assertEqual((self.folder / "conversation.jsonl").read_text(), before)

    def test_an_event_of_a_capability_the_page_does_not_declare_is_refused(self):
        url = self.start_server()
        answer = self.post(url, "answer", {"id": "a-x", "decision": "D1", "text": "t", "default": False})
        self.assertEqual(answer["error"]["code"], -32601)


def better_command():
    from better import command

    return command()


def better_env():
    import os

    return {**os.environ, "BETTER_AI_SKILL": SKILL, "PYTHONUNBUFFERED": "1"}


class UnitBoundaries(unittest.TestCase):
    """The verbs refuse what is not a unit of architect-better, before reading or writing anything."""

    def test_each_verb_refuses_a_folder_that_is_not_an_architect_unit(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".git").mkdir()
            other = Path(d) / ".code" / "x"
            other.mkdir(parents=True)
            (other / "code.json").write_text("{}")
            for verb in ("review", "specs", "register", "render"):
                with self.subTest(verb=verb):
                    args = ["--perspectives", "security"] if verb == "review" else []
                    result = better_call(SKILL, verb, str(other), *args, cwd=d)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn("belongs to code-better", result.stderr)
                    self.assertEqual(sorted(p.name for p in other.iterdir()), ["code.json"])

    def test_a_unit_outside_a_unit_place_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            result = better_run(SKILL, "specs", d, cwd=d)
            self.assertEqual(result.returncode, 1)
            self.assertIn("not at a place a architect-better unit can be", result.stderr)


class ToolsAreOnlyThePackage(unittest.TestCase):
    def test_the_skill_folder_holds_no_scripts_schemas_or_example(self):
        skill = ROOT / "skills" / "architect-better"
        for name in (
            "schemas",
            "scripts/example",
            "scripts/example.json",
            "scripts/architect.py",
            "scripts/diagram.py",
        ):
            self.assertFalse((skill / name).exists(), name)
        left = [p for p in (skill / "scripts").rglob("*") if p.is_file()] if (skill / "scripts").exists() else []
        self.assertEqual([p for p in left if p.suffix in (".py", ".html", ".css", ".js", ".json")], [])

    def test_the_package_does_not_import_another_skill(self):
        for path in PACKAGE.glob("*.py"):
            text = path.read_text()
            for other in ("code", "design", "research", "show"):
                self.assertNotRegex(text, rf"from \.\.{other}\b|import better_ai\.{other}\b", path.name)
        shutil.which("node")  # the page script is checked by `node --check` in CI


if __name__ == "__main__":
    unittest.main()
