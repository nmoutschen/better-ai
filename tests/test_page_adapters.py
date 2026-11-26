"""The page's adapter wire messages, exercised without logging into a harness."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from better_ai.page.adapters import (  # noqa: E402
    ACPAdapter,
    CodexAdapter,
    OpenCodeAdapter,
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
        self.assertIsNone(found.kind)
        self.assertEqual((found.approval, found.codec_factory), ("webauthn", CodexAdapter))
        opencode = candidate("opencode", {}, lambda _: "/bin/opencode")
        self.assertEqual((opencode.approval, opencode.codec_factory), ("webauthn", OpenCodeAdapter))
        for name in ("cursor", "droid", "devin"):
            self.assertEqual(candidate(name, {}, lambda _: "/bin/harness").kind, "no-approvals")
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
        config = json.loads(opencode["OPENCODE_CONFIG_CONTENT"])
        self.assertEqual(config["permission"], {"edit": "ask", "bash": "ask"})
        self.assertEqual(
            config["permissions"],
            [
                {"action": "edit", "resource": "*", "effect": "ask"},
                {"action": "shell", "resource": "*", "effect": "ask"},
            ],
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
        self.assertIsNone(event.tool_id)
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
        self.assertEqual(sent[-1]["method"], "account/read")
        self.assertEqual(sent[-1]["params"], {"refreshToken": False})
        adapter.receive({"id": sent[-1]["id"], "result": {"account": {"type": "chatgpt"}}})
        self.assertEqual(sent[-1]["method"], "thread/resume")
        self.assertEqual(sent[-1]["params"]["threadId"], SESSION)
        self.assertEqual(sent[-1]["params"]["approvalsReviewer"], "user")
        result = adapter.receive(
            {
                "id": sent[-1]["id"],
                "result": {
                    "thread": {"id": SESSION},
                    "approvalPolicy": "on-request",
                    "approvalsReviewer": "user",
                    "sandbox": {"type": "workspaceWrite", "networkAccess": False},
                },
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
                adapter.receive({"id": sent[-1]["id"], "result": {"account": {"type": "chatgpt"}}})
                event = adapter.receive(
                    {
                        "id": sent[-1]["id"],
                        "result": {
                            "thread": {"id": SESSION},
                            "approvalPolicy": policy,
                            "approvalsReviewer": reviewer,
                            "sandbox": {"type": "workspaceWrite", "networkAccess": False},
                        },
                    }
                )[0]
                self.assertEqual((event.kind, event.outcome), ("failed", "unsafe-mode"))

    def open_claude(self, permission_mode="default", account=None):
        sent = []
        plan = candidate("claude", {}, lambda _: "/bin/claude")
        adapter = plan.codec(sent.append, SESSION, None)
        adapter.open("/repo", None)
        self.assertEqual(sent[-1]["request"]["subtype"], "initialize")
        data = {
            "claude_code_version": "2.1.332",
            "current_permission_mode": permission_mode,
            "account": {"subscriptionType": "pro"} if account is None else account,
        }
        event = adapter.receive(
            {
                "type": "control_response",
                "response": {"subtype": "success", "request_id": sent[-1]["request_id"], "response": data},
            }
        )[0]
        return plan, adapter, sent, event

    def test_claude_reuses_one_stream_for_multiple_prompts(self):
        plan, adapter, sent, ready = self.open_claude()
        self.assertEqual((plan.approval, ready.kind, ready.session_id), ("webauthn", "ready", SESSION))
        self.assertEqual(plan.command(SESSION, None)[-1], f"--session-id={SESSION}")
        self.assertEqual(plan.command(SESSION, SESSION)[-1], f"--resume={SESSION}")
        self.assertEqual(plan.command(SESSION, "--dangerously-skip-permissions")[-1], f"--session-id={SESSION}")
        self.assertIn("--permission-prompts", plan.command(SESSION, None))
        adapter.prompt("First")
        adapter.prompt("Second")
        adapter.cancel()
        self.assertEqual([m["message"]["content"] for m in sent[1:3]], ["First", "Second"])
        self.assertEqual(sent[-1]["request"]["subtype"], "interrupt")
        result = adapter.receive({"type": "result", "subtype": "success", "result": "Complete"})
        self.assertEqual((result[0].kind, result[0].outcome, result[0].text), ("turn_ended", "normal", "Complete"))

    def test_claude_checks_login_and_effective_mode_before_a_turn(self):
        for mode, account, expected in (("bypassPermissions", None, "unsafe-mode"), ("default", {}, "login")):
            with self.subTest(mode=mode, account=account):
                _, _, sent, event = self.open_claude(mode, account)
                self.assertEqual((event.kind, event.outcome), ("failed", expected))
                self.assertEqual(len(sent), 1)

    def test_claude_rechecks_permissions_at_the_first_turn(self):
        _, adapter, _, ready = self.open_claude()
        self.assertEqual(ready.kind, "ready")
        event = adapter.receive(
            {"type": "system", "subtype": "init", "session_id": SESSION, "permissionMode": "bypassPermissions"}
        )[0]
        self.assertEqual((event.kind, event.outcome), ("failed", "unsafe-mode"))
        self.assertIsNone(adapter.session_id)

    def test_claude_replies_to_the_exact_permission_request(self):
        _, adapter, sent, _ = self.open_claude()
        raw = {"command": "pwd"}
        request = {
            "type": "control_request",
            "request_id": "p1",
            "request": {"subtype": "can_use_tool", "tool_name": "Bash", "input": raw, "agent_id": "worker"},
        }
        event = adapter.receive(request)[0]
        self.assertEqual((event.kind, event.arguments, event.requester), ("approval", raw, "worker"))
        self.assertEqual(event.tool_id, "Bash")
        self.assertEqual(event.options, ("allow_once", "deny"))
        self.assertFalse(adapter.answer("different", "allow_once"))
        self.assertTrue(adapter.answer("p1", "allow_once"))
        self.assertEqual(sent[-1]["response"]["response"], {"behavior": "allow", "updatedInput": raw})
        self.assertFalse(adapter.answer("p1", "allow_once"))
        adapter.receive({**request, "request_id": "p2"})
        closed = adapter.receive({"type": "control_cancel_request", "request_id": "p2"})[0]
        self.assertEqual((closed.kind, closed.request_id, closed.outcome), ("approval_closed", "p2", "expired"))
        self.assertFalse(adapter.answer("p2", "allow_once"))
        adapter.receive({**request, "request_id": "p3", "request": {"subtype": "can_use_tool"}})
        self.assertEqual(sent[-1]["response"]["response"]["behavior"], "deny")

    def test_claude_spontaneous_turn_starts_on_main_assistant_output(self):
        _, adapter, _, _ = self.open_claude()
        assistant = {
            "type": "assistant",
            "parent_tool_use_id": None,
            "message": {"content": [{"type": "text", "text": "Main output"}]},
        }
        worker = {**assistant, "parent_tool_use_id": "tool123"}
        self.assertNotIn("turn_started", [event.kind for event in adapter.receive(worker)])
        self.assertEqual([event.kind for event in adapter.receive(assistant)], ["turn_started", "text"])
        self.assertEqual([event.kind for event in adapter.receive(assistant)], ["text"])
        adapter.receive({"type": "result", "subtype": "success", "result": "Complete"})
        self.assertEqual([event.kind for event in adapter.receive(assistant)], ["turn_started", "text"])

    def test_codex_reports_logged_out_without_starting_a_thread(self):
        sent = []
        adapter = CodexAdapter(sent.append)
        adapter.open("/repo", None)
        adapter.receive({"id": sent[-1]["id"], "result": {"userAgent": "codex_cli_rs/0.172.0"}})
        event = adapter.receive({"id": sent[-1]["id"], "result": {"account": None}})[0]
        self.assertEqual((event.kind, event.outcome), ("failed", "login"))
        self.assertFalse(any(message.get("method") == "thread/start" for message in sent))

    def test_codex_opens_a_configured_provider_without_openai_auth(self):
        sent = []
        adapter = CodexAdapter(sent.append)
        adapter.open("/repo", None)
        adapter.receive({"id": sent[-1]["id"], "result": {"userAgent": "codex_cli_rs/0.172.0"}})
        account = {"account": None, "requiresOpenaiAuth": False}
        self.assertEqual(adapter.receive({"id": sent[-1]["id"], "result": account}), ())
        self.assertEqual(sent[-1]["method"], "thread/start")

    def test_opencode_replaces_a_missing_saved_session(self):
        sent = []
        adapter = OpenCodeAdapter(sent.append)
        adapter.open("/repo", "ses_missing")
        adapter.receive({"id": sent[-1]["id"], "result": {"protocolVersion": 1, "agentInfo": {"version": "2.4.1"}}})
        self.assertEqual(sent[-1]["method"], "session/load")
        missing = {"code": -32002, "message": "The selected session is gone"}
        self.assertEqual(adapter.receive({"id": sent[-1]["id"], "error": missing}), ())
        self.assertEqual(sent[-1]["method"], "session/new")
        result = {"sessionId": "ses_new", "configOptions": [{"category": "mode", "currentValue": "build"}]}
        event = adapter.receive({"id": sent[-1]["id"], "result": result})[0]
        self.assertEqual((event.kind, event.session_id), ("ready", "ses_new"))

    def test_opencode_checks_its_reported_version_and_mode(self):
        sent = []
        adapter = OpenCodeAdapter(sent.append)
        adapter.open("/repo", None)
        adapter.receive({"id": sent[-1]["id"], "result": {"protocolVersion": 1, "agentInfo": {"version": "2.4.1"}}})
        result = {"sessionId": "ses_new", "configOptions": [{"category": "mode", "currentValue": "build"}]}
        event = adapter.receive({"id": sent[-1]["id"], "result": result})[0]
        self.assertEqual((event.kind, event.session_id), ("ready", "ses_new"))
        adapter = OpenCodeAdapter(sent.append)
        adapter.open("/repo", None)
        old = {"protocolVersion": 1, "agentInfo": {"version": "2.3.9"}}
        event = adapter.receive({"id": sent[-1]["id"], "result": old})[0]
        self.assertEqual((event.kind, event.outcome), ("failed", "version"))


if __name__ == "__main__":
    unittest.main()
