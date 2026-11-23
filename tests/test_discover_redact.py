"""discover-better: the `redact` verb removes a person's words from a discovery (S48, S49, S50, S51, S52, S86).

Run with `python3 tests/run.py test_discover_redact`. The unit is built by `discover_populated.populated`, and every
brief is made by the `brief` verb, as it is in use.
"""

import hashlib
import http.server
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
import discover_populated as P  # noqa: E402
import discover_records as R  # noqa: E402

from better_ai.discover import brief  # noqa: E402

CHAT = "E-coord-1"
PAGE = "E-coord-2"


def lines_of(path):
    return [json.loads(x) for x in path.read_text().splitlines()]


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.unit = P.populated(self.root)

    def verb(self, *args, root=None, unit=None):
        root, unit = root or self.root, unit or self.unit
        return R.run(root, *args[:1], str(unit.relative_to(root)), *args[1:])

    def redact(self, evidence=CHAT, request="d1", **kw):
        return self.verb("redact", evidence, "--request", request, **kw)

    def ask_on_the_page(self, evidence=CHAT, ident="d1"):
        with (self.unit / "conversation.jsonl").open("a") as log:
            log.write(json.dumps(R.event("redact", id=ident, evidence=evidence)) + "\n")

    def ask_in_the_chat(self, evidence=CHAT, text=None, ident="D2"):
        decisions = self.unit / "decisions.jsonl"
        with decisions.open("a") as log:
            log.write(
                json.dumps(
                    R.record(
                        R.DECISION,
                        id=ident,
                        about={"type": "evidence", "evidence": evidence},
                        asked=f"Remove {evidence}?",
                        status="answered",
                        answer={"type": "chat", "text": text or f"remove {evidence}"},
                        answered_at=R.AT,
                    )
                )
                + "\n"
            )

    def brief_final(self):
        done = self.verb("brief", "v1")
        self.assertEqual(done.returncode, 0, done.stderr)

    def everything(self, unit=None):
        unit = unit or self.unit
        return "\n".join(p.read_bytes().decode("utf-8", "replace") for p in sorted(unit.rglob("*")) if p.is_file())


class Request(Fixture):
    def test_S48_no_request_the_wrong_request_or_a_missing_one_refuses_and_writes_nothing(self):
        self.brief_final()
        before = P.files_under(self.unit)
        no_flag = self.verb("redact", CHAT)
        self.assertEqual(no_flag.returncode, 2)  # argparse: --request is required
        for request in ("d1", "nothing"):
            with self.subTest(request=request):
                done = self.redact(request=request)
                self.assertEqual(done.returncode, 1)
                self.assertIn("--request", done.stderr)
                self.assertEqual(P.files_under(self.unit), before)
        self.ask_on_the_page(evidence=PAGE)  # a request about other evidence
        before = P.files_under(self.unit)
        self.assertEqual(self.redact().returncode, 1)
        self.assertEqual(P.files_under(self.unit), before)

    def test_S48_a_request_must_come_from_the_user_not_from_an_agent(self):
        event = R.event("redact", by="coordinator")
        (self.unit / "conversation.jsonl").write_text(json.dumps(event) + "\n")
        before = P.files_under(self.unit)
        self.assertEqual(self.redact().returncode, 1)
        self.assertEqual(P.files_under(self.unit), before)

    def test_S48_a_decision_that_is_waiting_or_answered_in_other_words_is_not_a_request(self):
        for text in ("Keep it.", "remove E-a1-1"):
            self.ask_in_the_chat(text=text, ident="D2")
            self.assertEqual(self.redact(request="D2").returncode, 1)
            (self.unit / "decisions.jsonl").write_text(
                "".join(x for x in (self.unit / "decisions.jsonl").read_text().splitlines(True) if '"D2"' not in x)
            )
        waiting = R.record(
            R.DECISION, id="D3", about={"type": "evidence", "evidence": CHAT}, asked="Remove it?", status="waiting"
        )
        with (self.unit / "decisions.jsonl").open("a") as log:
            log.write(json.dumps(waiting) + "\n")
        self.assertEqual(self.redact(request="D3").returncode, 1)

    def test_S48_a_page_that_answers_must_be_closed_first_and_the_refusal_names_the_pid(self):
        self.ask_on_the_page()

        class Quiet(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), Quiet)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        address = f"http://127.0.0.1:{server.server_address[1]}/"
        (self.unit / ".server").write_text(address)
        before = P.files_under(self.unit)
        done = self.redact()
        self.assertEqual(done.returncode, 1)
        self.assertIn("close the page, then run again", done.stderr)
        self.assertIn(f"pid {os.getpid()}" if shutil.which("lsof") else "pid not known", done.stderr)
        self.assertEqual(P.files_under(self.unit), before)
        server.shutdown()  # the page is closed; the file it leaves behind does not stop a redact
        done = self.redact()
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_S52_a_request_made_in_the_chat_is_the_fixed_text_remove_and_the_id(self):
        self.ask_in_the_chat()
        record = lines_of(self.unit / "decisions.jsonl")[-1]
        self.assertEqual(record["answer"], {"type": "chat", "text": f"remove {CHAT}"})
        self.assertEqual(R.run(self.root, "check", str(self.unit.relative_to(self.root))).returncode, 0)
        done = self.redact(request="D2")
        self.assertEqual(done.returncode, 0, done.stderr)


class Removal(Fixture):
    def test_S49_the_words_and_the_name_are_gone_from_the_whole_unit(self):
        self.brief_final()
        self.assertIn(P.GIVEN, self.everything())
        self.ask_on_the_page(evidence=CHAT)
        done = self.redact()
        self.assertEqual(done.returncode, 0, done.stderr)
        text = self.everything()
        for words in (P.GIVEN, "Dana from payments"):
            self.assertNotIn(words, text)
        evidence = json.loads((self.unit / "evidence" / f"{CHAT}.json").read_text())
        self.assertEqual(evidence["status"], "removed")
        self.assertIn("d1", evidence["reason"])
        self.assertEqual(evidence["words"], {"type": "quote", "text": "[removed]"})
        self.assertEqual(evidence["summary"], "[removed]")
        for key in ("checked_read", "span", "sha256", "since"):
            self.assertNotIn(key, evidence)
        source = json.loads((self.unit / "sources" / "S-coord-1.json").read_text())
        self.assertEqual(source["origin"]["given"], {"type": "chat", "text": "[removed]"})
        self.assertEqual(source["said_by_role"], "a teammate on payments")  # a role is not a person's words
        self.assertEqual(R.run(self.root, "check", str(self.unit.relative_to(self.root))).returncode, 0)

    def test_S49_the_event_that_holds_the_words_is_emptied_and_its_line_stays(self):
        self.ask_on_the_page(evidence=PAGE)
        with (self.unit / "conversation.jsonl").open("a") as log:
            log.write(
                json.dumps({"type": "note", "at": R.AT, "by": "user", "id": "n1", "text": "hello", "to": None}) + "\n"
            )
        before = lines_of(self.unit / "conversation.jsonl")
        done = self.redact(evidence=PAGE)
        self.assertEqual(done.returncode, 0, done.stderr)
        after = lines_of(self.unit / "conversation.jsonl")
        self.assertEqual(len(after), len(before))
        self.assertEqual(after[0]["id"], "a1")
        self.assertEqual((after[0]["text"], after[0]["source"]), ("[removed]", "[removed]"))
        self.assertEqual(after[1:], before[1:])
        raw = (self.unit / "conversation.jsonl").read_text()
        self.assertNotIn("Dana", raw)
        self.assertEqual(R.run(self.root, "check", str(self.unit.relative_to(self.root))).returncode, 0)

    def test_S49_words_held_by_a_result_event_are_emptied_too(self):
        """A source of the user's points to the add_result event that holds the words; check accepts every record."""
        source = json.loads((self.unit / "sources" / "S-coord-2.json").read_text())
        source["origin"]["given"]["event"] = "r1"
        P.write_json(self.unit / "sources" / "S-coord-2.json", source)
        evidence = json.loads((self.unit / "evidence" / f"{PAGE}.json").read_text())
        evidence["words"] = {"type": "quote", "text": "A team found it fast."}  # event words must be an add_evidence
        P.write_json(self.unit / "evidence" / f"{PAGE}.json", evidence)
        with (self.unit / "conversation.jsonl").open("a") as log:
            log.write(json.dumps(R.event("add_result", text="Dana's team found it fast.")) + "\n")
            log.write(json.dumps(R.event("redact", id="d1", evidence=PAGE)) + "\n")
        self.assertEqual(R.run(self.root, "check", str(self.unit.relative_to(self.root))).returncode, 0)
        self.assertEqual(self.redact(evidence=PAGE).returncode, 0)
        self.assertNotIn("Dana's team", self.everything())
        self.assertEqual(R.run(self.root, "check", str(self.unit.relative_to(self.root))).returncode, 0)

    def result(self, evidence=(CHAT,), text="Dana's team found it fast."):
        done = {"text": text, "outcome": "holds", "evidence": list(evidence)}
        P.write_lines(self.unit / "tests.jsonl", [R.record(R.TEST, status="done", result=done)])

    def test_D16_the_text_of_a_result_that_cites_the_evidence_is_emptied_in_the_tests(self):
        self.result()
        self.brief_final()
        self.assertIn("Dana's team", (self.unit / "brief" / "v1.md").read_text())
        self.ask_on_the_page()
        done = self.redact()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertNotIn("Dana's team", self.everything())
        (test,) = lines_of(self.unit / "tests.jsonl")
        self.assertEqual(test["result"], {"text": "[removed]", "outcome": "holds", "evidence": [CHAT]})
        self.assertIn("tests.jsonl:1", done.stdout)
        self.assertEqual(R.run(self.root, "check", str(self.unit.relative_to(self.root))).returncode, 0)

    def test_D16_a_result_that_cites_other_evidence_is_left_alone(self):
        self.result(evidence=("E-a1-1",))
        self.ask_on_the_page()
        self.assertEqual(self.redact().returncode, 0)
        self.assertIn("Dana's team", (self.unit / "tests.jsonl").read_text())

    def test_D21_evidence_from_a_file_or_a_tool_is_redactable_in_an_external_discovery(self):
        for origin in ({"type": "file", "path": "notes/call.md", "read": "raw"}, {"type": "tool", "tool": "tickets", "ref": "T-1", "read": "raw"}):
            with self.subTest(origin=origin["type"]):
                self.setUp()
                P.write_json(
                    self.unit / "sources" / "S-a1-2.json",
                    R.record(R.SOURCE, id="S-a1-2", origin=origin, said_by_role="a customer"),
                )
                found = R.record(
                    R.COUNTING,
                    id="E-a1-2",
                    source="S-a1-2",
                    words={"type": "quote", "text": "Acme Corp told us it took a week."},
                    summary="a customer lost a week",
                )
                P.write_json(self.unit / "evidence" / "E-a1-2.json", found)
                self.brief_final()
                self.assertNotIn("Acme", (self.unit / "brief" / "v1.md").read_text())  # shown by role, not as quoted
                self.ask_on_the_page(evidence="E-a1-2")
                self.assertEqual(self.redact(evidence="E-a1-2").returncode, 0)
                self.assertNotIn("Acme", self.everything())
                self.assertEqual(json.loads((self.unit / "evidence" / "E-a1-2.json").read_text())["status"], "removed")

    def test_S49_a_leftover_draft_file_and_an_orphan_temporary_file_do_not_keep_the_block(self):
        self.brief_final()
        text = (self.unit / "brief" / "v1.md").read_text()
        (self.unit / "brief" / "v2.md").write_text(text)  # a draft whose run stopped after it linked the file
        (self.unit / "brief" / ".v3.md.0123456789abcdef.tmp").write_text(text)  # a run that stopped before it linked
        (self.unit / "brief" / "notes.md").write_text("nothing about the evidence\n")
        self.ask_on_the_page()
        done = self.redact()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertNotIn(P.GIVEN, self.everything())
        self.assertEqual((self.unit / "brief" / "notes.md").read_text(), "nothing about the evidence\n")
        self.assertIn("brief/v2.md", done.stdout)
        self.assertIn("brief/.v3.md.0123456789abcdef.tmp", done.stdout)

    def test_L3_an_evidence_id_with_a_trailing_newline_is_refused(self):
        self.assertEqual(self.redact(evidence=CHAT + "\n").returncode, 1)

    def test_S49_each_final_brief_gets_the_block_replaced_in_place_and_a_new_hash(self):
        self.brief_final()
        path = self.unit / "brief" / "v1.md"
        old = path.read_text()
        old_hash = hashlib.sha256(old.encode()).hexdigest()
        self.ask_on_the_page()
        done = self.redact()
        self.assertEqual(done.returncode, 0, done.stderr)
        new = path.read_text()
        self.assertNotIn(f"<!-- {CHAT} -->", new)
        self.assertIn("[removed]", new)
        start = old.index(f"<!-- {CHAT} -->")
        end = old.index(f"<!-- /{CHAT} -->") + len(f"<!-- /{CHAT} -->")
        self.assertEqual(new, old[:start] + "[removed]" + old[end:])  # in place, nothing else re-rendered
        (record,) = lines_of(self.unit / "briefs.jsonl")
        self.assertEqual(record["sha256"], hashlib.sha256(new.encode()).hexdigest())
        self.assertEqual(record["redacted"], [old_hash])
        self.assertEqual(self.verb("brief", "v1").returncode, 0)  # the version is still final and its hash matches

    def test_S49_the_output_names_each_file_and_line_and_the_stale_states_it_caused(self):
        self.brief_final()
        self.ask_on_the_page(evidence="E-a1-1")
        done = self.redact(evidence="E-a1-1")
        self.assertEqual(done.returncode, 0, done.stderr)
        out = done.stdout
        for place in ("brief/v1.md:", "briefs.jsonl:1", "evidence/E-a1-1.json:"):
            self.assertIn(place, out)
        self.assertIn("P1", out.split("stale", 1)[1] if "stale" in out else "")
        self.assertIn("add a change for P1", out)

    def test_S49_evidence_that_was_removed_before_is_still_emptied(self):
        evidence = json.loads((self.unit / "evidence" / f"{CHAT}.json").read_text())
        evidence["status"] = "removed"
        evidence["reason"] = "Wrong person."
        P.write_json(self.unit / "evidence" / f"{CHAT}.json", evidence)
        self.ask_on_the_page()
        self.assertEqual(self.redact().returncode, 0)
        self.assertNotIn(P.GIVEN, self.everything())

    def test_S86_the_end_names_where_copies_may_remain(self):
        discover = json.loads((self.unit / "discover.json").read_text())
        discover["handed"] = {"brief": "brief/v1.md", "to": "design-better", "at": R.AT}
        P.write_json(self.unit / "discover.json", discover)
        self.brief_final()
        self.ask_on_the_page()
        out = self.redact().stdout
        tail = out[out.index("Copies may remain") :]
        for place in ("brief/v1.md", "design-better", "git history", "session transcripts", "model provider"):
            self.assertIn(place, tail)

    def test_S86_without_a_handed_brief_the_list_still_names_the_other_places(self):
        self.ask_on_the_page()
        out = self.redact().stdout
        self.assertIn("git history", out)
        self.assertIn("none recorded", out)


class Stopping(Fixture):
    def expected(self):
        clean = self.root / "clean"
        clean.mkdir()
        unit = P.populated(clean)
        self.assertEqual(R.run(clean, "brief", str(unit.relative_to(clean)), "v1").returncode, 0)
        with (unit / "conversation.jsonl").open("a") as log:
            log.write(json.dumps(R.event("redact", id="d1", evidence=PAGE)) + "\n")
        done = R.run(clean, "redact", str(unit.relative_to(clean)), PAGE, "--request", "d1")
        self.assertEqual(done.returncode, 0, done.stderr)
        return P.files_under(unit), done.stdout

    def start(self):
        self.brief_final()
        self.ask_on_the_page(evidence=PAGE)

    def test_S50_a_kill_after_each_place_and_a_rerun_finish_the_same_result(self):
        files, out = self.expected()
        self.start()
        places = []

        def spy(place):
            places.append(place)

        with mock.patch.object(brief, "_after_place", spy):
            self.assertEqual(self.redact(evidence=PAGE).returncode, 0)
        self.assertGreaterEqual(len(places), 5)
        for number in range(len(places)):
            with self.subTest(place=places[number]):
                self.setUp()
                self.start()
                count = [0]

                def killed(place, number=number, count=count):
                    if count[0] == number:
                        raise KeyboardInterrupt
                    count[0] += 1

                with mock.patch.object(brief, "_after_place", killed):
                    self.assertEqual(self.redact(evidence=PAGE).returncode, 130)
                self.assertTrue((self.unit / brief.STATE).exists())
                rerun = self.redact(evidence=PAGE)
                self.assertEqual(rerun.returncode, 0, rerun.stderr)
                self.assertFalse((self.unit / brief.STATE).exists())
                self.assertEqual(rerun.stdout, out)  # a rerun prints each place, also those the killed run did
                self.assertEqual(P.files_under(self.unit), files)

    def test_S50_a_failure_part_way_exits_non_zero_until_a_rerun_finishes(self):
        self.start()

        def fails(place):
            raise OSError("disk full")

        with mock.patch.object(brief, "_after_place", fails):
            done = self.redact(evidence=PAGE)
        self.assertEqual(done.returncode, 1)
        self.assertIn("partly done: run redact again", done.stderr)
        self.assertTrue((self.unit / brief.STATE).exists())
        self.assertEqual(self.redact(evidence=PAGE).returncode, 0)
        self.assertFalse((self.unit / brief.STATE).exists())

    def test_S50_a_state_file_for_other_evidence_must_be_finished_first(self):
        self.start()
        with mock.patch.object(brief, "_after_place", mock.Mock(side_effect=KeyboardInterrupt)):
            self.redact(evidence=PAGE)
        self.ask_on_the_page(evidence=CHAT, ident="d9")
        done = self.redact(request="d9")
        self.assertEqual(done.returncode, 1)
        self.assertIn(PAGE, done.stderr)
        self.assertIn("partly done: run redact again", done.stderr)

    def test_S51_serve_refuses_while_a_redact_state_file_exists_and_not_after(self):
        self.start()
        with mock.patch.object(brief, "_after_place", mock.Mock(side_effect=KeyboardInterrupt)):
            self.redact(evidence=PAGE)
        stopped = self.verb("serve", "--once")
        self.assertEqual(stopped.returncode, 1)
        self.assertIn("redact", stopped.stderr)
        self.assertIn(PAGE, stopped.stderr)
        self.assertEqual(self.redact(evidence=PAGE).returncode, 0)
        after = self.verb("serve", "--once")
        self.assertNotIn("redact", after.stderr)


if __name__ == "__main__":
    unittest.main()
