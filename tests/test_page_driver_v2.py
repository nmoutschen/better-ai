"""The driver's state, liveness and failure handling (task T4 of the page protocol)."""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_page_driver import Conversation, Event, Peer, eventually  # noqa: E402

FIELDS = {
    "version",
    "harness",
    "session",
    "server_pid",
    "server_started",
    "child_pid",
    "child_argv",
    "opened",
    "delivered",
    "note",
    "fired",
    "handoff_delivered",
    "turn",
    "ended",
}


def approval(key=1, requester=None, tool="Write", arguments=None):
    return SimpleNamespace(
        kind="approval",
        request_id=key,
        tool=tool,
        arguments=arguments or {"path": "example"},
        options=("allow_once", "deny"),
        requester=requester,
    )


def gone(pid, wait=2.0):
    """True once pid no longer runs. A killed grandchild can stay a zombie until init reaps it: that counts as gone."""
    deadline = time.monotonic() + wait
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
        if state.startswith("Z"):
            return True
        if time.monotonic() > deadline:
            return False
        time.sleep(0.05)


class Answering(Peer):
    def answer(self, request_id, choice, reason):
        self.calls.append(("answer", request_id, choice, reason))
        return True


class Silent(Peer):
    """Ignores the cancel, like a stuck harness."""

    def cancel(self):
        self.calls.append(("cancel",))


class Case(unittest.TestCase):
    def setUp(self):
        from better_ai.page import driver

        self.module = driver
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.conv = Conversation(scratch.name)
        self.peers = []
        self.clock = time.monotonic
        self.triggers = []
        self.workers = []

    def driver(self, launch=None, harness="stub", paired=True, **options):
        if not (self.root / ".driver").exists():
            # A session that was opened earlier is resumed: a new one starts with a turn of its own (S93).
            self.saved()

        def recording_launch(tag, resume):
            peer = launch(tag) if launch else Peer()
            self.peers.append(peer)
            return peer

        driver = self.module.Driver(
            self.conv,
            harness,
            recording_launch,
            skill_path="/plugins/code/SKILL.md",
            command="/usr/bin/python3 /plugins/code/better.pyz",
            cwd=self.root,
            step="review",
            triggers=lambda: self.triggers,
            workers=lambda: self.workers,
            clock=lambda: self.clock(),
            valid_session=lambda key: key == "session-1",
            **options,
        )
        self.addCleanup(driver.close)
        if paired:
            driver.tab_paired()
        return driver

    def state(self):
        return json.loads((self.root / ".driver").read_text())

    def records(self, kind=None):
        lines = (self.root / ".driver.log").read_text().splitlines()
        return [r for r in map(json.loads, lines) if kind is None or r["type"] == kind]

    def saved(self, **fields):
        from better_ai.page.driver_state import save_state

        save_state(self.conv.unit, {"harness": "stub", "session": "session-1", "opened": 1.0, **fields})


class StateTests(Case):
    def test_state_holds_exactly_the_fields_of_version_1(self):
        # S150
        driver = self.driver()
        driver.start()
        state = self.state()
        self.assertEqual(
            set(state) - {"tag"}, FIELDS
        )  # tag: the name the page agent's verbs carry, for the verbs' notice
        self.assertEqual(state["tag"], driver.tag)
        self.assertEqual(state["version"], 1)
        self.assertEqual(set(state["ended"]), {"at", "reason", "kind", "build", "repeats"})
        self.assertEqual(state["server_pid"], os.getpid())
        self.assertEqual((self.root / ".driver").stat().st_mode & 0o777, 0o600)

    def test_rewrite_gives_missing_fields_defaults_and_keeps_unknown_fields(self):
        # S124
        (self.root / ".driver").write_text(json.dumps({"version": 1, "harness": "stub", "extra": {"a": 1}}))
        os.chmod(self.root / ".driver", 0o600)
        self.driver().start()
        state = self.state()
        self.assertEqual(set(state) - FIELDS - {"tag"}, {"extra"})
        self.assertEqual(state["extra"], {"a": 1})
        self.assertEqual(state["fired"], [])

    def test_load_state_is_none_when_absent_foreign_or_open_to_others(self):
        # S59
        from better_ai.page import driver_state

        unit = self.conv.unit
        self.assertIsNone(driver_state.load_state(unit))
        self.saved()
        self.assertEqual(driver_state.load_state(unit)["session"], "session-1")
        with mock.patch.object(driver_state.os, "getuid", return_value=os.getuid() + 1):
            self.assertIsNone(driver_state.load_state(unit))
        os.chmod(self.root / ".driver", 0o644)
        self.assertIsNone(driver_state.load_state(unit))

    def test_forged_state_opens_a_new_session(self):
        # S59
        self.saved()
        os.chmod(self.root / ".driver", 0o644)
        self.driver().start()
        self.assertEqual(self.peers[0].calls[0], ("open", str(self.root), None))

    def test_resume_only_a_session_this_driver_opened_in_the_same_harness(self):
        # S48, S131. One driver owns .driver at a time (decision D2): each ends before the next state is written,
        # since a new session's first turn (S93) writes .driver after start returns.
        self.saved()
        driver = self.driver()
        driver.start()
        self.assertEqual(self.peers[-1].calls[0], ("open", str(self.root), "session-1"))
        driver.close()
        self.saved(opened=0)
        driver = self.driver()
        driver.start()
        self.assertEqual(self.peers[-1].calls[0], ("open", str(self.root), None))
        driver.close()
        self.saved(harness="codex")
        self.driver().start()
        self.assertEqual(self.peers[-1].calls[0], ("open", str(self.root), None))

    def test_delivered_position_follows_the_event_id(self):
        # S125
        from better_ai.page.driver_state import delivered_field, delivered_position

        events = [{"id": f"e{n}"} for n in range(5)]
        field = delivered_field(3, events)
        self.assertEqual(field, {"id": "e2", "position": 3})
        self.assertEqual(delivered_position(field, events), 3)
        self.assertEqual(delivered_position(field, [{"id": "x"}, {"id": "e2"}]), 2)
        self.assertEqual(delivered_position(field, [{"id": "x"}]), 1)
        self.assertEqual(delivered_position({"id": None, "position": 4}, events), 4)

    def test_log_reset_under_a_live_state_recomputes_the_position(self):
        # S125
        self.conv.log.extend({"type": "comment", "id": f"e{n}", "by": "user"} for n in range(4))
        self.saved(delivered={"id": "e1", "position": 4})
        driver = self.driver()
        driver.start()
        self.assertEqual(driver._delivered, 2)

    def test_turn_is_set_when_a_prompt_is_sent_and_cleared_at_a_normal_end(self):
        # S153
        self.conv.item("one")
        driver = self.driver()
        driver.start()
        self.assertTrue(self.peers[0].prompt_arrived.wait(2))
        turn = self.state()["turn"]
        self.assertEqual(self.peers[0].uuids, [turn["prompt_uuid"]])
        self.assertEqual(set(turn), {"number", "prompt_uuid", "sent_at"})
        self.assertEqual(turn["number"], 1)
        self.conv.items["one"] = "done"
        self.peers[0].events.put(Event("turn_ended", outcome="completed"))
        eventually(lambda: self.state()["turn"] is None)

    def test_a_turn_left_in_the_state_is_a_crash_and_its_items_come_back(self):
        # S72
        self.conv.item("work")
        first = self.driver()
        first.start()
        self.assertTrue(self.peers[0].prompt_arrived.wait(2))
        self.conv.items["work"] = "working"
        kept = (self.root / ".driver").read_bytes()
        first.close()
        (self.root / ".driver").write_bytes(kept)
        os.chmod(self.root / ".driver", 0o600)
        resumed = self.driver()
        resumed.start()
        self.assertTrue(self.peers[-1].prompt_arrived.wait(2))
        self.assertIn(
            '"id": "work", "status": "working", "sent_before": {"turn": 1, "ended": "crashed"}',
            self.peers[-1].prompts[0],
        )

    def test_the_state_is_written_before_the_driver_serves(self):
        # S120
        self.saved(turn={"number": 4, "prompt_uuid": "u", "sent_at": 1.0})
        driver = self.driver()
        driver.start()
        state = self.state()
        self.assertIsNone(state["turn"])
        self.assertEqual(state["server_pid"], os.getpid())

    def test_each_end_of_the_harness_is_recorded_with_its_reason(self):
        # S98
        driver = self.driver()
        driver.start()
        driver.request_stop()
        eventually(lambda: self.state()["ended"]["reason"] == "stopped by the user")
        self.assertTrue(self.state()["ended"]["at"])
        driver.request_start()
        eventually(lambda: driver.snapshot()["state"] == "idle")
        self.peers[-1].events.put(Event("failed", outcome="crashed", text="boom"))
        eventually(lambda: self.state()["ended"]["reason"] == "boom")
        driver.close("stopped", "server stopped")
        self.assertEqual(self.state()["ended"]["reason"], "boom")

    def test_a_server_stop_is_recorded(self):
        # S98
        driver = self.driver()
        driver.start()
        driver.close("signal", "signal received")
        self.assertEqual(self.state()["ended"]["reason"], "signal received")

    def test_an_orphaned_child_is_ended_at_start_and_recorded(self):
        # S98
        from better_ai.page.transport import process_command

        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
        self.addCleanup(child.wait)
        self.addCleanup(child.kill)
        command = process_command(child.pid)
        self.saved(child_pid=child.pid, child_argv=command.split(" "))
        self.driver().start()
        self.assertEqual(child.wait(timeout=5), -signal.SIGTERM)
        self.assertEqual(self.state()["ended"]["reason"], "orphan ended at start")

    def test_a_process_with_another_command_line_is_left_alone(self):
        # S98
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
        self.addCleanup(child.wait)
        self.addCleanup(child.kill)
        self.saved(child_pid=child.pid, child_argv=["something", "else"])
        self.driver().start()
        self.assertIsNone(child.poll())


class LifecycleTests(Case):
    def test_a_session_that_cannot_be_resumed_is_replaced_and_why_is_logged(self):
        # S30, S111
        self.saved()
        driver = self.driver(launch=lambda tag: Peer(missing=True))
        driver.start()
        self.assertEqual(self.peers[-1].calls[0], ("open", str(self.root), None))
        self.assertTrue(self.peers[0].closed)
        self.assertTrue([r for r in self.records("error") if r["kind"] == "resume"])

    def test_a_resume_that_hangs_is_replaced_after_ten_seconds(self):
        # S111
        class Hangs(Peer):
            def open(self, cwd, resume):
                self.calls.append(("open", cwd, resume))
                if not resume:
                    self.events.put(Event("ready", session_id="session-1"))

        self.saved()
        with mock.patch.object(self.module, "RESUME_TIMEOUT", 0.3):
            self.driver(launch=lambda tag: Hangs()).start()
        self.assertEqual(self.peers[-1].calls[0], ("open", str(self.root), None))
        self.assertIn("more than 10 s", self.records("error")[0]["message"])

    def test_stop_keeps_the_mark_alive_and_shows_stopped_only_after_the_end(self):
        # S19, S100
        self.conv.item("one")
        driver = self.driver(launch=lambda tag: Silent())
        driver.start()
        self.assertTrue(self.peers[0].prompt_arrived.wait(2))
        samples = []
        stop = threading.Event()

        def sample():
            while not stop.is_set():
                samples.append((driver.snapshot(), self.peers[0].closed))
                time.sleep(0.01)

        thread = threading.Thread(target=sample)
        thread.start()
        with mock.patch.object(self.module, "STOP_TIMEOUT", 0.6):
            driver.request_stop()
            eventually(lambda: driver.snapshot()["state"] == "stopped")
        stop.set()
        thread.join()
        stopping = [snap for snap, _ in samples if snap["state"] == "stopping"]
        self.assertTrue(stopping)
        self.assertLess(max(snap["age"] for snap in stopping), 0.4)
        self.assertTrue(all(closed for snap, closed in samples if snap["state"] == "stopped"))
        self.assertIn(("cancel",), self.peers[0].calls)

    def test_a_harness_that_ignores_term_and_has_a_child_is_gone_after_close(self):
        # S19
        class Codec:
            def __init__(self, send):
                pass

            def receive(self, message):
                return (SimpleNamespace(kind="child", pid=message["child"]),)

        script = (
            "import json, signal, subprocess, sys;"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN);"
            "child=subprocess.Popen([sys.executable,'-c','import signal,time; signal.signal(15,signal.SIG_IGN); time.sleep(60)']);"
            "print(json.dumps(dict(child=child.pid)),flush=True);"
            "time.sleep(60) if False else sys.stdin.read() and None;"
            "import time; time.sleep(60)"
        )
        transport = self.module.ProcessTransport([sys.executable, "-c", script], self.root, os.environ, Codec)
        child = transport.poll(3).pid
        started = time.monotonic()
        transport.close()
        self.assertLess(time.monotonic() - started, 5)
        for pid in (transport.pid, child):
            self.assertTrue(gone(pid), f"process {pid} still runs after close")

    def test_a_planned_close_cancels_the_turn_and_publishes_closed_with_the_reason(self):
        # S47, S105
        self.conv.item("one")
        driver = self.driver()
        driver.start()
        self.assertTrue(self.peers[0].prompt_arrived.wait(2))
        driver.close("finished", "the unit finished")
        self.assertIn(("cancel",), self.peers[0].calls)
        self.assertTrue(self.peers[0].closed)
        body = driver.agent()
        self.assertEqual(body["state"], "closed")
        self.assertEqual(body["kind"], "finished")
        self.assertEqual(body["text"], "This page has closed: the unit finished.")

    def test_unknown_message_then_silence_fails_as_protocol_with_the_versions(self):
        # S112
        self.conv.item("one")
        driver = self.driver(version="9.0.1", tested="1.0 to 2.0")
        driver.start()
        self.assertTrue(self.peers[0].prompt_arrived.wait(2))
        with mock.patch.object(self.module, "PROTOCOL_TIMEOUT", 0.3):
            self.peers[0].events.put(Event("unknown"))
            eventually(lambda: driver.snapshot()["state"] == "failed")
        body = driver.agent()
        self.assertEqual(body["kind"], "protocol")
        self.assertIn("9.0.1", body["text"])
        self.assertIn("1.0 to 2.0", body["text"])

    def test_a_known_message_after_an_unknown_one_is_not_a_protocol_failure(self):
        # S112
        self.conv.item("one")
        driver = self.driver()
        driver.start()
        self.assertTrue(self.peers[0].prompt_arrived.wait(2))
        with mock.patch.object(self.module, "PROTOCOL_TIMEOUT", 0.3):
            self.peers[0].events.put(Event("unknown"))
            self.peers[0].events.put(Event("text", text="hello"))
            time.sleep(0.6)
        self.assertEqual(driver.snapshot()["state"], "working")

    def test_a_newer_harness_version_runs_and_is_logged(self):
        # S113
        driver = self.driver(version="9.9.9", tested="1.0 to 2.0")
        driver.start()
        self.assertEqual(driver.snapshot()["state"], "idle")
        line = self.records("version")[0]
        self.assertEqual((line["version"], line["tested"]), ("9.9.9", "1.0 to 2.0"))

    def test_a_write_that_does_not_finish_ends_the_harness_as_crashed(self):
        # S114
        class Codec:
            def __init__(self, send):
                self.send = send

        transport = self.module.ProcessTransport(
            [sys.executable, "-c", "import time; time.sleep(30)"], self.root, os.environ, Codec
        )
        self.addCleanup(transport.close)
        with mock.patch("better_ai.page.transport.WRITE_TIMEOUT", 0.3):
            transport.codec.send({"text": "x" * 2_000_000})
            event = transport.poll(3)
        self.assertEqual((event.kind, event.outcome), ("failed", "crashed"))

    def test_the_transport_passes_the_prompt_uuid_to_the_codec(self):
        seen = []

        class Codec:
            def __init__(self, send):
                pass

            def prompt(self, text, uuid):
                seen.append((text, uuid))

        transport = self.module.ProcessTransport(
            [sys.executable, "-c", "import time; time.sleep(30)"], self.root, os.environ, Codec
        )
        self.addCleanup(transport.close)
        transport.prompt("hello", "u-1")
        self.assertEqual(seen, [("hello", "u-1")])

    def test_the_same_error_after_start_gets_the_fixed_sentence(self):
        # S121
        self.conv.item("one")
        driver = self.driver()
        driver.start()
        self.assertTrue(self.peers[0].prompt_arrived.wait(2))
        self.peers[0].events.put(Event("failed", outcome="crashed", text="boom"))
        eventually(lambda: driver.snapshot()["state"] == "failed")
        self.assertEqual(
            driver.agent()["text"], "All agents are stopped because the harness failed: boom. Press Start to resume."
        )
        driver.request_start()
        eventually(lambda: len(self.peers) == 2 and self.peers[1].prompts)
        self.peers[1].events.put(Event("failed", outcome="crashed", text="boom"))
        eventually(lambda: (driver.agent()["text"] or "").startswith("The same error"))
        self.assertEqual(
            driver.agent()["text"], "The same error came back: boom. Fix it in a terminal, then press Start."
        )
        # Only a repeated driver error counts in ended.repeats (D11).
        self.assertEqual(self.state()["ended"]["repeats"], 0)
        self.assertEqual(self.state()["ended"]["kind"], "crashed")


class ApprovalTests(Case):
    def request(self, driver, **kwargs):
        before = len(driver.agent()["approvals"])
        self.peers[0].events.put(approval(**kwargs))
        eventually(lambda: len(driver.agent()["approvals"]) == before + 1)
        return driver.agent()["approvals"][-1]

    def test_an_open_approval_shows_waiting_with_who_tool_and_since(self):
        # S101
        driver = self.driver(launch=lambda tag: Answering())
        driver.start()
        item = self.request(driver, requester="worker-1")
        body = driver.agent()
        self.assertEqual(body["state"], "waiting")
        self.assertEqual((item["who"], item["tool"], item["summary"]), ("worker-1", "Write", "to write a file"))
        self.assertIsInstance(item["arguments"], str)
        self.assertRegex(item["since"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(item["options"], ["allow_once", "deny"])
        self.assertIn("example", item["arguments"])
        self.assertEqual(
            set(body),
            {
                "state",
                "since",
                "kind",
                "text",
                "mark_age",
                "approvals",
                "workers",
                "blocked",
                "auto_approved_once",
                "problems",
            },
        )

    def test_an_approval_has_no_deadline_and_is_relayed_after_an_hour(self):
        # S70
        now = time.monotonic()
        self.clock = lambda: now
        driver = self.driver(launch=lambda tag: Answering())
        driver.start()
        item = self.request(driver)
        now += 3600
        time.sleep(0.2)
        self.assertEqual(len(driver.agent()["approvals"]), 1)
        self.assertTrue(driver.answer_approval(item["id"], "allow_once").result(timeout=2))
        self.assertIn(("answer", 1, "allow_once", "allowed once"), self.peers[0].calls)

    def test_a_waiting_approval_prevents_a_stall(self):
        # S22
        now = time.monotonic()
        self.clock = lambda: now
        self.conv.item("one")
        driver = self.driver(launch=lambda tag: Answering())
        driver.start()
        self.assertTrue(self.peers[0].prompt_arrived.wait(2))
        self.request(driver)
        now += 601
        time.sleep(0.2)
        self.assertEqual(driver.agent()["state"], "waiting")
        self.assertNotIn(driver.agent()["state"], ("stalled", "failed"))

    def test_silence_without_an_approval_stalls_and_does_not_end_the_turn(self):
        # S22
        now = time.monotonic()
        self.clock = lambda: now
        self.conv.item("one")
        driver = self.driver()
        driver.start()
        self.assertTrue(self.peers[0].prompt_arrived.wait(2))
        now += 601
        eventually(lambda: driver.agent()["state"] == "stalled")
        self.assertEqual(
            driver.agent()["text"],
            "The agents have shown no output for 10 minutes. Press Stop to end them, or keep waiting.",
        )
        self.assertFalse(self.peers[0].closed)

    def test_stop_denies_open_approvals_with_its_reason(self):
        # S43
        driver = self.driver(launch=lambda tag: Answering())
        driver.start()
        self.request(driver)
        driver.request_stop()
        eventually(lambda: driver.snapshot()["state"] == "stopped")
        self.assertIn(("answer", 1, "deny", "stopped by the user"), self.peers[0].calls)
        self.assertEqual(driver.agent()["approvals"], [])
        record = self.records("approval")[0]
        self.assertEqual((record["answer"], record["reason"]), ("denied", "stopped by the user"))

    def test_the_harness_exiting_expires_open_approvals(self):
        # S43
        driver = self.driver(launch=lambda tag: Answering())
        driver.start()
        self.request(driver)
        self.peers[0].events.put(Event("failed", outcome="crashed", text="gone"))
        eventually(lambda: driver.snapshot()["state"] == "failed")
        self.assertEqual(driver.agent()["approvals"], [])
        self.assertEqual(self.records("approval")[0]["answer"], "expired")

    def test_a_restart_expires_approvals_the_log_left_open(self):
        # S43
        driver = self.driver(launch=lambda tag: Answering())
        driver.start()
        self.request(driver)
        kept = (self.root / ".driver.log").read_bytes()
        driver.close()
        (self.root / ".driver.log").write_bytes(kept.replace(b'"answer"', b'"x"') if b'"answer"' in kept else kept)
        os.chmod(self.root / ".driver.log", 0o600)
        again = self.driver(launch=lambda tag: Answering())
        again.start()
        self.assertEqual(again.agent()["approvals"], [])

    def test_a_turn_end_closes_only_the_approvals_of_its_own_requester(self):
        # S44
        self.conv.item("one")
        driver = self.driver(launch=lambda tag: Answering())
        driver.start()
        self.assertTrue(self.peers[0].prompt_arrived.wait(2))
        self.request(driver, key=1, requester=None)
        self.request(driver, key=2, requester="worker-1")
        self.conv.items["one"] = "done"
        self.peers[0].events.put(Event("turn_ended", outcome="completed"))
        eventually(lambda: [a["who"] for a in driver.agent()["approvals"]] == ["worker-1"])

    def test_the_options_are_the_adapters_and_the_choice_goes_to_the_harness(self):
        # B2: D5, D8, S10
        driver = self.driver(launch=lambda tag: Answering())
        driver.start()
        wide = approval(key=1)
        wide.options = ("allow_once", "allow_session", "deny")
        self.peers[0].events.put(wide)
        eventually(lambda: driver.agent()["approvals"])
        item = driver.agent()["approvals"][0]
        self.assertEqual(item["options"], ["allow_once", "allow_session", "deny"])
        self.assertTrue(driver.answer_approval(item["id"], "allow_session").result(timeout=2))
        self.assertEqual([c[:3] for c in self.peers[0].calls if c[0] == "answer"], [("answer", 1, "allow_session")])

    def test_a_choice_outside_the_events_options_is_refused(self):
        # B2
        driver = self.driver(launch=lambda tag: Answering())
        driver.start()
        item = self.request(driver)
        with self.assertRaises(ValueError):
            driver.answer_approval(item["id"], "allow_session")
        self.assertEqual(len(driver.agent()["approvals"]), 1)
        self.assertFalse([c for c in self.peers[0].calls if c[0] == "answer"])

    def test_a_repeat_after_allow_for_the_session_is_approved_and_logged(self):
        # S145: the same tool and arguments in the same session are approved without asking, and logged
        driver = self.driver(launch=lambda tag: Answering())
        driver.start()
        wide = approval(key=1)
        wide.options = ("allow_once", "allow_session", "deny")
        self.peers[0].events.put(wide)
        eventually(lambda: driver.agent()["approvals"])
        driver.answer_approval(driver.agent()["approvals"][0]["id"], "allow_session").result(timeout=2)
        again = approval(key=2)
        again.options = wide.options
        self.peers[0].events.put(again)
        eventually(lambda: ("answer", 2, "allow_once", "Allowed earlier for this session") in self.peers[0].calls)
        self.assertEqual(driver.agent()["approvals"], [])
        self.assertEqual(len(self.records("asked_again")), 1)

    def test_auto_approval_is_reported_once_it_happened(self):
        driver = self.driver(launch=lambda tag: Answering(), harness="claude", verbs=("add", "set"))
        driver.start()
        self.assertFalse(driver.agent()["auto_approved_once"])
        command = f"/usr/bin/python3 /plugins/code/better.pyz pending {self.root}"
        self.peers[0].events.put(approval(tool="Bash", arguments={"command": command}))
        eventually(lambda: driver.agent()["auto_approved_once"])

    def test_auto_mode_blocks_are_listed(self):
        driver = self.driver()
        driver.start()
        self.peers[0].events.put(
            SimpleNamespace(kind="blocked", tool="Bash", arguments={"command": "rm"}, text="risky")
        )
        eventually(lambda: driver.agent()["blocked"])
        entry = driver.agent()["blocked"][0]
        self.assertEqual((entry["tool"], entry["reason"]), ("Bash", "risky"))

    def test_the_log_has_a_line_for_each_kind_and_stays_user_only_and_capped(self):
        # S60
        self.conv.item("one")
        driver = self.driver(launch=lambda tag: Answering(), version="1.0", tested="1.0")
        driver.start()
        self.assertTrue(self.peers[0].prompt_arrived.wait(2))
        item = self.request(driver)
        driver.answer_approval(item["id"], "deny", "no").result(timeout=2)
        driver.log("pairing", result="paired")
        self.conv.items["one"] = "done"
        self.peers[0].events.put(Event("text", text="x" * 900))
        self.peers[0].events.put(Event("turn_ended", outcome="completed"))
        eventually(lambda: any("end" in r for r in self.records("turn")))
        kinds = {r["type"] for r in self.records()}
        self.assertLessEqual({"turn", "state", "approval", "pairing", "version"}, kinds)
        turn = self.records("turn")[0]
        self.assertLessEqual(len(turn["final_message"]), 500)
        self.assertLessEqual({"number", "session", "items", "start", "end", "outcome", "stderr"}, set(turn))
        approval_line = self.records("approval")[0]
        self.assertLessEqual({"tool", "arguments_sha256", "where", "answer", "reason", "wait"}, set(approval_line))
        self.assertEqual((self.root / ".driver.log").stat().st_mode & 0o777, 0o600)
        for _ in range(20):
            driver.log("filler", text="x" * 100_000)
        self.assertLessEqual((self.root / ".driver.log").stat().st_size, 1024 * 1024)


class FailureTests(Case):
    def test_an_error_in_the_loop_publishes_failed_driver_with_the_log_path(self):
        # S62
        driver = self.driver(launch=lambda tag: Answering())
        driver.start()
        self.peers[0].events.put(approval())
        eventually(lambda: driver.agent()["approvals"])
        self.conv.delivery = lambda *a, **k: (_ for _ in ()).throw(ValueError("broken"))
        driver.enqueue(self.conv.item("bad"))
        eventually(lambda: driver.snapshot()["state"] == "failed")
        body = driver.agent()
        self.assertEqual(body["kind"], "driver")
        self.assertIn("broken", body["text"])
        self.assertIn(str(self.root / ".driver.log"), body["text"])
        self.assertEqual(self.state()["ended"]["reason"], "broken")
        self.assertTrue(self.peers[0].closed)
        self.assertEqual(body["approvals"], [])
        self.assertFalse(driver.check_alive())

    def test_a_loop_that_stops_marking_is_failed_by_the_watchdog(self):
        # S62
        release = threading.Event()
        self.addCleanup(release.set)
        driver = self.driver(launch=lambda tag: Answering())
        driver.start()
        self.peers[0].events.put(approval())
        eventually(lambda: driver.agent()["approvals"])
        self.triggers = [{"id": "t"}]
        patch = mock.patch.object(self.module.Driver, "_available_triggers", lambda self: release.wait(5) or ())
        patch.start()
        self.addCleanup(patch.stop)
        time.sleep(0.5)
        self.assertTrue(driver.check_alive(limit=60))
        self.assertFalse(driver.check_alive(limit=0.3))
        body = driver.agent()
        self.assertEqual((body["state"], body["kind"]), ("failed", "driver"))
        self.assertTrue(self.peers[0].closed)
        self.assertEqual(body["approvals"], [])
        self.assertTrue(self.state()["ended"]["reason"])

    def test_a_full_disk_still_leaves_a_readable_failure(self):
        # S62
        driver = self.driver()
        driver.start()
        with mock.patch.object(self.module, "store_log", side_effect=OSError(28, "No space left on device")):
            driver.enqueue(self.conv.item("one"))
            eventually(lambda: driver.snapshot()["state"] == "failed")
        self.assertEqual(driver.agent()["kind"], "driver")
        self.assertIn("No space left", driver.agent()["text"])
        self.assertIn("No space left", driver._ended["reason"])

    def test_closing_after_a_driver_error_keeps_the_error_and_its_reason_on_the_page(self):
        # B2 of the whole-change review: serve ends a failed driver with close("driver", reason); the page keeps the
        # error's notice, not a closed one, and .driver keeps the reason.
        driver = self.driver()
        driver.start()
        with mock.patch.object(self.module, "store_log", side_effect=OSError(28, "No space left on device")):
            driver.enqueue(self.conv.item("one"))
            eventually(lambda: driver.snapshot()["state"] == "failed")
        driver.close("driver", driver.error)
        body = driver.agent()
        self.assertEqual((body["state"], body["kind"]), ("failed", "driver"))
        self.assertIn("No space left", body["text"])
        self.assertIn("No space left", self.state()["ended"]["reason"])

    def test_a_unit_removed_while_served_fails_the_driver(self):
        # S62
        driver = self.driver()
        driver.start()
        shutil.rmtree(self.root)
        eventually(lambda: driver.snapshot()["state"] == "failed")
        self.assertEqual(driver.agent()["kind"], "driver")
        self.assertTrue(self.peers[0].closed)


class LingerTests(Case):
    def test_linger_waits_for_the_turn_and_for_triggers(self):
        # S32
        self.conv.item("one")
        driver = self.driver()
        driver.start()
        self.assertTrue(self.peers[0].prompt_arrived.wait(2))
        self.assertFalse(driver.can_linger())
        self.conv.items["one"] = "done"
        self.peers[0].events.put(Event("turn_ended", outcome="completed"))
        eventually(driver.can_linger)
        self.triggers.append({"id": "t1"})
        eventually(lambda: not driver.can_linger())

    def test_an_open_approval_or_worker_keeps_the_page(self):
        # S32
        driver = self.driver(launch=lambda tag: Answering())
        driver.start()
        eventually(driver.can_linger)
        self.workers.append({"name": "w", "item": "i", "waiting": False, "silent_min": 1})
        self.assertFalse(driver.can_linger())
        self.assertEqual(driver.agent()["workers"][0]["name"], "w")

    def test_idle_limit_counts_polls_not_busy_work(self):
        # S104
        now = 1000.0
        self.clock = lambda: now
        self.workers = []
        driver = self.driver()
        driver.start()
        eventually(lambda: not driver.busy())
        now += 29 * 60
        self.assertFalse(driver.idle_expired())
        now += 2 * 60
        self.workers.append({"name": "w", "item": "i", "waiting": False, "silent_min": None})
        self.assertFalse(driver.idle_expired())
        self.workers.clear()
        self.assertTrue(driver.idle_expired())
        driver.agent()
        self.assertFalse(driver.idle_expired())

    def test_work_held_until_a_tab_pairs_does_not_keep_the_page(self):
        # S77 holds the turn until a tab pairs; with no tab, a stopped unit still lingers out (S32) and the idle limit
        # still ends the server (S104). Once a tab pairs, the held turn starts and keeps the page again.
        now = 1000.0
        self.clock = lambda: now
        self.conv.item("one")
        driver = self.driver(paired=False)
        driver.start()
        eventually(driver.can_linger)
        self.assertFalse(self.peers[0].prompt_arrived.is_set())
        now += 31 * 60
        self.assertTrue(driver.idle_expired())
        driver.tab_paired()
        self.assertTrue(self.peers[0].prompt_arrived.wait(2))
        self.assertFalse(driver.can_linger())

    def test_work_held_until_a_tab_pairs_does_not_spin_the_loop(self):
        # S77: while no tab has paired, the held turn cannot start, so the loop waits on the harness as when idle
        # instead of polling it without a timeout (a busy loop starves the server's other threads).
        class Counting(Peer):
            def poll(self, timeout):
                self.polls = getattr(self, "polls", 0) + 1
                return super().poll(timeout)

        self.conv.item("one")
        driver = self.driver(launch=lambda tag: Counting(), paired=False)
        driver.start()
        eventually(driver.can_linger)
        before = self.peers[0].polls
        time.sleep(0.5)
        self.assertLess(self.peers[0].polls - before, 50)


class RoundTwoTests(Case):
    def test_interrupted_turn_survives_a_lost_log(self):
        # B1: S72 with the log gone; the items come from .page-delivery
        self.conv.item("open-item")
        driver = self.driver()
        driver.start()
        self.assertTrue(self.peers[0].prompt_arrived.wait(2))
        self.conv.items["open-item"] = "working"
        kept = (self.root / ".driver").read_bytes()
        driver.close()
        (self.root / ".driver").write_bytes(kept)
        os.chmod(self.root / ".driver", 0o600)
        (self.root / ".driver.log").write_text("")
        os.chmod(self.root / ".driver.log", 0o600)
        (self.root / ".page-delivery").write_text(json.dumps({"item_ids": ["open-item"]}))
        self.driver().start()
        self.assertTrue(self.peers[-1].prompt_arrived.wait(2))
        self.assertIn(
            '"id": "open-item", "status": "working", "sent_before": {"turn": 1, "ended": "crashed"}',
            self.peers[-1].prompts[0],
        )

    def test_a_missing_turn_record_never_falls_back_to_an_older_turn(self):
        # B1
        self.conv.items.update({"old": "seen", "new": "working"})
        self.saved(turn={"number": 2, "prompt_uuid": "u", "sent_at": 1.0})
        older = {"type": "turn", "number": 1, "session": "session-1", "items": ["old"], "start": 1, "end": 2}
        (self.root / ".driver.log").write_text(json.dumps({**older, "outcome": "completed"}) + "\n")
        os.chmod(self.root / ".driver.log", 0o600)
        (self.root / ".page-delivery").write_text(json.dumps({"item_ids": ["new"]}))
        self.driver().start()
        self.assertTrue(self.peers[-1].prompt_arrived.wait(2))
        self.assertIn(
            '"id": "new", "status": "working", "sent_before": {"turn": 2, "ended": "crashed"}',
            self.peers[-1].prompts[0],
        )
        self.assertNotIn('"id": "old"', self.peers[-1].prompts[0])

    def test_an_unknown_message_from_a_real_transport_drives_the_protocol_failure(self):
        # B3 (lesson L1): a stub codec returns kind "unknown" through ProcessTransport
        script = (
            "import sys\n"
            'print(\'{"t": "ready"}\', flush=True)\n'
            "for line in sys.stdin:\n"
            '    print(\'{"t": "odd"}\', flush=True)\n'
        )

        class Codec:
            def __init__(self, send):
                self.send = send

            def open(self, cwd, resume):
                pass

            def prompt(self, text, uuid=None):
                self.send({"prompt": text})

            def receive(self, message):
                if message["t"] == "ready":
                    return (SimpleNamespace(kind="ready", session_id="session-1"),)
                return (SimpleNamespace(kind="unknown"),)

        self.conv.item("one")
        driver = self.driver(
            launch=lambda tag: self.module.ProcessTransport(
                [sys.executable, "-c", script], self.root, os.environ, Codec
            ),
            version="9.0.1",
            tested="1.0 to 2.0",
        )
        with mock.patch.object(self.module, "PROTOCOL_TIMEOUT", 0.4):
            driver.start()
            eventually(lambda: driver.snapshot()["state"] == "failed")
        self.assertEqual(driver.agent()["kind"], "protocol")

    def test_verb_calls_are_attached_to_the_turn_record(self):
        # B4, S60, D11
        from better_ai.page.driver_state import log_verb

        self.conv.item("one")
        driver = self.driver()
        driver.start()
        self.assertTrue(self.peers[0].prompt_arrived.wait(2))
        log_verb(self.conv.unit, "reply", 0)
        log_verb(self.conv.unit, "set", 2)
        self.conv.items["one"] = "done"
        self.peers[0].events.put(Event("turn_ended", outcome="completed"))
        eventually(lambda: any("end" in r for r in self.records("turn")))
        turn = self.records("turn")[0]
        self.assertEqual([(v["verb"], v["exit"]) for v in turn["verbs"]], [("reply", 0), ("set", 2)])
        self.assertEqual(self.records("verb"), [])
        self.assertEqual((self.root / ".driver.log").stat().st_mode & 0o777, 0o600)

    def test_log_verb_line_carries_the_current_turn_number(self):
        # B4
        from better_ai.page.driver_state import log_verb

        self.saved(turn={"number": 7, "prompt_uuid": "u", "sent_at": 1.0})
        log_verb(self.conv.unit, "pending", 0)
        line = self.records("verb")[0]
        self.assertEqual((line["verb"], line["exit"], line["turn"]), ("pending", 0, 7))

    def test_ended_has_one_writer_and_counts_only_repeated_driver_errors(self):
        # D11
        from better_ai.page.driver_state import last_ended

        def fail(build):
            driver = self.driver(build=build)
            driver.start()
            self.conv.delivery = lambda *a, **k: (_ for _ in ()).throw(ValueError("broken"))
            driver.enqueue(self.conv.item(f"x{len(self.peers)}"))
            eventually(lambda: driver.snapshot()["state"] == "failed")
            driver.close()
            self.conv.__dict__.pop("delivery")
            self.conv.items.clear()

        fail("b1")
        ended = last_ended(self.conv.unit)
        self.assertEqual(set(ended), {"at", "reason", "kind", "build", "repeats"})
        self.assertEqual((ended["kind"], ended["build"], ended["repeats"]), ("driver", "b1", 0))
        # Reaching driver: on resets the count, so a second serve that fails the same way is the first again.
        fail("b1")
        self.assertEqual(last_ended(self.conv.unit)["repeats"], 0)

    def test_the_same_driver_error_before_driver_on_counts_as_repeated(self):
        # D11: two serves in a row that end with the same driver error
        from better_ai.page.driver_state import last_ended

        def broken(tag):
            raise ValueError("boom")

        for expected in (0, 1, 2):
            driver = self.driver(launch=broken, build="b1")
            with self.assertRaises(self.module.StartError):
                driver.start()
            self.assertEqual(last_ended(self.conv.unit)["repeats"], expected)

    def test_repeats_count_within_one_serve_and_a_new_build_resets_them(self):
        # D11
        self.saved(
            ended={"at": "2026-01-01T00:00:00Z", "reason": "broken", "kind": "driver", "build": "b1", "repeats": 1}
        )
        driver = self.driver(build="b2")
        self.assertEqual(driver._ended["repeats"], 0)
        again = self.driver(build="b1")
        self.assertEqual(again._ended["repeats"], 1)

    def test_notices_name_the_harness_by_its_display_name(self):
        # N6: the page says Claude Code, not the adapter's id
        driver = self.driver(harness="claude")
        self.assertEqual(
            driver._text("failed", {"kind": "login"}),
            "All agents are stopped because Claude Code isn't logged in. Log in from a terminal, then press Start.",
        )

    def test_no_approvals_is_a_fixed_sentence_with_its_action(self):
        # N3: no word of a chat agent that listens; serving from another harness is the action
        driver = self.driver()
        self.assertEqual(
            driver._text("failed", {"kind": "no-approvals"}),
            "All agents are stopped because this harness does not send its approval requests to the page. "
            "Ask the agent in your chat to serve this page from another harness.",
        )

    def test_stopping_and_stalled_have_their_fixed_text(self):
        # D10
        driver = self.driver()
        driver.start()
        self.assertEqual(driver._text("stopping", {}), "The agents are stopping.")
        self.assertEqual(
            driver._text("stalled", {}),
            "The agents have shown no output for 10 minutes. Press Stop to end them, or keep waiting.",
        )

    def test_a_long_command_line_is_read_in_full(self):
        # N4
        from better_ai.page.transport import process_command

        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)", "x" * 900])
        self.addCleanup(child.wait)
        self.addCleanup(child.kill)
        self.assertTrue(process_command(child.pid).endswith("x" * 900))

    def test_the_writer_thread_closes_stdin(self):
        # N5
        transport = self.module.ProcessTransport(
            [sys.executable, "-c", "import time; time.sleep(30)"], self.root, os.environ, lambda send: None
        )
        transport.close()
        transport._writer.join(timeout=2)
        self.assertFalse(transport._writer.is_alive())
        self.assertTrue(transport._proc.stdin.closed)

    def test_a_process_group_that_did_not_end_is_reported(self):
        # N6
        class Stuck(Peer):
            def close(self):
                raise OSError("the harness's process group did not end")

        driver = self.driver(launch=lambda tag: Stuck())
        driver.start()
        driver.fail_driver("loop stopped")
        self.assertIn("did not end", " ".join(r.get("message", "") for r in self.records("error")))

    def test_a_broken_workers_callback_keeps_the_page(self):
        # N6
        driver = self.driver()
        driver.start()
        eventually(lambda: not driver.busy())
        driver.workers = lambda: 1 / 0
        self.assertTrue(driver.busy())
        self.assertFalse(driver.idle_expired(0))

    def test_a_delivered_position_whose_id_is_gone_is_clamped_not_reset(self):
        # N7
        from better_ai.page.driver_state import delivered_position

        events = [{"id": "a"}, {"id": "b"}]
        self.assertEqual(delivered_position({"id": "zzz", "position": 5}, events), 2)
        self.assertEqual(delivered_position({"id": "zzz", "position": 1}, events), 1)


class RoundThreeTests(Case):
    def write_log(self, *records):
        (self.root / ".driver.log").write_text("".join(json.dumps(r) + "\n" for r in records))
        os.chmod(self.root / ".driver.log", 0o600)

    def verb_calls(self):
        """Every verb call in the log: on turn records and on lines of their own."""
        on_turns = [(v["verb"], v["exit"]) for r in self.records("turn") for v in r.get("verbs", [])]
        alone = [(r["verb"], r["exit"]) for r in self.records("verb")]
        return on_turns, alone

    def test_a_verb_line_left_on_disk_is_attached_once_however_often_the_log_is_written(self):
        # S60, round 2 F1
        turn = {"type": "turn", "number": 1, "session": "session-1", "items": [], "start": 1, "end": 2}
        verb = {"type": "verb", "at": 1.5, "verb": "reply", "exit": 0, "turn": 1}
        self.write_log({**turn, "outcome": "completed"}, verb)
        driver = self.driver()
        driver.start()
        for _ in range(6):
            driver.log("pairing", event="paired")
        self.assertEqual(self.verb_calls(), ([("reply", 0)], []))

    def test_a_verb_line_before_any_turn_is_kept(self):
        # S60, round 2 F1
        self.write_log({"type": "verb", "at": 1.5, "verb": "pending", "exit": 3, "turn": None})
        driver = self.driver()
        driver.start()
        for _ in range(3):
            driver.log("pairing", event="paired")
        self.assertEqual(self.verb_calls(), ([], [("pending", 3)]))
        # A later serve reads the same log and still holds the call once.
        driver.close()
        self.driver().start()
        self.assertEqual(self.verb_calls(), ([], [("pending", 3)]))

    def test_a_verb_line_between_turns_stays_on_its_own_line(self):
        # S60, round 2 F1: no turn ran when the verb did, so no turn record takes it
        turn = {"type": "turn", "number": 1, "session": "session-1", "items": [], "start": 1, "end": 2}
        self.write_log({**turn, "outcome": "completed"}, {"type": "verb", "at": 3, "verb": "set", "exit": 0})
        driver = self.driver()
        driver.start()
        driver.log("pairing", event="paired")
        self.assertEqual(self.verb_calls(), ([], [("set", 0)]))

    def test_verb_lines_appended_while_the_driver_writes_the_log_are_never_lost(self):
        # S60, round 2 F1: log_verb appends while the driver replaces the file
        from better_ai.page.driver_state import log_verb

        driver = self.driver()
        driver.start()
        count = 150

        def verbs():
            for index in range(count):
                log_verb(self.conv.unit, f"v{index}", 0)

        def flushes():
            for _ in range(count):
                driver.log("pairing", event="paired")

        threads = [threading.Thread(target=verbs), threading.Thread(target=flushes)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        driver.log("pairing", event="paired")
        on_turns, alone = self.verb_calls()
        self.assertEqual(sorted(on_turns + alone), sorted((f"v{index}", 0) for index in range(count)))

    def test_a_known_frame_the_codec_ignores_ends_the_protocol_clock(self):
        # S112, round 2 F2: a frame that maps to no event is still a known message
        script = (
            "import sys, time\n"
            'print(\'{"t": "ready"}\', flush=True)\n'
            "for line in sys.stdin:\n"
            '    print(\'{"t": "odd"}\', flush=True)\n'
            '    print(\'{"t": "known"}\', flush=True)\n'
        )

        class Codec:
            def __init__(self, send):
                self.send = send

            def open(self, cwd, resume):
                pass

            def prompt(self, text, uuid=None):
                self.send({"prompt": text})

            def receive(self, message):
                if message["t"] == "ready":
                    return (SimpleNamespace(kind="ready", session_id="session-1"),)
                if message["t"] == "odd":
                    return (SimpleNamespace(kind="unknown"),)
                return ()

        self.conv.item("one")
        driver = self.driver(
            launch=lambda tag: self.module.ProcessTransport(
                [sys.executable, "-c", script], self.root, os.environ, Codec
            )
        )
        with mock.patch.object(self.module, "PROTOCOL_TIMEOUT", 0.4):
            driver.start()
            eventually(lambda: driver.snapshot()["state"] == "working")
            time.sleep(1.2)
            self.assertEqual(driver.snapshot()["state"], "working")

    def test_serve_records_the_orphan_it_ends_before_the_driver_starts(self):
        # S98, round 2 F3: serve ends the orphan in stop_orphan, before the driver looks
        from better_ai.page import stop_orphan
        from better_ai.page.transport import process_command

        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
        self.addCleanup(child.wait)
        self.addCleanup(child.kill)
        command = process_command(child.pid)
        self.saved(child_pid=child.pid, child_argv=command.split(" "))
        stop_orphan(self.conv.unit)
        self.assertEqual(child.wait(timeout=5), -signal.SIGTERM)
        ended = self.state()["ended"]
        self.assertEqual((ended["reason"], ended["kind"]), ("orphan ended at start", "orphan"))
        self.assertTrue(ended["at"])
        self.driver().start()
        self.assertEqual(self.state()["ended"]["reason"], "orphan ended at start")


if __name__ == "__main__":
    unittest.main()
