"""Exercise the paired session, request binding, and real ES256 signatures without opening a browser."""

import base64
import hashlib
import json
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
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
        self.key = self.root / "data" / "credential.json"
        self.archive = self.root / "better.pyz"
        self.archive.write_bytes(b"test archive")
        self.gate = self.make_gate(False)
        self.answers = []

    def make_gate(self, presence):
        return ApprovalGate(
            self.unit, ORIGIN, credential_path=self.key, require_presence=presence, archive=self.archive
        )

    def request(self, tool="Read", args=None, rid=1):
        event = SimpleNamespace(
            tool=tool,
            arguments={"file_path": "/tmp/example"} if args is None else args,
            request_id=rid,
            requester=None,
            options=("allow_once", "deny"),
        )
        self.gate.receive(event, lambda answer, reason: self.answers.append((answer, reason)))
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
            (item,) = self.request(tool, args)
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
        self.assertEqual(self.request("Bash", {"command": base}), [])
        self.assertTrue(self.gate.snapshot()["notice"])
        for command in [base + "; pwd", base + " >file", "X=1 " + base, base + " $(pwd)"]:
            (item,) = self.request("Bash", {"command": command})
            self.gate.answer(item["id"], "deny")
        self.archive.write_bytes(b"different")
        self.assertTrue(self.request("Bash", {"command": base}))

    def test_enrollment_deadline_and_long_wait(self):
        with patch("better_ai.page.approvals.time.monotonic", return_value=10):
            self.gate = self.make_gate(True)
        with (
            patch("better_ai.page.approvals.time.monotonic", return_value=130),
            self.assertRaisesRegex(ValueError, "closed"),
        ):
            self.gate.begin_enrollment()
        self.gate = self.make_gate(False)
        (item,) = self.request()
        with patch("better_ai.page.approvals.time.monotonic", return_value=10**10):
            self.gate.answer(item["id"], "allow_once")
        self.assertEqual(self.answers[-1][0], "allow_once")

    def test_closing_one_request_preserves_other_worker(self):
        (first,) = self.request(rid=17)
        _, worker = self.request(rid=18)
        self.gate.closed(SimpleNamespace(request_id=17, outcome="expired", text=""))
        with self.assertRaisesRegex(ValueError, "expired"):
            self.gate.answer(first["id"], "allow_once")
        self.gate.answer(worker["id"], "allow_once")

    def test_heredoc_is_complete_and_quoted(self):
        prefix = f"{sys.executable} {self.archive} reply {self.unit} --to m-5"
        self.assertEqual(self.request("Bash", {"command": prefix + " <<'TEXT'\na message\nTEXT"}), [])
        for suffix in [" <<TEXT\na message\nTEXT", " <<'TEXT'\na\nTEXT\nmore\nTEXT", " <<'TEXT'\na\nTEXT\nmore"]:
            (item,) = self.request("Bash", {"command": prefix + suffix})
            self.gate.answer(item["id"], "deny")

    def test_no_assertion_denied(self):
        self.gate = self.make_gate(True)
        (item,) = self.request()
        with self.assertRaises(ValueError):
            self.gate.answer(item["id"], "allow_once")
        self.gate.answer(item["id"], "deny")

    @unittest.skipUnless(shutil.which("openssl"), "openssl needed to generate an independent ES256 signature")
    def test_registration_and_signed_assertion(self):
        def openssl(*args, data=None):
            return subprocess.run(["openssl", *args], input=data, capture_output=True, check=True).stdout

        def client(kind, challenge, origin=ORIGIN):
            return json.dumps(dict(type="webauthn." + kind, challenge=challenge, origin=origin)).encode()

        private = self.root / "private.pem"
        openssl("ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(private))
        point = openssl("ec", "-in", str(private), "-pubout", "-outform", "DER")[-65:]
        cose = bytes.fromhex("a5010203262001215820") + point[1:33] + bytes.fromhex("225820") + point[33:]
        self.gate = self.make_gate(True)
        create = self.gate.begin_enrollment()
        auth = RP + b"\x41" + bytes(20) + b"\x00\x03abc" + cose
        # CTAP canonical CBOR attestation object with none attestation.
        att = b"\xa3\x63fmt\x64none\x67attStmt\xa0\x68authData\x58" + bytes([len(auth)]) + auth
        self.gate.finish_enrollment(
            {
                "type": "public-key",
                "rawId": b64(b"abc"),
                "response": {
                    "clientDataJSON": b64(client("create", create["challenge"])),
                    "attestationObject": b64(att),
                },
            }
        )
        self.assertEqual(stat.S_IMODE(self.key.stat().st_mode), 0o600)
        self.gate = self.make_gate(True)
        self.assertTrue(self.gate.enrolled())
        (item,) = self.request()
        rid = item["id"]

        def proof(opts, origin=ORIGIN, wrong_key=False, rp=RP, flags=1, kind="get"):
            data = client(kind, opts["challenge"], origin)
            auth = rp + bytes([flags]) + bytes(4)
            if wrong_key:
                openssl("ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(self.root / "other.pem"))
            sig = openssl(
                "dgst",
                "-sha256",
                "-sign",
                str(self.root / "other.pem" if wrong_key else private),
                data=auth + hashlib.sha256(data).digest(),
            )
            return {
                "type": "public-key",
                "rawId": b64(b"abc"),
                "response": {"clientDataJSON": b64(data), "authenticatorData": b64(auth), "signature": b64(sig)},
            }

        for modify in [
            lambda c: proof({"challenge": "wrong"}),
            lambda c: proof(c, "http://localhost:4444"),
            lambda c: proof(c, wrong_key=True),
            lambda c: proof(c, rp=bytes(32)),
            lambda c: proof(c, flags=0),
            lambda c: proof(c, kind="create"),
        ]:
            with self.assertRaises(ValueError):
                self.gate.answer(rid, "allow_once", modify(self.gate.challenge(rid, "allow_once")))
        signed = proof(self.gate.challenge(rid, "allow_once"))
        with self.assertRaises(ValueError):
            self.gate.answer(rid, "allow_session", signed)
        self.gate.answer(rid, "allow_once", proof(self.gate.challenge(rid, "allow_once")))
        self.assertEqual(self.answers[-1][0], "allow_once")
