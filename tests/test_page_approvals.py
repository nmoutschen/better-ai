"""Exercise the paired session and request binding without opening a browser."""

import base64
import hashlib
import os
import sys
import tempfile
import unittest
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from better_ai.page.approvals import ApprovalGate, Pairing  # noqa: E402

ORIGIN = "http://localhost:54321"
RP = hashlib.sha256(b"localhost").digest()


def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


class GateTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.unit = self.root / "unit"
        self.unit.mkdir()
        self.archive = self.root / "better.pyz"
        self.archive.write_bytes(b"test archive")
        self.gate = self.make_gate(False)
        self.answers = []

    def make_gate(self, presence):
        return ApprovalGate(self.unit, archive=self.archive)

    def request(self, tool="Read", args=None, rid=1, *, tool_id="Read", callback=None):
        def delivered(answer, reason):
            self.answers.append((answer, reason))
            result = Future()
            result.set_result(True)
            return result

        event = SimpleNamespace(
            tool=tool,
            tool_id=tool_id,
            arguments={"file_path": "/tmp/example"} if args is None else args,
            request_id=rid,
            requester=None,
            options=("allow_once", "deny"),
        )
        self.gate.receive(event, callback or delivered)
        return self.gate.snapshot()["approvals"]

    def test_pairing(self):
        pairing = Pairing(ORIGIN)
        token = pairing.issue()
        with self.assertRaises(ValueError):
            pairing.exchange(token, "http://localhost:54322")
        secret = pairing.exchange(token, ORIGIN)
        self.assertTrue(pairing.valid(secret, ORIGIN))
        self.assertFalse(pairing.valid(secret, "null"))
        with self.assertRaises(ValueError):
            pairing.exchange(token, ORIGIN)
        pairing.issue()
        self.assertFalse(pairing.valid(secret, ORIGIN))

    def test_display_and_consume_once(self):
        args = {"text": "<x>\u202e" + "z" * 10000}
        (item,) = self.request("Write", args)
        args["text"] = "changed"
        self.assertIn(r"\u202e", item["arguments"])
        self.assertIn("z" * 10000, item["arguments"])
        self.gate.answer(item["id"], "deny")
        with self.assertRaisesRegex(ValueError, "den"):
            self.gate.answer(item["id"], "allow_once")
        self.assertEqual(len(self.answers), 1)

    def test_close_invalidates_waiting(self):
        (item,) = self.request()
        self.assertTrue(self.gate.waiting())
        self.gate.close("stopped by the user")
        with self.assertRaisesRegex(ValueError, "stopped by the user"):
            self.gate.answer(item["id"], "allow_once")
        self.assertEqual(self.answers, [("deny", "stopped by the user")])

    def test_session_scope(self):
        for tool, args in [
            ("Bash", {"command": "pwd"}),
            ("Read", {"file_path": "~/.claude/settings.json"}),
            ("Write", {"file_path": str(self.unit / "doc")}),
        ]:
            (item,) = self.request(tool, args, tool_id=tool)
            self.assertNotIn("allow_session", item["options"])
            self.gate.answer(item["id"], "deny")
        (item,) = self.request()
        self.gate.answer(item["id"], "allow_session")
        self.assertEqual(self.request(), [])
        self.assertEqual(self.answers[-1][0], "allow_once")
        self.gate.close("restart")
        self.assertTrue(self.request())

    def test_verb_scope(self):
        base = f"{sys.executable} {self.archive} pending {self.unit}"
        self.assertEqual(self.request("Bash", {"command": base}, tool_id="Bash"), [])
        self.assertTrue(self.gate.snapshot()["notice"])
        for command in [base + "; pwd", base + " >file", "X=1 " + base, base + " $(pwd)"]:
            (item,) = self.request("Bash", {"command": command}, tool_id="Bash")
            self.gate.answer(item["id"], "deny")
        self.archive.write_bytes(b"different")
        self.assertTrue(self.request("Bash", {"command": base}, tool_id="Bash"))

    def test_answer_outcome_depends_on_delivery(self):
        for outcome in (False, RuntimeError("connection closed"), True):
            with self.subTest(outcome=outcome):
                self.gate = self.make_gate(False)
                delivery = Future()
                (item,) = self.request(callback=lambda *_, result=delivery: result)
                self.gate.answer(item["id"], "allow_session")
                self.assertEqual(self.gate.snapshot()["last_outcome"], "")
                with self.assertRaises(ValueError):
                    self.gate.answer(item["id"], "allow_session")
                if isinstance(outcome, Exception):
                    delivery.set_exception(outcome)
                else:
                    delivery.set_result(outcome)
                expected = "allowed for this session" if outcome is True else "expired"
                self.assertEqual(self.gate.snapshot()["last_outcome"], expected)
                with self.assertRaisesRegex(ValueError, expected):
                    self.gate.answer(item["id"], "allow_session")
                self.assertEqual(bool(self.request()), outcome is not True)

    def test_close_invalidates_before_notifying(self):
        notifications = []

        def broken(*_):
            notifications.append(self.gate.waiting())
            raise BrokenPipeError()

        self.request(callback=broken)
        self.request(rid=2)
        self.gate.close("stopped")
        self.assertEqual(notifications, [False])
        self.assertEqual(self.answers, [("deny", "stopped")])

    def test_late_ack_cannot_grant_after_stop(self):
        delivery = Future()
        (item,) = self.request(callback=lambda *_: delivery)
        self.gate.answer(item["id"], "allow_session")
        self.gate.close("stopped")
        delivery.set_result(True)
        self.assertTrue(self.request())
        self.assertEqual(self.gate.snapshot()["last_outcome"], "stopped")

    def test_implicit_approval_requires_verified_identity(self):
        command = f"{sys.executable} {self.archive} pending {self.unit}"
        for title, args in [("Bash", {"command": command}), ("Read", {"file_path": "/tmp/example"})]:
            (item,) = self.request(title, args, tool_id=None)
            self.assertEqual(item["options"], ["allow_once", "deny"])
            self.gate.answer(item["id"], "deny")

    def test_config_locations_cannot_be_granted(self):
        custom = self.root / "per-user-data"
        config = self.root / "project" / "opencode.jsonc"
        link = self.root / "innocent"
        link.symlink_to(config)
        with patch.dict(os.environ, {"CODEX_HOME": str(custom), "OPENCODE_CONFIG": str(self.root / "overrides")}):
            for path in [config, link, custom / "config.toml", self.root / "overrides"]:
                (item,) = self.request("Read", {"file_path": str(path)})
                self.assertNotIn("allow_session", item["options"])
                self.gate.answer(item["id"], "deny")

    def test_closing_one_request_preserves_other_worker(self):
        (first,) = self.request(rid=17)
        _, worker = self.request(rid=18)
        self.gate.closed(SimpleNamespace(request_id=17, outcome="expired", text=""))
        with self.assertRaisesRegex(ValueError, "expired"):
            self.gate.answer(first["id"], "allow_once")
        self.gate.answer(worker["id"], "allow_once")

    def test_heredoc_is_complete_and_quoted(self):
        prefix = f"{sys.executable} {self.archive} reply {self.unit} --to m-5"
        self.assertEqual(self.request("Bash", {"command": prefix + " <<'TEXT'\na message\nTEXT"}, tool_id="Bash"), [])
        for suffix in [" <<TEXT\na message\nTEXT", " <<'TEXT'\na\nTEXT\nmore\nTEXT", " <<'TEXT'\na\nTEXT\nmore"]:
            (item,) = self.request("Bash", {"command": prefix + suffix}, tool_id="Bash")
            self.gate.answer(item["id"], "deny")


if __name__ == "__main__":
    unittest.main()
