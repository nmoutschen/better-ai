"""Exercise the driver with a controllable protocol peer and a scratch unit."""

import json
import os
import queue
import sys
import tempfile
import threading
import time
import unittest
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@dataclass
class Event:
    kind: str
    session_id: str | None = None
    outcome: str | None = None
    text: str = ""
    turn_id: str | None = None


class Peer:
    pid = None
    stderr = ""

    def __init__(self, events=(), missing=False):
        self.events = queue.Queue()
        for event in events:
            self.events.put(event)
        self.missing = missing
        self.calls = []
        self.closed = False
        self.prompt_arrived = threading.Event()

    def open(self, cwd, resume):
        self.calls.append(("open", cwd, resume))
        if self.missing and resume:
            self.events.put(Event("failed", outcome="missing-session"))
        else:
            self.events.put(Event("ready", session_id="session-1"))

    def poll(self, timeout):
        try:
            return self.events.get(timeout=timeout)
        except queue.Empty:
            return None

    def prompt(self, text):
        self.calls.append(("prompt", text))
        self.prompt_arrived.set()

    def cancel(self):
        self.calls.append(("cancel",))
        self.events.put(Event("turn_ended", outcome="cancelled"))

    def close(self):
        self.closed = True

    @property
    def prompts(self):
        return [call[1] for call in self.calls if call[0] == "prompt"]


class Unit:
    label = ".code/scratch"

    def __init__(self, path):
        self.path = Path(path)

    def target(self, relative):
        return self.path / relative


class Batch:
    def __init__(self, items, events, position):
        self.items, self.events, self.position = items, events, position

    def prompt_items(self):
        return self.items


class Conversation:
    def __init__(self, root):
        self.unit = Unit(root)
        self.items = {}
        self.events = []

    def item(self, key, status="new"):
        self.items[key] = status
        event = {"type": "comment", "id": key, "by": "user"}
        self.events.append(event)
        return event

    def delivery(self, after=0, *, carry_ids=frozenset(), recover_ids=frozenset()):
        items = [
            {"id": key, "status": status}
            for key, status in self.items.items()
            if status == "new"
            or (status == "seen" and key in carry_ids | recover_ids)
            or (status == "working" and key in recover_ids)
        ]
        return Batch(items, [e for e in self.events[after:] if e["type"] == "accept"], len(self.events))


def eventually(test):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if test():
            return
        time.sleep(0.01)
    raise AssertionError("condition did not become true")


class DriverTests(unittest.TestCase):
    def setUp(self):
        from better_ai.page import driver

        self.driver_module = driver
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.conv = Conversation(scratch.name)
        self.root = Path(scratch.name)
        self.peers = []
        self.clock = time.monotonic
        self.trigger_data = []

    def driver(self, launch=None, approvals=None):
        def recording_launch(tag, resume):
            peer = launch(tag) if launch else Peer()
            self.peers.append(peer)
            return peer

        driver = self.driver_module.Driver(
            self.conv,
            "stub",
            recording_launch,
            skill_path="/plugins/code/SKILL.md",
            command="/usr/bin/python3 /plugins/code/better.pyz",
            cwd=self.root,
            step="review",
            handoff="Carry the user's decision forward.",
            triggers=lambda: self.trigger_data,
            approvals=approvals,
            clock=self.clock,
            valid_session=lambda key: key == "session-1",
        )
        self.addCleanup(driver.close)
        return driver

    def state(self):
        return json.loads((self.root / ".driver").read_text())

    def records(self):
        return [json.loads(line) for line in (self.root / ".driver.log").read_text().splitlines()]

    def test_idle_rpc_wakes_and_busy_action_waits(self):
        # S12, S13, S14 and S66.
        now = time.monotonic()
        self.clock = lambda: now
        driver = self.driver()
        self.assertEqual(driver.start(), "session-1")
        peer = self.peers[0]
        now += 20 * 60
        self.conv.item("untrusted")
        time.sleep(0.1)
        self.assertEqual(peer.prompts, [])
        self.conv.items["untrusted"] = "done"

        driver.enqueue(self.conv.item("first"))
        self.assertTrue(peer.prompt_arrived.wait(2))
        self.assertEqual(driver.snapshot()["state"], "working")
        driver.enqueue(self.conv.item("second"))
        time.sleep(0.1)
        self.assertEqual(len(peer.prompts), 1)
        self.conv.items["first"] = "done"
        peer.events.put(Event("turn_ended", outcome="completed"))
        eventually(lambda: len(peer.prompts) == 2)
        self.assertIn("second", peer.prompts[1])
        self.assertNotIn('"id": "first"', peer.prompts[1])

    def test_startup_delivery_and_first_prompt(self):
        # S17 and S27.
        self.conv.item("existing")
        driver = self.driver()
        driver.start()
        peer = self.peers[0]
        self.assertTrue(peer.prompt_arrived.wait(2))
        prompt = peer.prompts[0]
        for expected in (
            "/plugins/code/SKILL.md",
            ".code/scratch",
            str(self.root),
            "review",
            "Carry the user's decision forward.",
            "/usr/bin/python3 /plugins/code/better.pyz",
            "existing",
            "## Input",
            "## Output",
        ):
            self.assertIn(expected, prompt)
        metadata = json.loads((self.root / ".page-delivery").read_text())
        self.assertEqual(metadata["after"], 0)
        self.assertEqual(metadata["item_ids"], ["existing"])

    def test_end_checkpoints_and_restart_recovers_abnormal(self):
        # S16, S48, S54 and S72.
        self.conv.item("working-item")
        first = self.driver()
        first.start()
        peer = self.peers[0]
        self.assertTrue(peer.prompt_arrived.wait(2))
        self.conv.items["working-item"] = "working"
        peer.events.put(Event("failed", outcome="crashed"))
        eventually(lambda: first.snapshot()["state"] == "failed")
        self.assertEqual(self.state()["delivered"], 0)
        first.close()

        # Simulate a crash whose last turn start was persisted but whose end was not.
        last_start = [record for record in self.records() if record.get("items") == ["working-item"]][0]
        last_start.pop("end", None)
        (self.root / ".driver.log").write_text(json.dumps(last_start) + "\n")
        self.trigger_data.append({"id": "trigger-1"})
        resumed = self.driver()
        resumed.start()
        peer = self.peers[-1]
        self.assertEqual(peer.calls[0], ("open", str(self.root), "session-1"))
        self.assertTrue(peer.prompt_arrived.wait(2))
        self.assertIn("sent before in turn 1, which ended: crashed", peer.prompts[0])
        self.assertIn("Carry the user's decision forward.", peer.prompts[0])
        self.conv.items["working-item"] = "done"
        peer.events.put(Event("turn_ended", outcome="completed"))
        eventually(lambda: self.state()["delivered"] == 1)
        self.assertEqual(self.state()["fired"], ["trigger-1"])

    def test_normal_end_retries_seen_and_leaves_working(self):
        # S41.
        self.conv.item("seen")
        self.conv.item("working")
        driver = self.driver()
        driver.start()
        peer = self.peers[0]
        self.assertTrue(peer.prompt_arrived.wait(2))
        self.conv.items.update(seen="seen", working="working")
        peer.events.put(Event("turn_ended", outcome="completed"))
        eventually(lambda: len(peer.prompts) == 2)
        self.assertIn('"id": "seen"', peer.prompts[1])
        self.assertNotIn('"id": "working"', peer.prompts[1])

    def test_raw_append_during_completed_turn_does_not_wake(self):
        self.conv.item("first")
        driver = self.driver()
        driver.start()
        peer = self.peers[0]
        self.assertTrue(peer.prompt_arrived.wait(2))
        self.conv.items["first"] = "working"
        self.conv.item("direct")
        peer.events.put(Event("turn_ended", outcome="completed"))
        eventually(lambda: self.state()["delivered"] >= 1)
        time.sleep(0.15)
        self.assertEqual(len(peer.prompts), 1)

    def test_recovery_names_only_the_interrupted_batch(self):
        self.conv.item("first")
        driver = self.driver()
        driver.start()
        peer = self.peers[0]
        self.assertTrue(peer.prompt_arrived.wait(2))
        self.conv.items["first"] = "working"
        driver.enqueue(self.conv.item("second"))
        peer.events.put(Event("turn_ended", outcome="completed"))
        eventually(lambda: len(peer.prompts) == 2)
        self.conv.items["second"] = "working"
        peer.events.put(Event("failed", outcome="crashed"))
        eventually(lambda: driver.snapshot()["state"] == "failed")
        driver.request_start()
        eventually(lambda: self.peers[-1] is not peer and self.peers[-1].prompts)
        prompt = self.peers[-1].prompts[0]
        self.assertNotIn("first", prompt)
        self.assertIn("second: sent before in turn 2, which ended: crashed", prompt)

    def test_interrupted_turn_survives_rotated_history(self):
        self.conv.item("open-item")
        driver = self.driver()
        driver.start()
        self.assertTrue(self.peers[0].prompt_arrived.wait(2))
        self.conv.items["open-item"] = "working"
        # Restore the exact state a killed serve left before its graceful cleanup.
        checkpoint = (self.root / ".driver").read_bytes()
        driver.close()
        (self.root / ".driver").write_bytes(checkpoint)
        (self.root / ".driver.log").write_text("")
        resumed = self.driver()
        resumed.start()
        self.assertTrue(self.peers[-1].prompt_arrived.wait(1))
        self.assertIn("open-item: sent before in turn 1, which ended: crashed", self.peers[-1].prompts[0])

    def test_stop_interrupts_restarting_peer(self):
        class NoHandshake(Peer):
            def open(self, cwd, resume):
                self.calls.append(("open", cwd, resume))

        driver = self.driver(launch=lambda tag: NoHandshake() if self.peers else Peer())
        driver.start()
        driver.request_stop()
        eventually(lambda: driver.snapshot()["state"] == "stopped")
        driver.request_start()
        eventually(lambda: len(self.peers) == 2 and self.peers[-1].calls)
        driver.request_stop()
        eventually(lambda: self.peers[-1].closed)
        self.assertEqual(driver.snapshot()["state"], "stopped")

    def test_stderr_bytes_without_newline_are_output(self):
        script = "import os,sys; os.write(2, b'progress'); sys.stdin.read()"
        peer = self.driver_module.ProcessTransport(
            [sys.executable, "-c", script], self.root, os.environ, lambda _: None
        )
        self.addCleanup(peer.close)
        event = peer.poll(1)
        self.assertEqual(getattr(event, "kind", None), "output")
        self.assertIn("progress", peer.stderr)

    def test_handshake_and_stop_denials_are_audited(self):
        def approval(key):
            return SimpleNamespace(kind="approval", request_id=key, tool="Write", arguments={"path": "example"})

        class Requests(Peer):
            def cancel(self):
                self.events.put(approval("last"))
                super().cancel()

            def answer(self, request_id, choice, reason):
                self.calls.append((request_id, choice, reason))

        self.conv.item("one")
        driver = self.driver(launch=lambda _: Requests([approval("first")]))
        driver.start()
        self.assertTrue(self.peers[0].prompt_arrived.wait(2))
        driver.request_stop()
        eventually(lambda: driver.snapshot()["state"] == "stopped")
        records = [r for r in self.records() if r["type"] == "approval"]
        self.assertEqual([(r["request"], r["answer"]) for r in records], [("first", "deny"), ("last", "deny")])

    def test_failed_batch_uses_all_three_automatic_retries(self):
        self.conv.item("same")
        driver = self.driver()
        driver.start()
        for attempt in range(4):
            eventually(lambda attempt=attempt: len(self.peers) == attempt + 1 and self.peers[-1].prompts)
            self.peers[-1].events.put(Event("failed", outcome="crashed"))
            eventually(lambda: driver.snapshot()["state"] == "failed")
            self.assertEqual(driver.snapshot()["kind"], "crashed")
            driver.enqueue({"type": "accept", "id": "elsewhere"})
        time.sleep(0.15)
        self.assertEqual(len(self.peers), 4)

    def test_ignored_items_fail_with_diagnostics(self):
        # S18 and S60.
        self.conv.item("ignored")
        driver = self.driver()
        driver.start()
        peer = self.peers[0]
        for attempt in range(1, 4):
            eventually(lambda attempt=attempt: len(peer.prompts) == attempt)
            peer.events.put(Event("turn_ended", outcome="completed", text="No further work"))
        eventually(lambda: driver.snapshot()["state"] == "failed")
        state = driver.snapshot()
        self.assertEqual(state["kind"], "not-handling")
        self.assertEqual(state["items"], ["ignored"])
        self.assertEqual(state["final_message"], "No further work")
        self.assertEqual(state["denied"], [])
        self.assertEqual(state["log"], str(self.root / ".driver.log"))
        self.assertEqual((self.root / ".driver.log").stat().st_mode & 0o777, 0o600)

    def test_log_discards_oldest_records_and_keeps_complete_lines(self):
        from better_ai.page.driver_state import MAX_LOG, store_log

        records = [{"number": index, "text": "x" * (MAX_LOG // 3)} for index in range(5)]
        store_log(self.conv.unit, records)
        self.assertLessEqual((self.root / ".driver.log").stat().st_size, MAX_LOG)
        self.assertEqual(self.records(), records[-2:])

    def test_stop_waits_for_cancel_and_requires_start(self):
        # S19, S20, S32 and S54.
        driver = self.driver()
        self.conv.item("original")
        driver.start()
        peer = self.peers[0]
        self.assertTrue(peer.prompt_arrived.wait(2))
        self.conv.items["original"] = "working"
        self.assertFalse(driver.can_linger())
        driver.request_stop()
        eventually(lambda: driver.snapshot()["state"] == "stopped")
        self.assertIn(("cancel",), peer.calls)
        self.assertTrue(peer.closed)
        driver.enqueue(self.conv.item("later"))
        eventually(lambda: driver.snapshot()["waiting"])
        self.assertFalse(driver.can_linger())
        self.assertEqual(len(self.peers), 1)
        driver.request_start()
        eventually(lambda: len(self.peers) == 2 and self.peers[-1].prompts)
        self.assertIn("do not resume stopped work unless the user asks", self.peers[-1].prompts[0])

    def test_crash_retries_on_event_only_and_at_most_three_times(self):
        # S21.
        driver = self.driver()
        self.conv.item("first")
        driver.start()
        for index in range(4):
            eventually(lambda index=index: len(self.peers) == index + 1 and self.peers[-1].prompts)
            self.peers[-1].events.put(Event("failed", outcome="crashed"))
            eventually(lambda: driver.snapshot()["state"] == "failed")
            self.assertEqual(len(self.peers), index + 1)
            driver.enqueue(self.conv.item(f"after-{index}"))
        time.sleep(0.2)
        self.assertEqual(len(self.peers), 4)
        driver.request_start()
        eventually(lambda: len(self.peers) == 5 and self.peers[-1].prompts)

    def test_login_and_limit_fail_until_start(self):
        # S42.
        for kind in ("login", "limit"):
            with self.subTest(kind=kind):
                self.conv.item(kind)
                driver = self.driver()
                driver.start()
                peer = self.peers[-1]
                self.assertTrue(peer.prompt_arrived.wait(2))
                peer.events.put(Event("failed", outcome=kind))
                eventually(lambda driver=driver, kind=kind: driver.snapshot().get("kind") == kind)
                driver.enqueue(self.conv.item("after-" + kind))
                time.sleep(0.1)
                self.assertIs(peer, self.peers[-1])
                driver.request_start()
                eventually(lambda peer=peer: self.peers[-1] is not peer and self.peers[-1].prompts)
                driver.close()

    def test_silence_stalls_without_cancelling(self):
        # S22.
        now = time.monotonic()
        self.clock = lambda: now
        self.conv.item("silent")
        driver = self.driver()
        driver.start()
        peer = self.peers[-1]
        self.assertTrue(peer.prompt_arrived.wait(2))
        now += 601
        eventually(lambda: driver.snapshot()["state"] == "stalled")
        self.assertFalse(peer.closed)
        self.assertNotIn(("cancel",), peer.calls)

    def test_missing_session_opens_a_new_session(self):
        # S30.
        first = self.driver()
        first.start()
        first.close()
        driver = self.driver(launch=lambda tag: Peer(missing=True))
        driver.start()
        peer = self.peers[-1]
        self.assertTrue(self.peers[-2].closed)
        self.assertIn(("open", str(self.root), "session-1"), self.peers[-2].calls)
        self.assertIn(("open", str(self.root), None), peer.calls)
        self.assertEqual(self.state()["session"], "session-1")

    def test_autonomous_turn_blocks_another_prompt(self):
        # S49.
        driver = self.driver()
        driver.start()
        peer = self.peers[0]
        peer.events.put(Event("turn_started", turn_id="background"))
        eventually(lambda: driver.snapshot()["state"] == "working")
        driver.enqueue(self.conv.item("new"))
        time.sleep(0.1)
        self.assertEqual(peer.prompts, [])
        peer.events.put(Event("turn_ended", outcome="completed", turn_id="background"))
        self.assertTrue(peer.prompt_arrived.wait(2))
        self.assertTrue(any(record.get("turn_id") == "background" for record in self.records()))

    def test_driver_exception_is_visible_and_cleans_up(self):
        # S62.
        driver = self.driver()
        driver.start()
        self.assertEqual(driver.snapshot()["state"], "idle")
        self.conv.delivery = lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("broken"))
        driver.enqueue(self.conv.item("bad"))
        eventually(lambda: driver.snapshot()["state"] == "failed")
        self.assertEqual(driver.snapshot()["kind"], "driver")
        self.assertTrue(self.peers[0].closed)

    @unittest.skipUnless(os.name == "posix", "process groups are POSIX")
    def test_transport_pipe_and_group_lifecycle(self):
        # S29, S36 and the shutdown cleanup used by S47.
        class Codec:
            def __init__(self, send):
                self.send = send

            def receive(self, message):
                return (SimpleNamespace(kind="child", pid=message["child"]),)

        script = (
            "import json, os, subprocess, sys;"
            "assert not sys.stdin.isatty();"
            "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']);"
            "print(json.dumps(dict(child=child.pid)),flush=True);"
            "sys.stdin.read()"
        )
        transport = self.driver_module.ProcessTransport([sys.executable, "-c", script], self.root, os.environ, Codec)
        self.addCleanup(transport.close)
        event = transport.poll(2)
        self.assertEqual(event.kind, "child")
        self.assertEqual(os.getpgid(transport.pid), transport.pid)
        if sys.platform in ("darwin", "linux"):
            from better_ai.page.transport import process_birth

            self.assertTrue(transport.started)
            self.assertEqual(process_birth(transport.pid), transport.started)
            self.assertNotEqual(process_birth(os.getpid()), transport.started)
        self.assertEqual(os.getpgid(event.pid), transport.pid)
        started = time.monotonic()
        transport.close()
        self.assertLess(time.monotonic() - started, 2)
        with self.assertRaises(ProcessLookupError):
            os.kill(transport.pid, 0)

        # The sleeping worker inherits both pipes. Readers reach EOF only after it exits.
        self.assertTrue(all(not reader.is_alive() for reader in transport._readers))


if __name__ == "__main__":
    unittest.main()
