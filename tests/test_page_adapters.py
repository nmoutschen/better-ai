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
            self.assertEqual(candidate(name, {}, lambda _: None).kind, "not-installed")
            found = candidate(name, {}, lambda _: "/bin/harness")
            self.assertIsNone(found.kind)
            self.assertEqual(found.approval, "webauthn")
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

    def test_startup_cli_version_gate_covers_every_candidate(self):
        cases = {
            "claude": ("2.1.332 (Claude Code)", "2.1.331 (Claude Code)"),
            "codex": ("codex-cli 0.172.0", "codex-cli 0.171.999"),
            "opencode": ("2.4.1", "2.4.0"),
            "cursor": ("2026.11.17-6dfa30c", "2026.11.16-6dfa30c"),
            "droid": ("droid 1.21.0", "droid 1.20.999"),
            "devin": ("devin v3000.13.4", "devin v3000.13.3"),
        }
        for name, (supported, previous) in cases.items():
            with self.subTest(name=name):
                plan = candidate(name, {}, lambda _: f"/bin/{name}")
                self.assertIsNone(plan.kind)
                self.assertTrue(version_supported(plan.name, supported))
                self.assertFalse(version_supported(plan.name, previous))
                self.assertFalse(version_supported(plan.name, "version unknown"))
        self.assertTrue(version_supported("cursor", "v2026.11.17"))
        self.assertTrue(version_supported("cursor", "cursor-agent 2027.01.05-abcdef0"))
        self.assertFalse(version_supported("cursor", "2026.12.32-abcdef0"))
        self.assertFalse(version_supported("cursor", "2026.11.17-not-a-release"))

    def test_devin_launch_selects_the_owned_process(self):
        plan = candidate("devin", {}, lambda _: "/bin/devin")
        self.assertEqual(plan.command(SESSION, None), ("/bin/devin", "--process-model", "in-process", "acp"))

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

    def test_codex_expires_only_approvals_owned_by_the_completed_turn(self):
        sent = []
        adapter = CodexAdapter(sent.append)
        adapter.open("/repo", None)
        adapter.receive({"id": sent[-1]["id"], "result": {"userAgent": "codex_cli_rs/0.172.0"}})
        adapter.receive({"id": sent[-1]["id"], "result": {"account": {"type": "chatgpt"}}})
        adapter.receive(
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
        turn = {"id": "turn-main", "status": "inProgress"}
        adapter.receive({"method": "turn/started", "params": {"threadId": SESSION, "turn": turn}})
        for request_id, turn_id in (("main", "turn-main"), ("worker", "turn-other")):
            event = adapter.receive(
                {
                    "id": request_id,
                    "method": "item/commandExecution/requestApproval",
                    "params": {"threadId": SESSION, "turnId": turn_id, "command": "pwd"},
                }
            )[0]
            self.assertEqual(event.requester, turn_id)
        events = adapter.receive(
            {
                "method": "turn/completed",
                "params": {"threadId": SESSION, "turn": {**turn, "status": "completed"}},
            }
        )
        self.assertEqual(
            [(event.kind, event.request_id, event.outcome) for event in events],
            [("approval_closed", "main", "expired"), ("turn_ended", None, "normal")],
        )
        self.assertFalse(adapter.answer("main", "allow_once"))
        self.assertTrue(adapter.answer("worker", "allow_once"))

    def test_acp_expires_an_exact_terminal_tool_call_only(self):
        sent = []
        adapter = ACPAdapter(sent.append)
        adapter.open("/repo", None)
        adapter.receive({"id": sent[-1]["id"], "result": {"protocolVersion": 1}})
        adapter.receive({"id": sent[-1]["id"], "result": {"sessionId": "ses_one"}})
        adapter.prompt("Work")
        prompt_id = sent[-1]["id"]
        for label in ("first", "worker"):
            adapter.receive(
                {
                    "id": label,
                    "method": "session/request_permission",
                    "params": {
                        "sessionId": "ses_one",
                        "toolCall": {"toolCallId": label, "name": "Run", "rawInput": {"command": "pwd"}},
                        "options": [{"optionId": "yes", "kind": "allow_once"}],
                    },
                }
            )
        self.assertEqual(
            adapter.receive(
                {
                    "id": prompt_id,
                    "result": {"stopReason": "end_turn"},
                }
            )[0].kind,
            "turn_ended",
        )
        event = adapter.receive(
            {
                "method": "session/update",
                "params": {
                    "sessionId": "ses_one",
                    "update": {"sessionUpdate": "tool_call_update", "toolCallId": "first", "status": "failed"},
                },
            }
        )[0]
        self.assertEqual((event.kind, event.request_id, event.outcome), ("approval_closed", "first", "expired"))
        self.assertFalse(adapter.answer("first", "allow_once"))
        self.assertTrue(adapter.answer("worker", "allow_once"))

    def test_claude_expires_main_and_ended_workers_separately(self):
        _, adapter, _, _ = self.open_claude()
        for request_id, owner in (("main", None), ("ended", "worker-a"), ("running", "worker-b")):
            adapter.receive(
                {
                    "type": "control_request",
                    "request_id": request_id,
                    "request": {
                        "subtype": "can_use_tool",
                        "tool_name": "Bash",
                        "input": {"command": "pwd"},
                        "agent_id": owner,
                    },
                }
            )
        events = adapter.receive({"type": "result", "subtype": "success"})
        self.assertEqual([event.request_id for event in events if event.kind == "approval_closed"], ["main"])
        self.assertFalse(adapter.answer("main", "allow_once"))
        event = adapter.receive(
            {
                "type": "system",
                "subtype": "task_updated",
                "session_id": SESSION,
                "task_id": "worker-a",
                "patch": {"status": "killed"},
            }
        )[0]
        self.assertEqual((event.kind, event.request_id, event.outcome), ("approval_closed", "ended", "expired"))
        self.assertFalse(adapter.answer("ended", "allow_once"))
        self.assertTrue(adapter.answer("running", "allow_once"))

    def test_cursor_authenticates_and_requires_reported_approval_policy(self):
        for mode, outcome in (("allowlist", None), ("unrestricted", "unsafe-mode"), (None, "no-approvals")):
            with self.subTest(mode=mode):
                sent = []
                plan = candidate("cursor", {}, lambda _: "/bin/agent")
                adapter = plan.codec(sent.append, SESSION, None)
                adapter.open("/repo", None)
                assert sent[-1]["method"] == "initialize"
                self.assertEqual(sent[-1]["params"]["clientInfo"]["name"], "better-ai")
                init = {
                    "protocolVersion": 1,
                    "authMethods": [
                        {"id": "cursor_login", "name": "Cursor Login"},
                    ],
                }
                adapter.receive({"id": sent[-1]["id"], "result": init})
                self.assertEqual(sent[-1]["method"], "authenticate")
                self.assertEqual(sent[-1]["params"], {"methodId": "cursor_login"})
                adapter.receive({"id": sent[-1]["id"], "result": {}})
                self.assertEqual(sent[-1]["method"], "session/new")
                options = (
                    [
                        {
                            "id": "approvalMode",
                            "name": "Approval mode",
                            "type": "select",
                            "currentValue": mode,
                            "options": [
                                {"value": "allowlist", "name": "Allowlist"},
                                {"value": "unrestricted", "name": "Unrestricted"},
                            ],
                        }
                    ]
                    if mode
                    else []
                )
                session = {"sessionId": "cursor_session", "configOptions": options}
                event = adapter.receive({"id": sent[-1]["id"], "result": session})[0]
                self.assertEqual(event.outcome, outcome)
                self.assertEqual(event.kind, "failed" if outcome else "ready")

    def test_devin_requires_normal_permissions_and_a_forwarded_startup_request(self):
        for forwarded in (False, True):
            with self.subTest(forwarded=forwarded):
                sent = []
                plan = candidate("devin", {}, lambda _: "/bin/devin")
                adapter = plan.codec(sent.append, SESSION, None)
                adapter.open("/repo", None)
                adapter.receive({"id": sent[-1]["id"], "result": {"protocolVersion": 1}})
                session_request = sent[-1]["id"]
                if forwarded:
                    request = {
                        "sessionId": "devin_session",
                        "toolCall": {"toolCallId": "call", "name": "Bash", "rawInput": {"command": "pwd"}},
                        "options": [
                            {"kind": "allow_once", "optionId": "once", "name": "Allow once"},
                            {"kind": "reject_once", "optionId": "no", "name": "Deny"},
                        ],
                    }
                    self.assertEqual(
                        adapter.receive(
                            {
                                "id": "perm",
                                "method": "session/request_permission",
                                "params": request,
                            }
                        ),
                        (),
                    )
                    self.assertEqual(sent[-1]["result"]["outcome"]["optionId"], "no")
                options = [
                    {
                        "id": "permission_mode",
                        "name": "Permission mode",
                        "type": "select",
                        "currentValue": "normal",
                        "options": [{"value": "normal", "name": "Normal"}, {"value": "dangerous", "name": "Bypass"}],
                    }
                ]
                event = adapter.receive(
                    {
                        "id": session_request,
                        "result": {"sessionId": "devin_session", "configOptions": options},
                    }
                )[0]
                self.assertEqual(event.kind, "ready" if forwarded else "failed")
                self.assertEqual(event.outcome, None if forwarded else "no-approvals")

    def test_droid_turn_interrupt_and_exact_permission_owner(self):
        sent = []
        plan = candidate("droid", {}, lambda _: "/bin/droid")
        adapter = plan.codec(sent.append, SESSION, None)
        adapter.open("/repo", None)
        self.assertEqual(sent[-1]["method"], "droid.initialize_session")
        self.assertEqual(sent[-1]["factoryApiVersion"], "1.0.0")
        self.assertEqual(sent[-1]["factoryProtocolVersion"], "1.332.0")
        self.assertEqual(
            sent[-1]["params"],
            {
                "machineId": "default",
                "cwd": "/repo",
                "autonomyLevel": "off",
                "interactionMode": "auto",
            },
        )
        reply = {
            "type": "response",
            "id": sent[-1]["id"],
            "factoryProtocolVersion": "1.332.0",
            "result": {
                "sessionId": SESSION,
                "session": {"messages": []},
                "settings": {
                    "autonomyLevel": "off",
                    "interactionMode": "auto",
                    "modelId": "model",
                    "reasoningEffort": "off",
                },
            },
        }
        self.assertEqual(adapter.receive(reply)[0].kind, "ready")
        adapter.prompt("Read a name")
        self.assertEqual(sent[-1]["method"], "droid.add_user_message")
        self.assertEqual(sent[-1]["params"], {"text": "Read a name", "queuePlacement": "end_of_turn"})
        adapter.receive({"type": "response", "id": sent[-1]["id"], "result": {}})
        text = adapter.receive(
            {
                "method": "droid.session_notification",
                "type": "notification",
                "params": {
                    "sessionId": SESSION,
                    "notification": {
                        "type": "assistant_text_delta",
                        "messageId": "msg",
                        "blockIndex": 0,
                        "textDelta": "Read",
                    },
                },
            }
        )[0]
        self.assertEqual((text.kind, text.text), ("text", "Read"))
        for key, owner in (("own", None), ("other", "child-id")):
            request = {
                "toolUses": [
                    {
                        "toolUse": {"type": "tool_use", "id": "tool", "name": "Execute", "input": {"command": "pwd"}},
                        "confirmationType": "exec",
                        "details": {"type": "exec", "command": "pwd", "fullCommand": "pwd"},
                    }
                ],
                "options": [{"value": "proceed_once", "label": "Allow once"}, {"value": "cancel", "label": "Deny"}],
            }
            if owner:
                request["workerSessionId"] = owner
            event = adapter.receive(
                {
                    "id": key,
                    "method": "droid.request_permission",
                    "type": "request",
                    "params": request,
                }
            )[0]
            self.assertEqual((event.kind, event.requester), ("approval", owner))
        adapter.cancel()
        self.assertEqual(sent[-1]["method"], "droid.interrupt_session")
        events = adapter.receive(
            {
                "method": "droid.session_notification",
                "type": "notification",
                "params": {
                    "sessionId": SESSION,
                    "notification": {"type": "agent_turn_completed", "reason": "cancelled"},
                },
            }
        )
        self.assertEqual(
            [(e.kind, e.outcome) for e in events], [("approval_closed", "expired"), ("turn_ended", "stopped")]
        )
        self.assertFalse(adapter.answer("own", "allow_once"))
        self.assertTrue(adapter.answer("other", "allow_once"))
        self.assertEqual(sent[-1]["result"], {"selectedOption": "proceed_once"})
        self.assertEqual(sent[-1]["type"], "response")

    def test_droid_requires_current_protocol_and_off_autonomy(self):
        for version, autonomy, failure in (
            ("1.331.0", "off", "version"),
            ("1.332.0", "high", "unsafe-mode"),
        ):
            with self.subTest(version=version, autonomy=autonomy):
                sent = []
                plan = candidate("droid", {}, lambda _: "/bin/droid")
                adapter = plan.codec(sent.append, SESSION, None)
                adapter.open("/repo", None)
                event = adapter.receive(
                    {
                        "type": "response",
                        "id": sent[-1]["id"],
                        "factoryProtocolVersion": version,
                        "result": {
                            "sessionId": SESSION,
                            "settings": {"autonomyLevel": autonomy, "interactionMode": "auto"},
                        },
                    }
                )[0]
                self.assertEqual((event.kind, event.outcome), ("failed", failure))


if __name__ == "__main__":
    unittest.main()
