"""Permission relay checks over an anonymous socketpair, with no Claude account."""

import json
import socket
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from better_ai.page.permission_relay import Relay, claude_permission_config  # noqa: E402


class PermissionRelayTests(unittest.TestCase):
    def test_approval_needs_ack_and_exact_answer(self):
        peer, child = socket.socketpair()
        with peer, child, Relay(child, ack_timeout=0.1) as relay:
            request = {"tool_name": "Bash", "input": {"command": "pwd"}, "tool_use_id": "tool1"}
            results = []
            worker = threading.Thread(target=lambda: results.append(relay.approve(request)))
            worker.start()
            peer.settimeout(2)
            with peer.makefile("r") as incoming:
                record = json.loads(incoming.readline())
            self.assertEqual((record["type"], record["arguments"]), ("permission", request))
            request_id = record["id"]

            def send(**message):
                peer.sendall(json.dumps(message).encode() + b"\n")

            send(type="ack", id=request_id)
            send(type="answer", id="wrong", allow=True)
            worker.join(0.15)
            self.assertTrue(worker.is_alive())
            send(type="answer", id=request_id, allow=True)
            worker.join(2)
            self.assertFalse(worker.is_alive())
            self.assertEqual(results, [{"behavior": "allow", "updatedInput": request["input"]}])

    def test_dead_driver_denies(self):
        peer, child = socket.socketpair()
        with peer, child, Relay(child, ack_timeout=0.01) as relay:
            request = {"tool_name": "Bash", "input": {"command": "pwd"}}
            unacknowledged = relay.approve(request)
            self.assertEqual(unacknowledged["behavior"], "deny")
            self.assertIn("acknowledge", unacknowledged["message"])
            peer.close()
            self.assertEqual(relay.approve(request)["behavior"], "deny")

    def test_config_passes_the_descriptor_as_an_argument(self):
        config = claude_permission_config(Path("/bin/python"), Path("/bundle/better.pyz"), 42)
        self.assertEqual(config["mcpServers"]["better_page"]["command"], "/bin/python")
        self.assertEqual(
            config["mcpServers"]["better_page"]["args"],
            ["/bundle/better.pyz", "permission-relay", "--fd", "42"],
        )
