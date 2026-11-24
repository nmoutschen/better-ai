"""discover-better: the live page's server side: what it registers, what it loads, and what the agent tracks.

Run with `python3 tests/run.py test_discover_page`. Each test names the requirement it checks. The page's own script and
markup are tested in tests/discover_page.test.js.
"""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
import better  # noqa: E402
import discover_populated as P  # noqa: E402
import discover_records as R  # noqa: E402

from better_ai import discover, page, paths, resources, schema  # noqa: E402
from better_ai.discover import pagespec, rules_moves, summary  # noqa: E402

PAGE_EVENTS = ("choose", "add_evidence", "add_result", "remove", "edit", "redact")


def unit_of(folder: Path):
    return paths.resolve_unit(str(folder), discover.SKILL)


class Registered(unittest.TestCase):
    def test_the_page_is_on_the_shared_shell(self):
        """S84: the page registers with the shared side column (the at-work list) and the shared decision question."""
        spec = page.PAGES["discover-better"]
        self.assertEqual(spec.main, "discover/page.html")
        self.assertEqual(spec.aside, "page/agents.html")
        self.assertEqual(spec.capabilities, ("decisions",))
        self.assertEqual(spec.agent, "coordinator")
        self.assertEqual(spec.events, "discover-events.schema.json")
        for url in (*spec.css, *spec.js):
            self.assertTrue(resources.exists(spec.assets[url]), url)

    def test_the_page_may_send_each_discover_event_and_answers(self):
        """S58: every discover event the page sends is a method of the page, and `answer` and `note` too."""
        sendable = page.PAGES["discover-better"].sendable()
        for name in (*PAGE_EVENTS, "answer", "note"):
            self.assertIn(name, sendable)

    def test_every_discover_event_is_tracked_so_pending_lists_it(self):
        """S58: after each event is saved, `pending` lists it until the coordinator marks it done."""
        spec = page.PAGES["discover-better"]
        for name in PAGE_EVENTS:
            self.assertIn(name, spec.tracked(), name)
        with tempfile.TemporaryDirectory() as tmp:
            unit = unit_of(P.populated(Path(tmp)))
            conv = page.Conversation(unit, spec, page.load_docs(discover.SKILL))
            for name in PAGE_EVENTS:
                conv.append(R.event(name, id=f"x-{name}"))
            listed = {e["id"] for e, _, _ in page.open_items(conv.events(), conv.items, conv.agent)}
            for name in PAGE_EVENTS:
                self.assertIn(f"x-{name}", listed, name)
            conv.append({"type": "status", "at": R.AT, "by": R.COORD, "to": "x-choose", "status": "done"})
            listed = {e["id"] for e, _, _ in page.open_items(conv.events(), conv.items, conv.agent)}
            self.assertNotIn("x-choose", listed)
            self.assertIn("x-redact", listed)


class Loaded(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = P.populated(Path(self.tmp.name))
        self.unit = unit_of(self.folder)

    def test_S56_the_last_word_of_each_agent_at_work_is_served_from_summary_and_counts_sources(self):
        data = pagespec.load(self.unit)
        working = {i["checker"] for i in data["items"] + data["tests"] if i.get("checker")}
        working |= {e["verifier"] for e in data["evidence"] if e.get("verifier")}
        self.assertEqual(set(data["last_word"]), working)
        agent = sorted(working)[0]
        at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        source = {
            "type": "source",
            "at": at,
            "by": agent,
            "id": f"S-{agent}-9",
            "origin": {"type": "web", "url": "https://example.com/"},
            "title": "t",
        }
        (self.folder / "sources" / f"S-{agent}-9.json").write_text(json.dumps(source))
        self.assertEqual(pagespec.load(self.unit)["last_word"][agent], at)

    def test_the_payload_holds_every_record_and_what_the_records_derive(self):
        data = pagespec.load(self.unit)
        self.assertEqual(data["head"]["idea"], R.HEAD["idea"])
        p1 = next(i for i in data["items"] if i["id"] == "P1")
        self.assertEqual((p1["state"], p1["recorded_state"]), ("risk accepted", "supported"))
        self.assertEqual(p1["accepted_risks"], ["R1"])
        self.assertEqual(data["chosen"], "K1")
        self.assertEqual([m["id"] for m in data["moves"]], ["M1"])
        self.assertEqual([t["id"] for t in data["tests"]], ["X1"])
        self.assertEqual([d["id"] for d in data["decisions"]], ["D1"])
        self.assertEqual([b["id"] for b in data["briefs"]], ["v1"])
        self.assertEqual({e["id"] for e in data["evidence"]}, {"E-a1-1", "E-coord-1", "E-coord-2"})
        self.assertEqual([e["id"] for e in data["conversation"]], ["a1"])

    def test_each_option_carries_the_revision_the_move_rule_checks(self):
        """S37: the page sends the hash `rules_moves.revision_in` computes, so a choose event passes the rule."""
        data = pagespec.load(self.unit)
        self.assertEqual(data["revisions"], {"K1": rules_moves.revision_in(self.folder, "K1")})
        self.assertRegex(data["revisions"]["K1"], r"^[0-9a-f]{64}$")

    def test_a_choose_event_with_the_loaded_revision_is_recorded_and_a_stale_one_is_refused(self):
        """S37: end to end, through `add`: the event the page sends holds a revision the move rule accepts."""
        for item in (self.folder / "moves.jsonl",):
            item.write_text("")
        revision = pagespec.load(self.unit)["revisions"]["K1"]
        events = self.folder / "conversation.jsonl"
        lines = [json.dumps(R.event("choose", id="c1", option="K1", revision=revision, confirmed=False))]
        lines.append(json.dumps(R.event("choose", id="c2", option="K1", revision="0" * 64, confirmed=False)))
        events.write_text(events.read_text() + "\n".join(lines) + "\n")
        move = {k: v for k, v in R.MOVE.items() if k not in ("type", "at", "by", "id")}
        fresh = better.call(
            R.SKILL,
            "add",
            ".discover/d",
            "move",
            "--by",
            R.COORD,
            stdin=json.dumps({**move, "answer": {"type": "page", "event": "c1"}}),
            cwd=self.folder.parents[1],
        )
        self.assertEqual(fresh.returncode, 0, fresh.stdout + fresh.stderr)
        stale = better.call(
            R.SKILL,
            "add",
            ".discover/d",
            "move",
            "--by",
            R.COORD,
            stdin=json.dumps({**move, "answer": {"type": "page", "event": "c2"}}),
            cwd=self.folder.parents[1],
        )
        self.assertNotEqual(stale.returncode, 0)
        self.assertIn("changed since", stale.stdout + stale.stderr)

    def test_a_choice_uses_the_option_seen_before_a_concurrent_edit(self):
        moves = self.folder / "moves.jsonl"
        moves.write_text("")
        option_file = self.folder / "options.jsonl"
        option = json.loads(option_file.read_text())
        edited = "A different option after an edit."
        read_records = schema.read_records

        def read_then_edit(unit, relative, *args, **kwargs):
            found = read_records(unit, relative, *args, **kwargs)
            if relative == "options.jsonl":
                P.write_lines(option_file, [{**option, "text": edited}])
            return found

        with patch.object(schema, "read_records", side_effect=read_then_edit):
            payload = pagespec.load(self.unit)
        self.assertEqual(payload["options"][0]["text"], option["text"])
        conv = page.Conversation(self.unit, pagespec.SPEC, page.load_docs(discover.SKILL))
        conv.append(R.event("choose", id="c1", option="K1", revision=payload["revisions"]["K1"], confirmed=False))
        move = R.without(R.MOVE, "type", "at", "by", "id")
        move["answer"] = {"type": "page", "event": "c1"}
        done = R.run(self.folder.parents[1], "add", ".discover/d", "move", "--by", R.COORD, stdin=json.dumps(move))
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("changed since", done.stdout + done.stderr)
        self.assertEqual(moves.read_text(), "")

    def test_page_brief_and_copy_warning_use_the_latest_valid_evidence_event(self):
        latest = "The revised evidence is three lost weeks."
        invalid = "An incomplete event supplied different words."
        events = self.folder / "conversation.jsonl"
        with events.open("a", encoding="utf-8") as log:
            log.write(json.dumps(R.event("add_evidence", id="a1", text=latest)) + "\n")
            log.write(json.dumps(R.without(R.event("add_evidence", id="a1", text=invalid), "source")) + "\n")
        data = pagespec.load(self.unit)
        words = next(record["text"] for record in data["evidence"] if record["id"] == "E-coord-2")
        done = R.run(self.folder.parents[1], "brief", ".discover/d", "v1")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        brief = (self.folder / "brief" / "v1.md").read_text()
        items = self.folder / "items.jsonl"
        problem, behaviour = (json.loads(line) for line in items.read_text().splitlines())
        P.write_lines(items, [problem, {**behaviour, "text": latest}])
        data = pagespec.load(self.unit)
        discovery = summary.Discovery(
            self.unit,
            items=data["items"],
            conversation=data["conversation"],
            evidence=[json.loads((self.folder / "evidence" / "E-coord-2.json").read_text())],
        )
        with self.subTest(reader="page"):
            self.assertEqual(words, latest)
        with self.subTest(reader="brief"):
            self.assertIn(latest, brief)
            self.assertNotIn(P.EVENT_TEXT, brief)
        with self.subTest(reader="copy warning"):
            warnings = summary.warnings_of(discovery, datetime.now(timezone.utc))
            self.assertIn(("evidence-text-copied", "E-coord-2"), [(w.code, w.about) for w in warnings])

    def test_the_words_of_evidence_given_on_the_page_come_from_its_event(self):
        data = pagespec.load(self.unit)
        words = {e["id"]: e["text"] for e in data["evidence"]}
        self.assertEqual(words["E-coord-2"], P.EVENT_TEXT)
        self.assertEqual(words["E-a1-1"], "We lost a week to this.")
        by_id = {e["id"]: e for e in data["evidence"]}
        self.assertEqual(by_id["E-coord-2"]["origin"]["type"], "you")
        self.assertEqual(by_id["E-a1-1"]["origin"]["type"], "web")
        self.assertEqual(by_id["E-a1-1"]["source_title"], R.SOURCE["title"])

    def test_the_text_of_a_final_brief_is_read_and_a_draft_has_none(self):
        data = pagespec.load(self.unit)
        self.assertIsNone(data["briefs"][0]["text"])
        (self.folder / "brief").mkdir()
        (self.folder / "brief" / "v1.md").write_text("# The brief\n\nShrink first.\n")
        lines = [json.loads(x) for x in (self.folder / "briefs.jsonl").read_text().splitlines()]
        lines[0].update(status="final", file="brief/v1.md", sha256="a" * 64)
        (self.folder / "briefs.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
        data = pagespec.load(self.unit)
        self.assertEqual(data["briefs"][0]["text"], "# The brief\n\nShrink first.\n")

    def test_a_record_that_fails_its_schema_is_listed_and_still_on_the_page(self):
        lines = (self.folder / "items.jsonl").read_text().splitlines()
        bad = json.loads(lines[0])
        bad["kind"] = "wish"
        (self.folder / "items.jsonl").write_text("\n".join([json.dumps(bad), lines[1]]) + "\n")
        data = pagespec.load(self.unit)
        self.assertTrue(any(e["file"] == "items.jsonl" and e["field"] == "kind" for e in data["errors"]))
        self.assertIn("P1", [i["id"] for i in data["items"]])

    def test_a_unit_with_no_records_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = pagespec.load(unit_of(R.made_unit(Path(tmp))))
        self.assertEqual(
            (data["items"], data["moves"], data["evidence"], data["revisions"], data["errors"]), ([], [], [], {}, [])
        )
        self.assertEqual(data["chosen"], None)


class SharedParts(unittest.TestCase):
    def test_the_page_has_no_agents_renderer_of_its_own(self):
        """S84, S102: the at-work list is the shared `pageAgents` and the shared markup; discover has no copy of either."""
        script = resources.read_text("discover/page.js")
        style = resources.read_text("discover/page.css")
        self.assertIn("pageAgents(", script)
        self.assertNotIn('class="agents', script)
        self.assertNotIn(".agents", style)
        self.assertNotIn(".agentsec", style)

    def test_the_page_defines_no_copy_of_a_shared_component(self):
        script = resources.read_text("discover/page.js")
        style = resources.read_text("discover/page.css")
        for shared in (".chip", ".tbl", ".tabs", ".decide", ".intro", ".rec", ".btn"):
            self.assertNotRegex(style, r"(^|\n)" + shared.replace(".", r"\.") + r"\s*[{,]", shared)
        for name in ("pageDecision(", "pageConversation(", "pageEscape"):
            self.assertIn(name, script)


if __name__ == "__main__":
    unittest.main()
