"""Driver delivery and turns (task T3 of the page protocol): which work a turn carries, when a turn starts, what its
prompt says, which tool calls the driver approves without asking, and the skill triggers that wake it."""

import json
import os
import re
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import test_page_shell as shell
from test_page_adapters_v2 import CODEX, SESSION, frame, open_claude, open_codex
from test_page_driver import Event, Peer, eventually, sent

from better_ai import page  # noqa: E402
from better_ai.code import SKILL as CODE  # noqa: E402
from better_ai.page import approvals, triggers  # noqa: E402
from better_ai.page import driver as driver_module
from better_ai.page.adapters import child_environment  # noqa: E402
from better_ai.paths import Unit  # noqa: E402
from better_ai.research import SKILL as RESEARCH  # noqa: E402

ARCHIVE = "/plugins/code/better.pyz"
COMMAND = f"{sys.executable} {ARCHIVE}"
AT = "2026-06-01T12:00:00Z"


def note(item, *, to=None, by="user"):
    return {"type": "note", "id": item, "to": to, "by": by, "text": item}


def status(item, state, by="coordinator"):
    return {"type": "status", "to": item, "by": by, "status": state}


def accept(item, ident="a1"):
    return {"type": "accept", "id": ident, "to": item, "by": "user"}


def approval(key=1, tool="Bash", command=None, arguments=None, requester=None):
    return SimpleNamespace(
        kind="approval",
        request_id=key,
        tool=tool,
        arguments=arguments if arguments is not None else {"command": command},
        options=("allow_once", "allow_session", "deny"),
        requester=requester,
    )


class Answering(Peer):
    def answer(self, request_id, choice, reason):
        self.calls.append(("answer", request_id, choice, reason))
        return True

    def answers(self):
        return [call for call in self.calls if call[0] == "answer"]


class Echoing(Answering):
    """Takes up each prompt as its own turn and echoes its uuid back, as Claude Code does."""

    def prompt(self, text, uuid=None):
        super().prompt(text, uuid)
        self.events.put(SimpleNamespace(kind="prompt_echoed", uuid=uuid))
        self.events.put(Event("turn_started"))


class Straying(Answering):
    """Runs a turn of its own while the prompt waits: the turn ends before any echo of the prompt."""

    def prompt(self, text, uuid=None):
        super().prompt(text, uuid)
        self.events.put(Event("turn_started"))
        self.events.put(Event("turn_ended", outcome="completed"))


class Turns(shell.Fixture):
    """A driver on a real conversation of the fixture page, and a peer to play the harness."""

    def setUp(self):
        super().setUp()
        self.peers = []
        self.clock = time.monotonic
        self.scanned = []
        self.workers = []
        for name, value in (("TRIGGER_INTERVAL", 0.05), ("TRIGGER_BUDGET", 5.0)):
            patch = mock.patch.object(driver_module, name, value)
            patch.start()
            self.addCleanup(patch.stop)

    def make(
        self, peer=Answering, *, handoff="", harness="stub", resume=True, paired=True, verbs=("add", "set"), **more
    ):
        if resume:
            # A session opened earlier is resumed; a new one starts with a turn of its own (S93).
            from better_ai.page.driver_state import save_state

            save_state(self.unit(), {"harness": harness, "session": "session-1", "opened": 1.0})

        def launch(tag, session):
            self.peers.append(peer())
            return self.peers[-1]

        driver = driver_module.Driver(
            page.Conversation(self.unit(), self.spec, self.docs),
            harness,
            launch,
            skill_path="/plugins/code/SKILL.md",
            command=COMMAND,
            cwd=self.unit_dir,
            step="review",
            handoff=handoff,
            triggers=lambda: self.scanned,
            workers=lambda: self.workers,
            verbs=verbs,
            clock=lambda: self.clock(),
            valid_session=lambda key: key == "session-1",
            **more,
        )
        self.addCleanup(driver.close)
        if paired:
            driver.tab_paired()
        driver.start()
        return driver

    def rpc(self, driver, *events):
        """What the server's /rpc handler does: append the user's event, then tell the driver."""
        self.seed(*events)
        for event in events:
            driver.enqueue(event)

    def state(self):
        return json.loads((self.unit_dir / ".driver").read_text())

    def records(self, kind):
        lines = (self.unit_dir / ".driver.log").read_text().splitlines()
        return [r for r in map(json.loads, lines) if r["type"] == kind]

    def end(self, peer, outcome="completed"):
        peer.events.put(Event("turn_ended", outcome=outcome))

    def prompts(self, count=1, peer=None):
        peer = peer or self.peers[-1]
        eventually(lambda: len(peer.prompts) >= count)
        return peer.prompts

    def quiet(self, peer=None, seconds=0.4):
        """No prompt arrives for a while."""
        peer = peer or self.peers[-1]
        before = len(peer.prompts)
        time.sleep(seconds)
        self.assertEqual(len(peer.prompts), before)


class WhatATurnCarries(Turns):
    def test_a_turn_carries_the_work_the_user_has_not_been_answered_on_and_nothing_settled_S15(self):
        self.seed(
            note("new"),
            note("replied"),
            status("replied", "asked"),
            note("answer", to="replied"),
            note("followup"),
            status("followup", "done"),
            note("more", to="followup"),
            note("reopened"),
            status("reopened", "done"),
            {"type": "reopen", "to": "reopened", "by": "user", "text": "again"},
            note("asked"),
            status("asked", "asked"),
            note("done"),
            status("done", "done"),
            note("accepted"),
            {"type": "accepted", "to": "accepted", "by": "coordinator", "text": "ok"},
            note("seen"),
            status("seen", "seen"),
            note("working"),
            status("working", "working"),
            accept("done"),
        )
        driver = self.make()
        (prompt,) = self.prompts()
        found = sent(prompt)
        self.assertEqual(
            sorted((item["id"], item["status"]) for item in found["items"]),
            sorted([("followup", "followup"), ("new", "new"), ("replied", "replied"), ("reopened", "reopened")]),
        )
        # The user's answers under items and the reopen come as events beside the items they target.
        self.assertEqual([event["type"] for event in found["user_actions"]], ["note", "note", "reopen", "accept"])
        # An item the user edits stays out while the agent has settled it, and comes in while it is working.
        self.seed(*(status(item, "done") for item in ("new", "replied", "followup", "reopened")))
        self.end(self.peers[0])
        eventually(lambda: driver.agent()["state"] == "idle")
        self.rpc(driver, {**note("done"), "text": "edited"}, {**note("working"), "text": "edited"})
        prompts = self.prompts(2)
        self.assertEqual([item["id"] for item in sent(prompts[1])["items"]], ["working"])

    def test_the_items_a_normal_turn_left_seen_come_once_more_and_working_ones_do_not_S41(self):
        self.seed(note("ignored"), note("working"))
        self.make()
        self.prompts()
        self.seed(status("ignored", "seen"), status("working", "working"))
        self.end(self.peers[0])
        prompts = self.prompts(2)
        self.assertEqual([item["id"] for item in sent(prompts[1])["items"]], ["ignored"])

    def test_the_same_items_three_turns_in_a_row_stop_the_agent_with_the_facts_S18(self):
        self.seed(note("ignored"))
        driver = self.make()
        peer = self.peers[0]
        for number in range(1, 4):
            self.prompts(number)
            peer.events.put(Event("text", text="I looked at it."))
            self.seed(status("ignored", "seen"))
            self.end(peer)
        eventually(lambda: driver.agent()["state"] == "failed")
        body = driver.agent()
        self.assertEqual(body["kind"], "not-handling")
        self.assertIn("ignored", body["text"])
        failed = self.records("state")[-1]
        self.assertEqual(failed["items"], ["ignored"])
        self.assertEqual(failed["final_message"], "I looked at it.")
        self.assertEqual(failed["denied"], [])
        self.assertTrue(failed["log"].endswith(".driver.log"))
        self.assertTrue(os.path.isabs(failed["log"]))
        self.assertEqual(len(peer.prompts), 3)

    def test_a_new_event_on_the_items_starts_the_count_again_S18(self):
        self.seed(note("ignored"))
        driver = self.make()
        peer = self.peers[0]
        for number in range(1, 6):
            self.prompts(number)
            self.seed(status("ignored", "seen"))
            if number == 2:
                self.rpc(driver, {**note("ignored"), "text": f"edit {number}"})
            self.end(peer)
        self.assertNotEqual(driver.agent()["state"], "failed")

    def test_more_than_twenty_items_come_as_ids_and_name_pending_S55(self):
        self.seed(*(note(f"m{n}") for n in range(25)))
        self.make()
        (prompt,) = self.prompts()
        found = sent(prompt)
        # Past twenty the lines hold ids only, so they are not read as items.
        self.assertEqual(found["items"], [])
        self.assertEqual(found["user_actions"], [{"id": f"m{n}"} for n in range(25)])
        self.assertIn("25 not done.", prompt)
        self.assertIn(f"pending {self.unit_dir}", prompt)
        self.assertNotIn('"text"', prompt)

    def test_the_prompt_holds_the_lines_pending_prints_S126(self):
        self.seed(note("a"), note("b"), status("b", "working"), accept("x"))
        driver = self.make()
        (prompt,) = self.prompts()
        with mock.patch.dict(os.environ, {"BETTER_PAGE_SESSION": driver.tag}):
            code, out, err = self.cli("pending", self.unit_arg)
        self.assertEqual((code, err), (0, ""))
        # The first prompt is the one turn so far: its lines are what `pending` prints for it.
        shown = [line for line in prompt.splitlines() if line.startswith("{") or line.endswith("not done.")]
        self.assertEqual(shown, out.splitlines())
        self.assertEqual(json.loads(shown[-2])["to"], "x")
        self.assertEqual(shown[-1], "1 not done.")

    def test_a_note_under_the_users_item_comes_with_its_thread_S126(self):
        self.seed(note("m1"), status("m1", "asked"), note("answer", to="m1"))
        self.make()
        (prompt,) = self.prompts()
        (item,) = sent(prompt)["items"]
        self.assertEqual((item["id"], item["status"]), ("m1", "replied"))
        self.assertEqual([message["text"] for message in item["thread"]], ["answer"])


class WhenATurnStarts(Turns):
    def test_an_action_after_twenty_idle_minutes_starts_a_turn_S12(self):
        now = time.monotonic()
        self.clock = lambda: now
        driver = self.make()
        self.quiet()
        now += 20 * 60
        began = time.monotonic()
        self.rpc(driver, note("late"))
        (prompt,) = self.prompts()
        self.assertLess(time.monotonic() - began, 30)
        self.assertEqual([item["id"] for item in sent(prompt)["items"]], ["late"])

    def test_a_trigger_that_came_during_a_turn_starts_the_next_within_five_seconds_S13(self):
        self.seed(note("first"))
        self.make()
        self.prompts()
        self.scanned = [{"id": "t1", "type": "handed_back"}]
        time.sleep(0.2)
        self.assertEqual(len(self.peers[0].prompts), 1)
        self.seed(status("first", "done"))
        began = time.monotonic()
        self.end(self.peers[0])
        prompts = self.prompts(2)
        self.assertLess(time.monotonic() - began, 5)
        self.assertEqual([t["id"] for t in sent(prompts[1])["triggers"]], ["t1"])

    def test_nothing_makes_no_model_call_for_fifteen_minutes_S14(self):
        now = time.monotonic()
        self.clock = lambda: now
        self.make()
        for _ in range(3):
            now += 5 * 60
            self.quiet(seconds=0.2)
        self.assertEqual(self.peers[0].prompts, [])

    def test_a_trigger_starts_one_turn_once_however_often_it_is_seen_S31(self):
        driver = self.make()
        self.scanned = [{"id": "t1", "type": "handed_back"}]
        prompts = self.prompts()
        self.end(self.peers[0])
        eventually(lambda: self.state()["fired"] == ["t1"])
        self.quiet()
        self.scanned = [{"id": "t1", "type": "handed_back"}, {"id": "t2", "type": "deadline"}]
        prompts = self.prompts(2)
        self.assertEqual([t["id"] for t in sent(prompts[1])["triggers"]], ["t2"])
        self.assertEqual(driver.agent()["state"], "working")

    def test_a_start_with_nothing_to_deliver_makes_no_model_call_S156(self):
        self.seed(note("done"), status("done", "done"))
        driver = self.make()
        driver.request_stop()
        eventually(lambda: driver.agent()["state"] == "stopped")
        driver.request_start()
        eventually(lambda: driver.agent()["state"] == "idle")
        self.quiet(self.peers[-1])
        self.assertEqual(self.peers[-1].prompts, [])

    def test_a_line_appended_by_anything_but_rpc_starts_no_turn_S66(self):
        self.make()
        self.seed(note("raw"))
        self.quiet()
        self.assertEqual(self.peers[0].prompts, [])

    def test_a_restart_with_a_new_comment_in_the_log_starts_a_turn_S17(self):
        driver = self.make()
        self.seed(note("while-away"))
        driver.close()
        self.make()
        (prompt,) = self.prompts()
        self.assertEqual([item["id"] for item in sent(prompt)["items"]], ["while-away"])

    def test_no_turn_starts_before_a_tab_has_paired_S77(self):
        self.seed(note("early"))
        driver = self.make(paired=False)
        self.quiet(self.peers[0], seconds=0.5)
        self.assertEqual(driver.agent()["state"], "idle")
        driver.tab_paired()
        (prompt,) = self.prompts()
        self.assertEqual([item["id"] for item in sent(prompt)["items"]], ["early"])

    def test_a_turn_the_harness_starts_by_itself_shows_working_and_blocks_a_prompt_S49(self):
        driver = self.make()
        self.peers[0].events.put(Event("turn_started", turn_id="background"))
        eventually(lambda: driver.agent()["state"] == "working")
        self.rpc(driver, note("during"))
        self.quiet(self.peers[0])
        self.end(self.peers[0])
        (prompt,) = self.prompts()
        self.assertEqual([item["id"] for item in sent(prompt)["items"]], ["during"])
        self.assertTrue(any(r.get("turn_id") == "background" for r in self.records("turn")))

    def test_a_new_session_starts_a_first_turn_with_no_comment_S93(self):
        self.make(resume=False)
        (prompt,) = self.prompts()
        self.assertIn("continue from the current step", prompt)
        self.assertEqual(sent(prompt)["items"], [])

    def test_a_resumed_session_with_a_note_starts_a_first_turn_and_one_without_does_not_S93(self):
        self.make(handoff="We agreed on A.")
        (prompt,) = self.prompts()
        self.assertIn("We agreed on A.", prompt)
        self.assertIn("continue from the current step", prompt)

    def test_the_first_prompt_holds_everything_the_agent_needs_S27(self):
        self.seed(note("m1"))
        self.make(handoff="We agreed on A.", resume=False)
        (prompt,) = self.prompts()
        for expected in (
            "/plugins/code/SKILL.md",
            self.unit().label,
            "Current step: review",
            "We agreed on A.",
            f"Verb command: {COMMAND}",
            f"Working directory: {self.unit_dir}",
            '"id": "m1"',
            "## Input",
        ):
            self.assertIn(expected, prompt)

    def test_the_hand_off_note_is_labelled_and_sent_once_S94_S148(self):
        self.make(handoff="We agreed on A.", resume=False)
        (prompt,) = self.prompts()
        self.assertRegex(
            prompt,
            r"from the chat, written \d{4}-\d\d-\d\dT[\d:]+Z; where it differs, the records and your own session are newer",
        )
        # A kill in the first turn keeps the note for the next one; a normal end retires it.
        self.peers[0].events.put(Event("failed", outcome="crashed"))
        eventually(lambda: self.state()["handoff_delivered"] is False and bool(self.state()["note"]))
        driver = self.make(handoff="")
        prompts = self.prompts(1, self.peers[-1])
        self.assertIn("We agreed on A.", prompts[0])
        self.assertIn("written", prompts[0])
        self.end(self.peers[-1])
        eventually(lambda: self.state()["handoff_delivered"] is True)
        self.seed(note("later"))
        self.rpc(driver, note("later2"))
        prompts = self.prompts(2, self.peers[-1])
        self.assertNotIn("We agreed on A.", prompts[1])

    def test_a_note_kept_from_an_earlier_serve_keeps_the_time_it_was_written_S94(self):
        first = self.make(handoff="Old agreement.", resume=False)
        (prompt,) = self.prompts()
        label = re.search(
            r"from the chat, written [^;]+; where it differs, the records and your own session are newer", prompt
        )[0]
        self.peers[0].events.put(Event("failed", outcome="crashed"))
        eventually(lambda: first.agent()["state"] == "failed")
        first.close()
        time.sleep(1.1)
        self.make(handoff="")
        again = self.prompts(1, self.peers[-1])[0]
        self.assertIn(label + ":\nOld agreement.", again)


class WhatAPromptSays(Turns):
    def test_every_prompt_starts_with_the_unit_the_approved_form_and_the_rules_S95(self):
        self.seed(note("m1"))
        driver = self.make()
        self.prompts()
        self.rpc(driver, note("m2"))
        self.end(self.peers[0])
        prompts = self.prompts(2)
        form = approvals.approved_form(COMMAND, self.unit_dir, ("add", "set"))
        for prompt in prompts:
            lines = prompt.splitlines()
            self.assertEqual(lines[0], f"Unit: {self.unit_dir}")
            self.assertEqual(lines[1], f"Approved without asking: {form}")
            self.assertIn(
                "every word for the user through reply; end the turn when the items are handled; never serve", lines[2]
            )
        self.assertTrue(os.path.isabs(prompts[0].splitlines()[0].split(": ", 1)[1]))

    def test_the_form_in_the_header_is_the_form_that_is_approved_S95(self):
        form = approvals.approved_form(COMMAND, self.unit_dir, ("add", "set"))
        for verb in approvals.verbs_of(("add", "set")):
            self.assertIn(verb, form)
        self.assertIn("quoted heredoc", form)
        self.assertIn("other than user", form)

    def test_a_turn_after_stop_marks_what_it_sends_again_and_says_not_to_resume_S54(self):
        self.seed(note("work"), accept("other"))
        driver = self.make()
        self.prompts()
        self.seed(status("work", "working"))
        driver.request_stop()
        eventually(lambda: driver.agent()["state"] == "stopped")
        driver.request_start()
        eventually(lambda: len(self.peers) == 2 and self.peers[-1].prompts)
        prompt = self.peers[-1].prompts[0]
        found = sent(prompt)
        mark = {"turn": 1, "ended": "stopped by the user"}
        self.assertEqual([(i["id"], i["sent_before"]) for i in found["items"]], [("work", mark)])
        self.assertEqual([e["sent_before"] for e in found["user_actions"]], [mark])
        self.assertIn("check the records and the working tree before acting on these again", prompt)
        self.assertIn("do not resume stopped work unless the user asks", prompt)

    def test_a_turn_after_a_crash_marks_what_it_sends_again_without_the_stop_line_S54(self):
        self.seed(note("work"), accept("other"))
        driver = self.make()
        self.prompts()
        self.peers[0].events.put(Event("failed", outcome="crashed", text="boom"))
        eventually(lambda: driver.agent()["state"] == "failed")
        driver.request_start()
        eventually(lambda: len(self.peers) == 2 and self.peers[-1].prompts)
        prompt = self.peers[-1].prompts[0]
        found = sent(prompt)
        mark = {"turn": 1, "ended": "crashed"}
        self.assertEqual([i["sent_before"] for i in found["items"]], [mark])
        self.assertEqual([e["sent_before"] for e in found["user_actions"]], [mark])
        self.assertIn("check the records and the working tree before acting on these again", prompt)
        self.assertNotIn("do not resume stopped work", prompt)

    def test_a_turn_after_a_stall_marks_it_stalled_and_a_resent_accept_too_S54(self):
        now = time.monotonic()
        self.clock = lambda: now
        self.seed(note("work"), accept("other"))
        driver = self.make()
        self.prompts()
        now += 601
        eventually(lambda: driver.agent()["state"] == "stalled")
        driver.request_stop()
        eventually(lambda: driver.agent()["state"] == "stopped")
        driver.request_start()
        eventually(lambda: len(self.peers) == 2 and self.peers[-1].prompts)
        found = sent(self.peers[-1].prompts[0])
        self.assertEqual([i["sent_before"]["ended"] for i in found["items"]], ["stalled"])
        self.assertEqual([e["sent_before"]["ended"] for e in found["user_actions"]], ["stalled"])

    def test_the_first_turn_after_a_harness_end_carries_the_working_items_S99(self):
        self.seed(note("one"), note("two"))
        driver = self.make()
        self.prompts()
        self.seed(status("one", "working"), status("two", "working"))
        self.end(self.peers[0])
        eventually(lambda: driver.agent()["state"] == "idle")
        driver.request_stop()
        eventually(lambda: driver.agent()["state"] == "stopped")
        driver.request_start()
        eventually(lambda: len(self.peers) == 2 and self.peers[-1].prompts)
        prompt = self.peers[-1].prompts[0]
        self.assertIn(
            "your harness process was ended (stopped by the user); background workers you started are gone; "
            "check the records and the working tree, then restart them or report what is unfinished",
            prompt,
        )
        self.assertEqual(sorted(i["id"] for i in sent(prompt)["items"]), ["one", "two"])
        # Only the first turn after the end carries it.
        self.end(self.peers[-1])
        self.rpc(driver, note("three"))
        prompts = self.prompts(2, self.peers[-1])
        self.assertNotIn("your harness process was ended", prompts[1])

    def test_a_crash_and_a_restart_between_turns_carry_the_working_items_too_S99(self):
        self.seed(note("one"))
        driver = self.make()
        self.prompts()
        self.seed(status("one", "working"))
        self.end(self.peers[0])
        eventually(lambda: driver.agent()["state"] == "idle")
        driver.close()
        self.make()
        (prompt,) = self.prompts()
        self.assertIn("your harness process was ended (server stopped)", prompt)
        self.assertEqual([i["id"] for i in sent(prompt)["items"]], ["one"])

    def test_a_crashed_harness_names_its_reason_to_the_next_turn_S99(self):
        self.seed(note("one"))
        driver = self.make()
        self.prompts()
        self.seed(status("one", "working"))
        self.end(self.peers[0])
        eventually(lambda: driver.agent()["state"] == "idle")
        self.peers[0].events.put(Event("failed", outcome="crashed", text="boom"))
        eventually(lambda: driver.agent()["state"] == "failed")
        driver.request_start()
        eventually(lambda: len(self.peers) == 2 and self.peers[-1].prompts)
        self.assertIn("your harness process was ended (boom)", self.peers[-1].prompts[0])

    def test_a_note_for_a_working_item_with_no_items_to_carry_gives_no_harness_line_S99(self):
        driver = self.make()
        driver.request_stop()
        eventually(lambda: driver.agent()["state"] == "stopped")
        driver.request_start()
        eventually(lambda: driver.agent()["state"] == "idle")
        self.rpc(driver, note("fresh"))
        eventually(lambda: self.peers[-1].prompts)
        self.assertNotIn("your harness process was ended", self.peers[-1].prompts[0])


class AfterABadEnd(Turns):
    def test_a_limit_or_crash_restarts_only_on_start_or_a_user_event_and_three_times_S21(self):
        self.seed(note("m0"))
        driver = self.make()
        peers = 0
        for number in range(1, 4):
            self.prompts(1, self.peers[-1])
            self.peers[-1].events.put(Event("failed", outcome="limit" if number % 2 else "crashed", text="no"))
            eventually(lambda: driver.agent()["state"] == "failed")
            peers = len(self.peers)
            self.quiet(self.peers[-1], 0.3)
            self.assertEqual(len(self.peers), peers)
            self.rpc(driver, note(f"m{number}"))
            eventually(lambda peers=peers: len(self.peers) == peers + 1 and self.peers[-1].prompts)
        self.peers[-1].events.put(Event("failed", outcome="crashed", text="no"))
        eventually(lambda: driver.agent()["state"] == "failed")
        peers = len(self.peers)
        self.rpc(driver, note("m4"))
        time.sleep(0.4)
        self.assertEqual(len(self.peers), peers)
        driver.request_start()
        eventually(lambda: len(self.peers) == peers + 1 and self.peers[-1].prompts)

    def test_a_login_failure_starts_no_turn_until_start_S42(self):
        self.seed(note("m0"))
        driver = self.make()
        self.prompts()
        self.peers[0].events.put(Event("failed", outcome="login"))
        eventually(lambda: driver.agent()["kind"] == "login")
        self.rpc(driver, note("m1"))
        time.sleep(0.4)
        self.assertEqual(len(self.peers), 1)
        driver.request_start()
        eventually(lambda: len(self.peers) == 2 and self.peers[-1].prompts)

    def test_after_stop_no_turn_starts_until_start_and_the_comment_shows_as_waiting_S20(self):
        driver = self.make()
        driver.request_stop()
        eventually(lambda: driver.agent()["state"] == "stopped")
        self.rpc(driver, note("m1"))
        self.scanned = [{"id": "t1", "type": "handed_back"}]
        time.sleep(0.4)
        self.assertEqual(len(self.peers), 1)
        self.assertEqual(self.peers[0].prompts, [])
        self.assertTrue(driver.snapshot()["waiting"])
        driver.request_start()
        eventually(lambda: len(self.peers) == 2 and self.peers[-1].prompts)
        found = sent(self.peers[-1].prompts[0])
        self.assertEqual([i["id"] for i in found["items"]], ["m1"])
        self.assertEqual([t["id"] for t in found["triggers"]], ["t1"])

    def test_after_a_stalled_turn_the_next_starts_only_on_stop_then_start_S119(self):
        now = time.monotonic()
        self.clock = lambda: now
        self.seed(note("m0"))
        driver = self.make(Peer)
        self.prompts()
        now += 601
        eventually(lambda: driver.agent()["state"] == "stalled")
        self.rpc(driver, note("m1"))
        time.sleep(0.4)
        self.assertEqual(len(self.peers[0].prompts), 1)
        driver.request_stop()
        eventually(lambda: driver.agent()["state"] == "stopped")
        self.assertEqual(len(self.peers[0].prompts), 1)
        driver.request_start()
        eventually(lambda: len(self.peers) == 2 and self.peers[-1].prompts)

    def test_a_turn_killed_midway_delivers_again_and_advances_nothing_S16(self):
        self.seed(note("m0"))
        driver = self.make()
        self.prompts()
        self.assertEqual(self.state()["delivered"]["position"], 0)
        driver.close()
        self.assertEqual(self.state()["delivered"]["position"], 0)
        self.assertEqual(self.state()["fired"], [])
        self.make()
        (prompt,) = self.prompts()
        self.assertEqual([i["id"] for i in sent(prompt)["items"]], ["m0"])

    def test_a_normal_end_advances_the_position_and_the_fired_triggers_S16(self):
        self.seed(note("m0"))
        self.scanned = [{"id": "t1", "type": "handed_back"}]
        self.make()
        self.prompts()
        self.seed(status("m0", "done"))
        self.end(self.peers[0])
        eventually(lambda: self.state()["delivered"]["position"] == 1)
        self.assertEqual(self.state()["fired"], ["t1"])
        self.assertIsNone(self.state()["turn"])


class WhichTurnsCount(Turns):
    def test_a_turn_ending_with_no_echo_of_its_prompt_advances_nothing_S97(self):
        self.scanned = [{"id": "t1", "type": "handed_back"}]
        self.seed(note("m0"))
        self.make(Straying, harness="claude")
        self.prompts()
        eventually(lambda: self.records("error"))
        self.assertEqual(self.state()["delivered"]["position"], 0)
        self.assertEqual(self.state()["fired"], [])

    def test_a_harness_that_never_echoes_stops_the_loop_with_a_clear_problem_S97(self):
        self.seed(note("m0"))
        driver = self.make(Straying, harness="claude")
        eventually(lambda: driver.agent()["state"] == "failed")
        self.assertEqual(driver.agent()["kind"], "protocol")
        self.assertEqual(len(self.peers[0].prompts), 3)

    def test_a_turn_that_echoes_its_prompt_advances_S97(self):
        self.scanned = [{"id": "t1", "type": "handed_back"}]
        self.seed(note("m0"))
        self.make(Echoing, harness="claude")
        self.prompts()
        self.seed(status("m0", "done"))
        self.end(self.peers[0])
        eventually(lambda: self.state()["delivered"]["position"] == 1)
        self.assertEqual(self.state()["fired"], ["t1"])

    def test_the_echo_of_another_uuid_is_not_this_prompts_S97(self):
        class Wrong(Answering):
            def prompt(self, text, uuid=None):
                super().prompt(text, uuid)
                self.events.put(SimpleNamespace(kind="prompt_echoed", uuid="not-mine"))

        self.seed(note("m0"))
        self.make(Wrong, harness="claude")
        self.prompts()
        self.end(self.peers[0])
        time.sleep(0.2)
        self.assertEqual(self.state()["delivered"]["position"], 0)

    def test_the_session_id_is_in_the_child_environment_S90(self):
        self.make()
        tags = []
        driver = driver_module.Driver(
            page.Conversation(self.unit(), self.spec, self.docs),
            "stub",
            lambda tag, resume: tags.append(tag) or Answering(),
            skill_path="s",
            command=COMMAND,
            cwd=self.unit_dir,
            valid_session=lambda key: True,
        )
        self.addCleanup(driver.close)
        driver.start()
        self.assertEqual(tags, [driver.tag])
        self.assertEqual(child_environment("claude", {}, driver.tag)["BETTER_PAGE_SESSION"], driver.tag)

    def test_the_hand_off_note_is_kept_until_a_turn_that_carried_it_ends_normally_S148(self):
        driver = self.make(handoff="Note.", resume=False)
        self.prompts()
        self.assertEqual(self.state()["handoff_delivered"], False)
        self.assertIn("Note.", self.state()["note"])
        self.end(self.peers[0])
        eventually(lambda: self.state()["handoff_delivered"] is True)
        self.assertEqual(driver.agent()["state"], "idle")


class TheApprovedForm(Turns):
    base = f"{COMMAND} reply {{unit}} --to m1 --state asked --by builder-t3"

    def command(self, tail="", head="reply {unit} --to m1 --state asked --by builder-t3"):
        return f"{COMMAND} " + head.format(unit=self.unit_dir) + tail

    def asked(self, driver, command, tool="Bash"):
        self.peers[0].events.put(approval(tool=tool, command=command))
        eventually(lambda: self.peers[0].answers() or driver.agent()["approvals"])

    def test_the_approved_calls_run_without_asking_per_tool_name_S9(self):
        driver = self.make()
        heredoc = " <<'EOF'\nIt's done:\nline two\nEOF"
        calls = [
            self.command(heredoc),
            self.command(" <<'END_1'\nno quote problem\nEND_1\n"),
            f"{COMMAND} pending {self.unit_dir}",
            f"{COMMAND} check {self.unit_dir}",
            f"{COMMAND} status {self.unit_dir} seen m1 m2 --by builder-t3",
            f"{COMMAND} add {self.unit_dir} progress --by builder-t3 <<'EOF'\n{{}}\nEOF",
            f"{COMMAND} set {self.unit_dir} T3 --by builder-t3 --unset note <<'EOF'\n{{}}\nEOF",
            f"{COMMAND} add {self.unit_dir} log --for builder-t3 --by builder-t3 <<'EOF'\n{{}}\nEOF",
        ]
        for number, command in enumerate(calls):
            for tool in ("Bash", "bash", "Command"):
                key = number * 10 + len(tool)
                self.peers[0].events.put(approval(key=key, tool=tool, command=command))
                eventually(lambda key=key: any(a[1] == key for a in self.peers[0].answers()))
                answer = next(a for a in self.peers[0].answers() if a[1] == key)
                self.assertEqual(answer[2:], ("allow_once", "Approved page command"), (command, tool))
        self.assertEqual(driver.agent()["approvals"], [])

    def test_the_requests_claude_code_really_sends_are_approved_or_denied_by_their_form_S9_S78(self):
        # The input of a Bash request carries description (tests/fixtures/page_wire/claude_2_1_332.json), and may carry timeout.
        _, adapter, _, _ = open_claude()
        driver = self.make()
        form = approvals.approved_form(COMMAND, self.unit_dir, ("add", "set"))
        ok = f"{COMMAND} reply {self.unit_dir} --to m1 --state done --by b <<'EOF'\nIt's done\nEOF"
        for number, (command, extra, expected) in enumerate(
            [
                (ok, {}, ("allow_once", "Approved page command")),
                (ok, {"timeout": 5000}, ("allow_once", "Approved page command")),
                (f"{COMMAND} reply .code/rel --to m1", {}, ("deny", f"not-the-approved-form: {form}")),
                (f"{COMMAND} status {self.unit_dir} accepted m1", {}, ("deny", f"not-the-approved-form: {form}")),
                (ok, {"run_in_background": True}, None),
                ("ls", {}, None),
            ]
        ):
            request = frame("bash_prefix_request", request_id=f"r{number}")
            request["request"]["input"].update({"command": command, **extra})
            (event,) = adapter.receive(request)
            self.assertIn("description", event.arguments)
            self.peers[0].events.put(event)
            if expected is None:
                eventually(lambda: len(driver.agent()["approvals"]) == 1)
                driver.answer_approval(driver.agent()["approvals"][0]["id"], "deny").result(timeout=2)
                continue
            eventually(lambda number=number: any(a[1] == f"r{number}" for a in self.peers[0].answers()))
            answer = next(a for a in self.peers[0].answers() if a[1] == f"r{number}")
            self.assertEqual(answer[2:], expected, command)

    def test_a_codex_command_request_is_asked_not_approved_or_denied_S9(self):
        # Codex sends the command wrapped in a login shell (command_request in tests/fixtures/page_wire/codex_0_172_0.json),
        # so it can never match the form and is asked on the page like any other call; Codex asks only for commands
        # outside its sandbox (the fixture's reason), not for a write inside the unit.
        _, adapter, _, _ = open_codex()
        driver = self.make()
        request = frame("command_request", CODEX)
        request["params"]["threadId"] = SESSION
        request["params"]["command"] = f"/bin/zsh -lc '{COMMAND} pending {self.unit_dir}'"
        (event,) = adapter.receive(request)
        self.peers[0].events.put(event)
        eventually(lambda: len(driver.agent()["approvals"]) == 1)
        self.assertEqual(self.peers[0].answers(), [])

    def test_the_skill_verbs_are_approved_only_where_the_skill_has_them_S9(self):
        form = lambda verb: f"{COMMAND} {verb} {self.unit_dir}"  # noqa: E731
        for verbs, verb, expected in (
            ((), "summary", False),
            (("summary",), "summary", True),
            ((), "specs", False),
            (("specs",), "specs", True),
            ((), "add", False),
        ):
            with self.subTest(verbs=verbs, verb=verb):
                self.assertIs(
                    approvals.verb_command(form(verb) + (" x" if verb == "add" else ""), self.unit_dir, ARCHIVE, verbs),
                    expected,
                )

    def test_a_call_outside_the_form_is_denied_without_asking_with_the_form_S78(self):
        driver = self.make()
        form = approvals.approved_form(COMMAND, self.unit_dir, ("add", "set"))
        bad = [
            f"{COMMAND} reply .code/rel --to m1 <<'EOF'\nx\nEOF",
            f"{COMMAND} reply {self.unit_dir} --to m1 <<<'it's'",
            f"{COMMAND} reply {self.unit_dir} --to m1 'it'\\''s'",
            f"{COMMAND} reply {self.unit_dir} --to m1\nsecond line",
            f"{COMMAND} reply {self.unit_dir} --to m1 <<'EOF'\nno end",
            f"{COMMAND} reply {self.unit_dir} --to m1 <<EOF\nx\nEOF",
            f"{COMMAND} reply {self.unit_dir} --to $(pwd)",
            f"{COMMAND} reply {self.unit_dir} --to m1; pwd",
            f"{COMMAND} reply {self.unit_dir} --to m1 > out",
            f"X=1 {COMMAND} pending {self.unit_dir}",
            f"{COMMAND} pending {self.unit_dir} | cat",
            f"{COMMAND} reply {self.unit_dir} --by user <<'EOF'\nx\nEOF",
            f"{COMMAND} add {self.unit_dir} decision --for user <<'EOF'\n{{}}\nEOF",
            f"{COMMAND} serve {self.unit_dir}",
            f"{COMMAND} status {self.unit_dir} accepted m1 --text --by builder-t3 <<'EOF'\nyes\nEOF",
            f"{COMMAND} status {self.unit_dir} accepted m1 --by builder-t3",
            f"{COMMAND} reply {self.unit_dir} --to m1 --state accepted --by builder-t3",
            f"{COMMAND} reply {self.unit_dir}/../other --to m1",
            f"/usr/bin/env {COMMAND} pending {self.unit_dir}",
        ]
        for number, command in enumerate(bad, 100):
            self.peers[0].events.put(approval(key=number, command=command))
            eventually(lambda number=number: any(a[1] == number for a in self.peers[0].answers()))
            answer = next(a for a in self.peers[0].answers() if a[1] == number)
            self.assertEqual(answer[2:], ("deny", f"not-the-approved-form: {form}"), command)
        self.assertEqual(driver.agent()["approvals"], [])
        self.assertEqual(driver.agent()["state"], "idle")

    def test_another_call_is_asked_as_before_S78(self):
        driver = self.make()
        self.peers[0].events.put(approval(command="ls"))
        self.peers[0].events.put(approval(key=2, tool="Read", arguments={"file_path": "/etc/hosts"}))
        eventually(lambda: len(driver.agent()["approvals"]) == 2)
        self.assertEqual(self.peers[0].answers(), [])

    def test_the_page_says_once_that_it_approves_the_form_S67(self):
        driver = self.make()
        self.assertFalse(driver.agent()["auto_approved_once"])
        self.peers[0].events.put(approval(command=f"{COMMAND} pending {self.unit_dir}"))
        eventually(lambda: driver.agent()["auto_approved_once"])
        self.assertTrue(driver.agent()["auto_approved_once"])

    def test_the_user_comes_before_a_tool_runs_S1(self):
        driver = self.make()
        self.peers[0].events.put(approval(key=1, tool="Write", arguments={"path": "a"}))
        eventually(lambda: driver.agent()["approvals"])
        (open_request,) = driver.agent()["approvals"]
        # An answer written into the log, or one for another id, runs nothing.
        self.seed({"type": "note", "by": "user", "id": "answer", "text": "allow", "to": None})
        self.assertFalse(driver.answer_approval("unknown", "allow_once").result(timeout=2))
        self.assertEqual(self.peers[0].answers(), [])
        # A changed argument is a new request with its own id.
        self.peers[0].events.put(approval(key=2, tool="Write", arguments={"path": "b"}))
        eventually(lambda: len(driver.agent()["approvals"]) == 2)
        ids = {a["id"] for a in driver.agent()["approvals"]}
        self.assertEqual(len(ids), 2)
        self.assertTrue(driver.answer_approval(open_request["id"], "allow_once").result(timeout=2))
        self.assertEqual([a[1] for a in self.peers[0].answers()], [1])

    def test_after_allow_for_the_session_the_same_request_is_approved_and_logged_S145(self):
        driver = self.make()
        self.peers[0].events.put(approval(key=1, tool="Write", arguments={"path": "a"}))
        eventually(lambda: driver.agent()["approvals"])
        driver.answer_approval(driver.agent()["approvals"][0]["id"], "allow_session").result(timeout=2)
        self.peers[0].events.put(approval(key=2, tool="Write", arguments={"path": "a"}))
        self.peers[0].events.put(approval(key=3, tool="Write", arguments={"path": "b"}))
        eventually(lambda: any(a[1] == 2 for a in self.peers[0].answers()))
        eventually(lambda: driver.agent()["approvals"])
        self.assertEqual([a["arguments"] for a in driver.agent()["approvals"]], ['{\n  "path": "b"\n}'])
        self.assertEqual(len(self.records("asked_again")), 1)


class SkillTriggers(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def unit(self, skill):
        kind = skill.kinds[0]
        return Unit(self.root / kind.folder / "unit", self.root, kind, skill)

    def write(self, unit, relative, *records, raw=""):
        path = unit.path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(record) + "\n" for record in records) + raw, encoding="utf-8")

    def ids(self, unit, spec_triggers=None):
        return [t["id"] for t in (spec_triggers or page.spec_of(unit.skill).triggers)(unit)]

    def line(self, by, kind, at=AT, **fields):
        return {"type": kind, "at": at, "by": by, "text": f"{kind} text", **fields}

    def test_a_trigger_id_comes_from_the_record_and_survives_a_reorder_S149(self):
        unit = self.unit(CODE)
        self.write(unit, "logs/b1.card.json", {"type": "card", "at": AT, "by": "coordinator", "role": "builder"})
        first = self.line("b1", "handed_back", result="done")
        second = self.line("b1", "handed_back", "2026-06-01T12:05:00Z", result="partly done")
        step = self.line("b1", "step")
        self.write(unit, "logs/b1.jsonl", step, first, second)
        ids = self.ids(unit)
        self.assertEqual(len(set(ids)), 2)
        self.write(unit, "logs/b1.jsonl", second, step, step, first)
        self.assertEqual(sorted(self.ids(unit)), sorted(ids))

    def test_a_line_that_cannot_be_read_is_one_trigger_once_S118(self):
        unit = self.unit(CODE)
        self.write(unit, "logs/b1.card.json", {"type": "card", "at": AT, "by": "coordinator", "role": "builder"})
        recent = (datetime.now(timezone.utc) - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.write(unit, "logs/b1.jsonl", self.line("b1", "step", recent), raw='{"type": "handed_back", "at": "2026\n')
        found = list(page.spec_of(unit.skill).triggers(unit))
        self.assertEqual([t["type"] for t in found], ["unreadable"])
        self.assertEqual((found[0]["file"], found[0]["line"]), ("logs/b1.jsonl", 2))
        self.assertEqual([t["id"] for t in page.spec_of(unit.skill).triggers(unit)], [found[0]["id"]])
        # A record that parses but breaks a rule wakes nothing.
        self.write(unit, "logs/b2.card.json", {"type": "card", "at": AT, "by": "coordinator", "role": "builder"})
        self.write(unit, "logs/b2.jsonl", self.line("b2", "handed_back", result="unknown"))
        self.assertEqual(len(list(page.spec_of(unit.skill).triggers(unit))), 1)

    def test_a_worker_with_no_end_line_is_a_row_and_a_silent_one_shows_its_silence_S116(self):
        unit = self.unit(RESEARCH)
        now = datetime(2026, 6, 1, 13, 0, tzinfo=timezone.utc)
        for name, at in (
            ("w1", "2026-06-01T12:55:00Z"),
            ("w2", "2026-06-01T12:10:00Z"),
            ("w3", "2026-06-01T12:59:00Z"),
        ):
            self.write(unit, f"logs/{name}.jsonl", {"type": "strategy", "at": at, "by": name, "text": "go"})
        self.write(unit, "logs/done.jsonl", {"type": "stop", "at": AT, "by": "done", "text": "finished"})
        rows = triggers.workers(unit, now)
        self.assertEqual(sorted((r["name"], r["silent_min"]) for r in rows), [("w1", None), ("w2", 50), ("w3", None)])
        self.assertEqual(set(rows[0]), {"name", "item", "waiting", "silent_min"})

    def test_a_silent_worker_gives_an_overdue_trigger_once_per_silence_S117(self):
        unit = self.unit(CODE)
        old = (datetime.now(timezone.utc) - timedelta(minutes=45)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.write(unit, "logs/b1.card.json", {"type": "card", "at": old, "by": "coordinator", "role": "builder"})
        self.write(unit, "logs/b1.jsonl", self.line("b1", "start", old))
        (found,) = [t for t in page.spec_of(unit.skill).triggers(unit) if t["type"] == "overdue"]
        self.assertEqual(found["worker"], "b1")
        self.assertEqual(self.ids(unit), [found["id"]])
        self.write(unit, "logs/b1.jsonl", self.line("b1", "start", old), self.line("b1", "handed_back", result="done"))
        self.assertEqual([t["type"] for t in page.spec_of(unit.skill).triggers(unit)], ["handed_back"])

    def test_a_worker_resumed_after_its_hand_back_is_running_again_S116_S117(self):
        unit = self.unit(CODE)
        self.write(unit, "logs/b1.card.json", {"type": "card", "at": AT, "by": "coordinator", "role": "builder"})

        def moment(minutes):
            return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")

        def log(*lines):
            self.write(
                unit, "logs/b1.jsonl", *(self.line("b1", kind, moment(ago), **extra) for kind, ago, extra in lines)
            )

        done = {"result": "done"}
        log(("start", 90, {}), ("handed_back", 80, done), ("start", 45, {}))
        (row,) = triggers.workers(unit)
        self.assertIn(row["silent_min"], (44, 45))
        overdue = [t for t in page.spec_of(unit.skill).triggers(unit) if t["type"] == "overdue"]
        self.assertEqual([t["worker"] for t in overdue], ["b1"])
        # Only the lines after the last hand-back count: its own age, not the first round's.
        self.assertIn(overdue[0]["silent_min"], (44, 45))
        log(("start", 90, {}), ("handed_back", 80, done), ("start", 2, {}))
        (row,) = triggers.workers(unit)
        self.assertIsNone(row["silent_min"])
        self.assertEqual([t for t in page.spec_of(unit.skill).triggers(unit) if t["type"] == "overdue"], [])
        log(("start", 90, {}), ("handed_back", 80, done))
        self.assertEqual(triggers.workers(unit), [])

    def test_a_worker_that_wrote_lately_is_not_overdue_S117(self):
        unit = self.unit(CODE)
        recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.write(unit, "logs/b1.card.json", {"type": "card", "at": recent, "by": "coordinator", "role": "builder"})
        self.write(unit, "logs/b1.jsonl", self.line("b1", "start", recent))
        self.assertEqual(self.ids(unit), [])


class TheScan(Turns):
    def test_a_slow_scan_never_stops_the_mark_and_is_logged_and_skipped_S115(self):
        def slow():
            time.sleep(0.6)
            return [{"id": "late", "type": "handed_back"}]

        patch = mock.patch.object(driver_module, "TRIGGER_BUDGET", 0.2)
        patch.start()
        self.addCleanup(patch.stop)
        self.seed(note("m0"))
        driver = self.make()
        driver.triggers = slow
        self.prompts()
        self.end(self.peers[0])
        eventually(lambda: self.records("error"))
        for _ in range(10):
            self.assertLess(driver.agent()["mark_age"], 3)
            time.sleep(0.05)
        self.assertIn("skipped", self.records("error")[-1]["message"])
        self.assertEqual(len(self.peers[0].prompts), 2)  # the retry of the seen item, never the skipped trigger
        self.assertNotIn("late", self.peers[0].prompts[-1])

    def test_the_scan_runs_off_the_loop_and_at_most_once_a_second_S115(self):
        calls = []
        patch = mock.patch.object(driver_module, "TRIGGER_INTERVAL", 1.0)
        patch.start()
        self.addCleanup(patch.stop)
        driver = self.make()
        driver.triggers = lambda: calls.append(time.monotonic()) or []
        time.sleep(2.5)
        gaps = [b - a for a, b in zip(calls, calls[1:], strict=False)]
        self.assertTrue(calls)
        self.assertTrue(all(gap >= 0.95 for gap in gaps), gaps)
        self.assertLess(driver.agent()["mark_age"], 1)

    def test_a_trigger_line_that_cannot_be_read_is_logged_once_and_starts_one_turn_S118(self):
        self.scanned = [{"id": "unreadable:x", "type": "unreadable", "file": "logs/b1.jsonl", "problem": "bad"}]
        self.make()
        (prompt,) = self.prompts()
        self.assertIn('"type": "unreadable"', prompt)
        self.end(self.peers[0])
        self.quiet()
        self.assertEqual(len(self.records("error")), 1)

    def test_the_lines_the_scan_cannot_read_are_listed_in_the_agent_body_while_they_stay_D21(self):
        driver = self.make()
        self.assertEqual(driver.agent()["problems"], [])
        self.scanned = [
            {
                "id": "unreadable:x",
                "type": "unreadable",
                "file": "logs/b1.jsonl",
                "line": 4,
                "problem": "(record): not valid JSON",
            },
            {"id": "t9", "type": "handed_back", "file": "logs/b1.jsonl"},
        ]
        eventually(lambda: driver.agent()["problems"])
        self.assertEqual(
            driver.agent()["problems"], [{"file": "logs/b1.jsonl", "line": 4, "text": "(record): not valid JSON"}]
        )
        self.prompts()
        self.end(self.peers[0])
        eventually(lambda: self.state()["fired"])
        # The turn it started is over, but the line is still unreadable, so the page still says so.
        self.assertEqual(len(driver.agent()["problems"]), 1)
        self.scanned = []
        eventually(lambda: driver.agent()["problems"] == [])

    def test_a_worker_with_an_open_approval_shows_it_is_waiting_S116(self):
        self.workers = [{"name": "builder-t1", "item": "T1", "waiting": False, "silent_min": None}]
        driver = self.make()
        self.peers[0].events.put(approval(tool="Write", arguments={"path": "a"}, requester="builder-t1"))
        eventually(lambda: driver.agent()["approvals"])
        (row,) = driver.agent()["workers"]
        self.assertTrue(row["waiting"])


class TheLog(Turns):
    def test_a_driven_session_appends_nothing_to_the_conversation_S39(self):
        self.seed(note("m0"), accept("m0"))
        before = (self.unit_dir / "conversation.jsonl").read_bytes()
        driver = self.make()
        self.prompts()
        self.peers[0].events.put(approval(tool="Write", arguments={"path": "a"}))
        eventually(lambda: driver.agent()["approvals"])
        driver.request_stop()
        eventually(lambda: driver.agent()["state"] == "stopped")
        driver.request_start()
        eventually(lambda: len(self.peers) == 2)
        self.assertEqual((self.unit_dir / "conversation.jsonl").read_bytes(), before)
        self.assertTrue((self.unit_dir / ".driver.log").exists())


if __name__ == "__main__":
    unittest.main()
