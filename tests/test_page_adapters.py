"""The page's adapter wire messages, exercised without logging into a harness."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from better_ai.page.adapters import (  # noqa: E402
    ACPAdapter,
    ClaudeAdapter,
    CodexAdapter,
    candidate,
    child_environment,
    version_supported,
)

SESSION = "018f237b-1234-7253-9111-0123456789ab"


class AdapterTests(unittest.TestCase):
    def test_selection_uses_harness_markers_and_checks_executable(self):
        self.assertEqual(candidate("auto", {}, lambda _: "/bin/codex").kind, "none")
        self.assertEqual(candidate("auto", {"CLAUDECODE": "1"}, lambda _: None).kind, "not-installed")
        found = candidate("auto", {"CODEX_THREAD_ID": SESSION}, lambda name: f"/bin/{name}")
        self.assertEqual(found.name, "codex")
        self.assertEqual(found.argv, ("/bin/codex", "app-server"))
        self.assertEqual(found.kind, "no-approvals")
        for name in ("claude", "codex", "cursor", "opencode", "droid", "devin"):
            with self.subTest(name=name):
                self.assertEqual(candidate(name, {}, lambda _: "/bin/harness").name, name)
        with self.assertRaises(ValueError):
            candidate("unknown", {}, lambda _: None)

    def test_version_checks(self):
        self.assertTrue(version_supported("claude", "2.1.332 (Claude Code)"))
        self.assertFalse(version_supported("claude", "2.1.301 (Claude Code)"))
        self.assertTrue(version_supported("codex", "codex-cli 0.172.0"))
        self.assertFalse(version_supported("codex", "codex-cli 0.171.0"))
        self.assertFalse(version_supported("opencode", "version unknown"))

    def test_environments(self):
        parent = {"PATH": "/bin", "OTHER": "original"}
        self.assertEqual(child_environment("codex", parent, SESSION), {**parent, "BETTER_PAGE_SESSION": SESSION})
        opencode = child_environment("opencode", parent, SESSION)
        self.assertEqual(opencode["OTHER"], "original")
        self.assertEqual(
            json.loads(opencode["OPENCODE_CONFIG_CONTENT"]), {"permission": {"edit": "ask", "bash": "ask"}}
        )
        self.assertEqual(parent, {"PATH": "/bin", "OTHER": "original"})

    def test_acp_version_session_turn_and_resume(self):
        sent = []
        adapter = ACPAdapter(sent.append)
        adapter.open("/repo", "sess_previous")
        self.assertEqual(sent[-1]["method"], "initialize")
        self.assertEqual(sent[-1]["params"]["protocolVersion"], 1)
        adapter.receive({"id": sent[-1]["id"], "result": {"protocolVersion": 1}})
        self.assertEqual(sent[-1]["method"], "session/load")
        self.assertEqual(sent[-1]["params"]["sessionId"], "sess_previous")
        result = adapter.receive({"id": sent[-1]["id"], "result": {}})
        self.assertEqual((result[0].kind, result[0].session_id), ("ready", "sess_previous"))
        adapter.prompt("Hello")
        prompt_id = sent[-1]["id"]
        self.assertEqual(sent[-1]["params"]["prompt"], [{"type": "text", "text": "Hello"}])
        adapter.cancel()
        self.assertEqual(sent[-1]["method"], "session/cancel")
        event = adapter.receive({"id": prompt_id, "result": {"stopReason": "cancelled"}})[0]
        self.assertEqual((event.kind, event.outcome), ("turn_ended", "stopped"))

    def test_acp_refuses_unsupported_version(self):
        sent = []
        adapter = ACPAdapter(sent.append)
        adapter.open("/repo", None)
        event = adapter.receive({"id": sent[-1]["id"], "result": {"protocolVersion": 2}})[0]
        self.assertEqual((event.kind, event.outcome), ("failed", "version"))

    def test_acp_permission_options_stay_bound_to_the_request(self):
        sent = []
        adapter = ACPAdapter(sent.append)
        adapter.open("/repo", None)
        adapter.receive({"id": sent[-1]["id"], "result": {"protocolVersion": 1}})
        adapter.receive({"id": sent[-1]["id"], "result": {"sessionId": "sess_one"}})
        params = {
            "sessionId": "sess_one",
            "toolCall": {"toolCallId": "tool1", "kind": "execute", "name": "Run", "rawInput": {"command": "pwd"}},
            "options": [
                {"optionId": "always", "kind": "allow_always"},
                {"optionId": "once", "kind": "allow_once"},
                {"optionId": "deny", "kind": "reject_once"},
            ],
        }
        request = {"id": "p", "method": "session/request_permission", "params": params}
        event = adapter.receive(request)[0]
        self.assertEqual((event.kind, event.tool, event.arguments), ("approval", "Run", {"command": "pwd"}))
        self.assertEqual(event.options, ("allow_once", "deny"))
        self.assertTrue(adapter.answer("p", "allow_once"))
        self.assertEqual(sent[-1]["result"], {"outcome": {"outcome": "selected", "optionId": "once"}})
        self.assertFalse(adapter.answer("p", "allow_once"))

        incomplete = {**params, "toolCall": {"toolCallId": "tool2", "name": "Run"}}
        self.assertEqual(adapter.receive({**request, "id": "incomplete", "params": incomplete}), ())
        self.assertEqual(sent[-1]["result"], {"outcome": {"outcome": "selected", "optionId": "deny"}})

    def test_unknown_notifications_and_requests(self):
        sent = []
        adapter = ACPAdapter(sent.append)
        self.assertEqual(adapter.receive({"method": "vendor/notification"}), ())
        self.assertEqual(sent, [])
        self.assertEqual(adapter.receive({"method": "vendor/rpc", "id": 1}), ())
        self.assertEqual(sent[-1]["error"]["code"], -32601)
        self.assertEqual(adapter.receive({"method": "vendor/requestApproval", "id": 2}), ())
        self.assertEqual(sent[-1]["error"]["message"], "permission denied")

    def test_codex_turn_interrupt_and_approval_policy(self):
        sent = []
        adapter = CodexAdapter(sent.append)
        adapter.open("/repo", SESSION)
        adapter.receive({"id": sent[-1]["id"], "result": {"userAgent": "codex_cli_rs/0.172.0"}})
        self.assertEqual(sent[-1]["method"], "thread/resume")
        self.assertEqual(sent[-1]["params"]["threadId"], SESSION)
        self.assertEqual(sent[-1]["params"]["approvalsReviewer"], "user")
        result = adapter.receive(
            {
                "id": sent[-1]["id"],
                "result": {"thread": {"id": SESSION}, "approvalPolicy": "on-request", "approvalsReviewer": "user"},
            }
        )
        self.assertEqual(result[0].session_id, SESSION)
        adapter.prompt("Hello")
        self.assertEqual(sent[-1]["method"], "turn/start")
        turn = {"id": "turn1", "status": "inProgress"}
        adapter.receive({"method": "turn/started", "params": {"threadId": SESSION, "turn": turn}})
        adapter.cancel()
        self.assertEqual(sent[-1]["params"], {"threadId": SESSION, "turnId": "turn1"})
        event = adapter.receive(
            {"method": "turn/completed", "params": {"threadId": SESSION, "turn": {**turn, "status": "interrupted"}}}
        )[0]
        self.assertEqual(event.outcome, "stopped")

    def test_codex_never_accepts_bypass_or_a_nonuser_reviewer(self):
        for policy, reviewer in (("never", "user"), ("on-request", "guardian")):
            with self.subTest(policy=policy, reviewer=reviewer):
                sent = []
                adapter = CodexAdapter(sent.append)
                adapter.open("/repo", None)
                adapter.receive({"id": sent[-1]["id"], "result": {"userAgent": "codex_cli_rs/0.172.0"}})
                event = adapter.receive(
                    {
                        "id": sent[-1]["id"],
                        "result": {"thread": {"id": SESSION}, "approvalPolicy": policy, "approvalsReviewer": reviewer},
                    }
                )[0]
                self.assertEqual((event.kind, event.outcome), ("failed", "unsafe-mode"))

    def test_claude_reuses_one_stream_for_multiple_prompts(self):
        sent = []
        adapter = ClaudeAdapter(sent.append)
        adapter.open("/repo", SESSION)
        adapter.prompt("First")
        adapter.prompt("Second")
        adapter.cancel()
        self.assertEqual([m["message"]["content"] for m in sent[:2]], ["First", "Second"])
        self.assertEqual(sent[2]["request"]["subtype"], "interrupt")
        start = adapter.receive(
            {"type": "system", "subtype": "init", "session_id": SESSION, "permissionMode": "default"}
        )
        self.assertEqual(start[0].session_id, SESSION)
        result = adapter.receive({"type": "result", "subtype": "success", "result": "Complete"})
        self.assertEqual((result[0].kind, result[0].outcome, result[0].text), ("turn_ended", "normal", "Complete"))
        result = adapter.receive(
            {"type": "system", "subtype": "init", "session_id": SESSION, "permissionMode": "bypassPermissions"}
        )
        self.assertEqual(result[0].outcome, "unsafe-mode")


if __name__ == "__main__":
    unittest.main()
