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

    def driver(self, launch=None, harness="stub", **options):
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
        self.assertEqual(set(state), FIELDS)
        self.assertEqual(state["version"], 1)
        self.assertEqual(set(state["ended"]), {"at", "reason", "repeats"})
        self.assertEqual(state["server_pid"], os.getpid())
        self.assertEqual((self.root / ".driver").stat().st_mode & 0o777, 0o600)

    def test_rewrite_gives_missing_fields_defaults_and_keeps_unknown_fields(self):
        # S124
        (self.root / ".driver").write_text(json.dumps({"version": 1, "harness": "stub", "extra": {"a": 1}}))
        os.chmod(self.root / ".driver", 0o600)
        self.driver().start()
        state = self.state()
        self.assertEqual(set(state) - FIELDS, {"extra"})
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
        # S48, S131
        self.saved()
        self.driver().start()
        self.assertEqual(self.peers[-1].calls[0], ("open", str(self.root), "session-1"))
        self.saved(opened=0)
        self.driver().start()
        self.assertEqual(self.peers[-1].calls[0], ("open", str(self.root), None))
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
        self.assertEqual(delivered_position(field, [{"id": "x"}]), 0)
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
        self.assertIn("work: sent before in turn 1, which ended: crashed", self.peers[-1].prompts[0])

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
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)

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
        self.assertEqual(self.state()["ended"]["repeats"], 1)


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
        self.assertEqual(item["options"], ["allow_once", "allow_session", "deny"])
        self.assertIn("example", item["arguments"])
        self.assertEqual(
            set(body),
            {"state", "since", "kind", "text", "mark_age", "approvals", "workers", "blocked", "auto_approved_once"},
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
        self.assertIsNone(driver.agent()["text"])
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

    def test_allow_for_the_session_approves_the_same_call_and_logs_it(self):
        # S60
        driver = self.driver(launch=lambda tag: Answering())
        driver.start()
        item = self.request(driver, key=1)
        self.assertTrue(driver.answer_approval(item["id"], "allow_session").result(timeout=2))
        self.peers[0].events.put(approval(key=2))
        eventually(lambda: ("answer", 2, "allow_once", "Allowed earlier for this session") in self.peers[0].calls)
        self.assertEqual(driver.agent()["approvals"], [])
        self.assertTrue(self.records("allowed"))

    def test_auto_approval_is_reported_once_it_happened(self):
        driver = self.driver(launch=lambda tag: Answering(), auto_approve=lambda event: True)
        driver.start()
        self.assertFalse(driver.agent()["auto_approved_once"])
        self.peers[0].events.put(approval())
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


if __name__ == "__main__":
    unittest.main()
