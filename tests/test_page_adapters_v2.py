"""The page's adapters against recorded wire data: Claude Code 2.1.332 and Codex 0.172.0 (tests/fixtures/page_wire)."""

import builtins
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from better_ai.page.adapters import (  # noqa: E402
    HARNESS_FACTS,
    CodexAdapter,
    DroidAdapter,
    OpenCodeAdapter,
    candidate,
    chat_argv,
    chat_mode,
    child_environment,
    version_supported,
)
from better_ai.page.adapters import _touches_config as touches_config  # noqa: E402
from better_ai.page.transport import ProcessTransport  # noqa: E402

WIRE = ROOT / "tests" / "fixtures" / "page_wire"
CLAUDE = json.loads((WIRE / "claude_2_1_332.json").read_text())
CODEX = json.loads((WIRE / "codex_0_172_0.json").read_text())
SESSION = "018f237b-1234-7253-9111-0123456789ab"
CLAUDE_SESSION = CLAUDE["system_init_auto"]["session_id"]


def frame(name, source=CLAUDE, **changes):
    return {**copy.deepcopy(source[name]), **changes}


def claude_plan(*chat):
    return candidate("claude", {}, lambda _: "/bin/claude", chat_argv=("claude", *chat))


def open_claude(*chat, initialize="initialize_default"):
    sent = []
    plan = claude_plan(*chat)
    adapter = plan.codec(sent.append, CLAUDE_SESSION, None)
    adapter.open("/repo", None)
    response = frame(initialize)
    response["response"]["request_id"] = sent[-1]["request_id"]
    return plan, adapter, sent, adapter.receive(response)


def open_codex(*chat, reviewer=None, policy="on-request", resume=None):
    sent = []
    plan = candidate("codex", {}, lambda _: "/bin/codex", chat_argv=("codex", *chat))
    adapter = plan.codec(sent.append, SESSION, resume)
    adapter.open("/repo", resume)
    adapter.receive({"id": sent[-1]["id"], "result": CODEX["initialize_response"]["result"]})
    adapter.receive({"id": sent[-1]["id"], "result": CODEX["account_response"]["result"]})
    start = sent[-1]
    key = "thread_start_response_auto_review" if start["params"].get("approvalsReviewer") == "auto_review" else None
    result = copy.deepcopy(CODEX[key or "thread_start_response_user"]["result"])
    result["thread"]["id"] = SESSION
    if reviewer:
        result["approvalsReviewer"] = reviewer
    result["approvalPolicy"] = policy
    events = adapter.receive({"id": start["id"], "result": result})
    return plan, adapter, sent, events


class SelectionAndLaunch(unittest.TestCase):
    def test_adapter_is_picked_from_the_environment(self):  # S51
        markers = {
            "claude": {"CLAUDECODE": "1"},
            "codex": {"CODEX_THREAD_ID": SESSION},
            "cursor": {"CURSOR_AGENT": "1"},
            "opencode": {"OPENCODE": "1"},
            "devin": {"DEVIN_CLI": "1"},
            "droid": {"FACTORY_DROID": "1"},
        }
        argv = {
            "claude": ("-p", "--input-format", "stream-json"),
            "codex": ("app-server",),
            "cursor": ("acp",),
            "opencode": ("acp",),
            "devin": ("acp",),
            "droid": ("exec", "--input-format", "stream-jsonrpc"),
        }
        for name, env in markers.items():
            with self.subTest(name=name):
                plan = candidate("auto", env, lambda binary: f"/bin/{binary}")
                self.assertEqual((plan.name, plan.kind), (name, None))
                self.assertTrue(set(argv[name]) <= set(plan.argv), plan.argv)
        none = candidate("auto", {}, lambda _: "/bin/x")
        self.assertEqual((none.name, none.kind), (None, "no-harness"))
        self.assertTrue(none.text.startswith("No supported harness"))
        missing = candidate("auto", {"CODEX_THREAD_ID": SESSION}, lambda _: None)
        self.assertEqual(
            (missing.kind, missing.text), ("not-installed", "Codex is not installed. Install it, then serve again.")
        )

    def test_claude_starts_with_the_host_approval_channel_and_replay(self):  # S130 S158 S96 S50
        argv = claude_plan().command(SESSION, None)
        self.assertEqual(argv[:1], ("/bin/claude",))
        for flag in ("-p", "--verbose", "--replay-user-messages"):
            self.assertIn(flag, argv)
        self.assertEqual(argv[argv.index("--input-format") + 1], "stream-json")
        self.assertEqual(argv[argv.index("--permission-prompts") + 1], "host")
        self.assertEqual(argv[argv.index("--permission-prompt-tool") + 1], "stdio")

    def test_claude_starts_without_the_users_browser_or_desktop_tools(self):  # S64
        argv = claude_plan().command(SESSION, None)
        self.assertIn("--no-chrome", argv)
        blocked = argv[argv.index("--disallowed-tools") + 1].split(",")
        for name in ("mcp__claude-in-chrome", "mcp__Claude_Browser", "mcp__computer-use"):
            self.assertIn(name, blocked)
        self.assertFalse([name for name in blocked if "playwright" in name.lower() or "puppeteer" in name.lower()])

    def test_claude_keeps_the_users_rules_and_network(self):  # S65 S155
        argv = claude_plan().command(SESSION, None)
        for flag in ("--bare", "--setting-sources", "--allowedTools", "--allowed-tools", "--tools", "--settings"):
            self.assertNotIn(flag, argv)
        self.assertFalse([part for part in argv if "sandbox" in part or "network" in part])
        _, codex, sent, _ = open_codex()
        self.assertTrue(set(sent[-1]["params"]) <= {"cwd", "approvalsReviewer"}, sent[-1]["params"])

    def test_child_environment_changes_only_the_session_variable(self):  # S74
        parent = {"PATH": "/bin", "ANTHROPIC_API_KEY": "kept-as-is", "OTHER": "1"}
        for name in ("claude", "codex", "cursor", "droid", "devin"):
            with self.subTest(name=name):
                self.assertEqual(child_environment(name, parent, SESSION), {**parent, "BETTER_PAGE_SESSION": SESSION})
        self.assertEqual(parent, {"PATH": "/bin", "ANTHROPIC_API_KEY": "kept-as-is", "OTHER": "1"})
        _, adapter, _, _ = open_claude()
        self.assertEqual(adapter.session_id, CLAUDE_SESSION)

    def test_missing_login_is_kind_login(self):  # S74
        sent = []
        adapter = claude_plan().codec(sent.append, CLAUDE_SESSION, None)
        adapter.open("/repo", None)
        response = frame("initialize_default")
        response["response"]["request_id"] = sent[-1]["request_id"]
        response["response"]["response"]["account"] = {}
        event = adapter.receive(response)[0]
        self.assertEqual((event.kind, event.outcome), ("failed", "login"))
        sent = []
        adapter = CodexAdapter(sent.append)
        adapter.open("/repo", None)
        adapter.receive({"id": sent[-1]["id"], "result": CODEX["initialize_response"]["result"]})
        event = adapter.receive({"id": sent[-1]["id"], "result": {"account": None, "requiresOpenaiAuth": True}})[0]
        self.assertEqual((event.kind, event.outcome), ("failed", "login"))

    def test_opencode_asks_for_edit_and_bash_through_its_environment(self):  # S34
        with tempfile.TemporaryDirectory() as home:
            env = {"HOME": home, "XDG_CONFIG_HOME": home, "PATH": "/bin"}
            plan = candidate("opencode", env, lambda _: "/bin/opencode")
            child = child_environment("opencode", env, SESSION)
            self.assertEqual(os.listdir(home), [])
            self.assertIsInstance(plan.codec(lambda _: None, SESSION, None), OpenCodeAdapter)
        config = json.loads(child["OPENCODE_CONFIG_CONTENT"])
        self.assertEqual(config["permission"], {"edit": "ask", "bash": "ask"})
        self.assertEqual(
            {rule["action"]: rule["effect"] for rule in config["permissions"]}, {"edit": "ask", "shell": "ask"}
        )
        self.assertEqual(
            {key: value for key, value in child.items() if key != "OPENCODE_CONFIG_CONTENT"},
            {**env, "BETTER_PAGE_SESSION": SESSION},
        )

    def test_no_adapter_reads_a_file(self):  # S52
        def refuse(*args, **kwargs):
            raise AssertionError(f"opened {args[:1]}")

        with mock.patch.object(builtins, "open", refuse), mock.patch.object(Path, "read_text", refuse):
            for name in ("claude", "codex", "cursor", "opencode", "droid", "devin"):
                plan = candidate(name, {}, lambda binary: f"/bin/{binary}")
                adapter = plan.codec(lambda _: None, SESSION, None)
                adapter.open("/repo", None)
                adapter.receive({"method": "vendor/notification"})
            _, adapter, _, _ = open_claude("--permission-mode", "auto", initialize="initialize_auto")
            adapter.receive(frame("edit_request"))


class DisplayNames(unittest.TestCase):
    def test_each_harness_has_its_display_name(self):  # N6
        from better_ai.page import adapters

        self.assertEqual(
            {name: adapters.display_name(name) for name in adapters.HARNESS_FACTS},
            {
                "claude": "Claude Code",
                "codex": "Codex",
                "cursor": "Cursor",
                "devin": "Devin",
                "droid": "Droid",
                "opencode": "OpenCode",
            },
        )
        self.assertEqual(adapters.display_name("stub"), "stub")

    def test_not_installed_names_the_harness_by_its_display_name(self):  # N6, S147
        from better_ai.page import adapters

        found = adapters.candidate("codex", {}, which=lambda command: None)
        self.assertEqual(
            (found.kind, found.text), ("not-installed", "Codex is not installed. Install it, then serve again.")
        )


class ChatMode(unittest.TestCase):
    def test_chat_mode_comes_from_the_chat_command_line(self):  # S11
        cases = {
            ("claude", ()): None,
            ("claude", ("--permission-mode", "auto")): "auto",
            ("claude", ("--permission-mode=acceptEdits",)): "accept edits",
            ("claude", ("--dangerously-skip-permissions",)): "skip approvals",
            ("claude", ("--permission-mode", "bypassPermissions")): "skip approvals",
            ("claude", ("--permission-mode", "manual")): "manual",
            ("codex", ()): None,
            ("codex", ("--approve-for-me",)): "auto",
            ("codex", ("-c", "approvals_reviewer=auto_review")): "auto",
            ("codex", ("--dangerously-bypass-approvals-and-sandbox",)): "skip approvals",
            ("codex", ("-a", "never")): "skip approvals",
            ("codex", ("--ask-for-approval", "on-request")): "manual",
            ("cursor", ("--yolo",)): "skip approvals",
            ("cursor", ("--auto-review",)): None,
        }
        for (name, flags), expected in cases.items():
            with self.subTest(name=name, flags=flags):
                self.assertEqual(chat_mode(name, (name, *flags)), expected)

    def test_chat_command_line_is_found_among_the_ancestors(self):  # S11
        table = {
            "300": "200 /bin/zsh -c serve page",
            "200": "100 claude --permission-mode auto",
            "100": "1 /sbin/launchd",
        }

        def ps(command, **_):
            line = table.get(command[-1], "")
            return subprocess.CompletedProcess(command, 0 if line else 1, stdout=line + "\n", stderr="")

        self.assertEqual(chat_argv("claude", 300, ps), ("claude", "--permission-mode", "auto"))
        self.assertEqual(chat_argv("codex", 300, ps), ())

    def test_claude_passes_the_chat_mode_on_and_reports_it(self):  # S11 S157
        plan, _, _, events = open_claude("--permission-mode", "auto", initialize="initialize_auto")
        argv = plan.command(SESSION, None)
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "auto")
        self.assertEqual((events[0].kind, events[0].mode), ("ready", "auto"))
        plan, _, _, events = open_claude()
        self.assertNotIn("--permission-mode", plan.command(SESSION, None))
        self.assertEqual((events[0].kind, events[0].mode), ("ready", "manual"))
        skip = claude_plan("--dangerously-skip-permissions").command(SESSION, None)
        self.assertIn("--dangerously-skip-permissions", skip)
        self.assertNotIn("--permission-mode", skip)

    def test_claude_refuses_a_session_in_another_mode_than_the_chat(self):  # S11
        _, _, _, events = open_claude("--permission-mode", "auto", initialize="initialize_default")
        self.assertEqual((events[0].kind, events[0].outcome), ("failed", "unsafe-mode"))
        _, adapter, _, events = open_claude("--permission-mode", "auto", initialize="initialize_auto")
        self.assertEqual(events[0].kind, "ready")
        changed = frame("system_init_auto", session_id=CLAUDE_SESSION, permissionMode="bypassPermissions")
        self.assertEqual(adapter.receive(changed)[0].outcome, "unsafe-mode")

    def test_skip_approvals_names_the_mode_and_raises_no_approval(self):  # S157
        init = copy.deepcopy(CLAUDE["initialize_default"])
        init["response"]["response"]["current_permission_mode"] = "bypassPermissions"
        sent = []
        adapter = claude_plan("--dangerously-skip-permissions").codec(sent.append, CLAUDE_SESSION, None)
        adapter.open("/repo", None)
        init["response"]["request_id"] = sent[-1]["request_id"]
        ready = adapter.receive(init)[0]
        self.assertEqual((ready.kind, ready.mode), ("ready", "skip approvals"))

    def test_codex_follows_the_chat_mode(self):  # S11 S160
        _, adapter, sent, events = open_codex("--approve-for-me", reviewer="auto_review")
        self.assertEqual(sent[-1]["method"], "thread/start")
        self.assertEqual(sent[-1]["params"]["approvalsReviewer"], "auto_review")
        self.assertEqual((events[0].kind, events[0].mode, events[0].session_id), ("ready", "auto", SESSION))
        _, _, sent, events = open_codex("-a", "on-request")
        self.assertEqual(sent[-1]["params"]["approvalPolicy"], "on-request")
        self.assertNotIn("approvalsReviewer", sent[-1]["params"])
        self.assertEqual((events[0].kind, events[0].mode), ("ready", "manual"))
        _, _, sent, events = open_codex("-a", "never", policy="never")
        self.assertEqual(sent[-1]["params"]["approvalPolicy"], "never")
        self.assertEqual((events[0].kind, events[0].mode), ("ready", "skip approvals"))
        _, _, sent, events = open_codex("--approve-for-me", reviewer="user")
        self.assertEqual(events[0].outcome, "unsafe-mode")
        _, _, _, events = open_codex(reviewer="guardian_subagent")
        self.assertEqual((events[0].kind, events[0].mode), ("ready", "auto"))
        _, _, _, events = open_codex(reviewer="someone_else")
        self.assertEqual(events[0].outcome, "unsafe-mode")

    def test_codex_resume_keeps_the_reviewer(self):  # S160
        _, _, sent, events = open_codex("--approve-for-me", reviewer="auto_review", resume=SESSION)
        self.assertEqual(
            (sent[-1]["method"], sent[-1]["params"]["approvalsReviewer"]), ("thread/resume", "auto_review")
        )
        self.assertEqual(events[0].kind, "ready")


class ClaudeApprovals(unittest.TestCase):
    def test_every_decision_offers_the_harness_session_scope(self):  # S10 S130 S158
        _, adapter, sent, _ = open_claude()
        edit = adapter.receive(frame("edit_request"))[0]
        self.assertEqual(
            (edit.kind, edit.tool, edit.options), ("approval", "Edit", ("allow_once", "allow_session", "deny"))
        )
        prefix = adapter.receive(frame("bash_prefix_request"))[0]
        self.assertEqual(prefix.options, ("allow_once", "allow_session", "deny"))
        none = adapter.receive(frame("bash_no_suggestion_request"))[0]
        self.assertEqual(none.options, ("allow_once", "deny"))
        self.assertTrue(adapter.answer(prefix.request_id, "allow_session"))
        reply = sent[-1]["response"]
        self.assertEqual(reply["request_id"], prefix.request_id)
        grant = reply["response"]
        self.assertEqual(grant["behavior"], "allow")
        self.assertEqual(grant["updatedInput"], prefix.arguments)
        self.assertEqual(grant["updatedPermissions"][0]["rules"], [{"toolName": "Bash", "ruleContent": "git push *"}])
        self.assertEqual({item["destination"] for item in grant["updatedPermissions"]}, {"session"})
        self.assertTrue(adapter.answer(edit.request_id, "allow_once"))
        self.assertNotIn("updatedPermissions", sent[-1]["response"]["response"])
        self.assertTrue(adapter.answer(none.request_id, "deny", "not now"))
        self.assertEqual(sent[-1]["response"]["response"], {"behavior": "deny", "message": "not now"})

    def test_no_session_scope_for_harness_config_paths(self):  # S10
        _, adapter, _, _ = open_claude()
        request = frame("write_request")
        for path in (
            "/repo/.claude/settings.json",
            "/home/u/.codex/config.toml",
            "/repo/.cursor/rules",
            "/repo/.factory/x",
        ):
            request["request_id"] = path
            request["request"]["input"]["file_path"] = path
            self.assertEqual(adapter.receive(copy.deepcopy(request))[0].options, ("allow_once", "deny"), path)
        request["request_id"] = "ok"
        request["request"]["input"]["file_path"] = "/repo/notes.txt"
        self.assertIn("allow_session", adapter.receive(copy.deepcopy(request))[0].options)
        bash = frame("bash_prefix_request", request_id="cfg")
        bash["request"]["input"]["command"] = "cat > .claude/settings.local.json"
        self.assertEqual(adapter.receive(bash)[0].options, ("allow_once", "deny"))

    def test_the_harness_can_withhold_the_session_scope(self):  # S10
        _, adapter, _, _ = open_claude()
        request = frame("bash_prefix_request", request_id="x")
        request["request"]["suppress_always_allow_rule"] = True
        self.assertEqual(adapter.receive(request)[0].options, ("allow_once", "deny"))

    def test_harness_cancel_closes_the_decision_as_expired_with_its_reason(self):  # S45
        _, adapter, sent, _ = open_claude()
        event = adapter.receive(frame("edit_request"))[0]
        closed = adapter.receive(frame("control_cancel_request"))[0]
        self.assertEqual(
            (closed.kind, closed.request_id, closed.outcome), ("approval_closed", event.request_id, "expired")
        )
        self.assertEqual(closed.text, "claude cancelled the request")
        self.assertFalse(adapter.answer(event.request_id, "allow_once"))

    def test_unknown_messages_are_ignored_or_refused(self):  # S33
        _, adapter, sent, _ = open_claude()
        self.assertEqual(
            [event.kind for event in adapter.receive({"type": "vendor_notice", "subtype": "x"})], ["unknown"]
        )
        before = len(sent)
        self.assertEqual(
            adapter.receive({"type": "control_request", "request_id": "u1", "request": {"subtype": "vendor"}}), ()
        )
        self.assertEqual(
            sent[before]["response"], {"request_id": "u1", "subtype": "error", "error": "method not supported"}
        )
        self.assertEqual(
            adapter.receive({"type": "control_request", "request_id": "u2", "request": {"subtype": "vendor_approval"}}),
            (),
        )
        self.assertEqual(sent[-1]["response"]["error"], "permission denied")

    def test_version_below_the_minimum_names_both_versions(self):  # S33
        sent = []
        adapter = claude_plan().codec(sent.append, CLAUDE_SESSION, None)
        adapter.open("/repo", None)
        old = frame("initialize_default")
        old["response"]["request_id"] = sent[-1]["request_id"]
        old["response"]["response"]["claude_code_version"] = "2.1.301"
        event = adapter.receive(old)[0]
        self.assertEqual((event.kind, event.outcome), ("failed", "version"))
        self.assertEqual(event.text, "Claude Code reported 2.1.301. Version 2.1.332 or later is required.")
        self.assertTrue(version_supported("claude", "2.9.0 (Claude Code)"))
        sent = []
        adapter = CodexAdapter(sent.append)
        adapter.open("/repo", None)
        event = adapter.receive({"id": sent[-1]["id"], "result": {"userAgent": "codex-cli/0.171.0 (Mac)"}})[0]
        self.assertEqual(event.text, "Codex reported 0.171.0. Version 0.172.0 or later is required.")

    def test_each_prompt_carries_its_uuid_and_its_echo_is_reported(self):  # S96 S50
        _, adapter, sent, _ = open_claude()
        adapter.prompt("First", "11111111-2222-4333-8444-555555555555")
        adapter.prompt("Second", "aaaaaaaa-2222-4333-8444-555555555555")
        self.assertEqual(
            [m["uuid"] for m in sent[1:3]],
            ["11111111-2222-4333-8444-555555555555", "aaaaaaaa-2222-4333-8444-555555555555"],
        )
        self.assertEqual([m["message"]["content"] for m in sent[1:3]], ["First", "Second"])
        echo = adapter.receive(frame("replayed_user_message"))
        self.assertEqual((echo[0].kind, echo[0].uuid), ("prompt_echoed", "11111111-2222-4333-8444-555555555555"))
        tool_result = {"type": "user", "uuid": "x", "message": {"content": [{"type": "tool_result"}]}}
        self.assertEqual(adapter.receive(tool_result), ())

    def test_auto_mode_blocks_show_as_notices_not_decisions(self):  # S159
        _, adapter, sent, _ = open_claude("--permission-mode", "auto", initialize="initialize_auto")
        self.assertEqual(adapter.receive(frame("permission_denied")), ())
        events = adapter.receive(frame("result_auto_blocked"))
        blocked = [event for event in events if event.kind == "blocked"]
        self.assertEqual(len(blocked), 2)
        first = CLAUDE["result_auto_blocked"]["permission_denials"][0]
        self.assertEqual((blocked[0].tool, blocked[0].arguments), (first["tool_name"], first["tool_input"]))
        self.assertEqual(blocked[0].text, "[Destructive or Unwanted Actions]")
        self.assertEqual(blocked[1].text, "")
        self.assertEqual(events[-1].kind, "turn_ended")
        self.assertEqual(blocked[0].options, ())

    def test_a_denial_the_user_gave_on_the_page_is_not_an_auto_mode_block(self):  # S159
        _, adapter, _, _ = open_claude("--permission-mode", "auto", initialize="initialize_auto")
        request = frame("bash_prefix_request")
        adapter.receive(request)
        adapter.answer(request["request_id"], "deny", "no")
        result = frame("result_denied_by_page")
        result["permission_denials"] = [
            {
                "tool_name": "Bash",
                "tool_use_id": request["request"]["tool_use_id"],
                "tool_input": request["request"]["input"],
            }
        ]
        self.assertEqual([event.kind for event in adapter.receive(result)], ["turn_ended"])

    def test_outside_auto_mode_denials_are_not_notices(self):  # S159
        _, adapter, _, _ = open_claude()
        self.assertEqual([event.kind for event in adapter.receive(frame("result_auto_blocked"))], ["turn_ended"])


class CodexApprovals(unittest.TestCase):
    def ready(self, *chat, **kwargs):
        _, adapter, sent, _ = open_codex(*chat, **kwargs)
        return adapter, sent

    def test_command_decisions_offer_session_only_when_codex_does(self):  # S10
        adapter, sent = self.ready()
        request = frame("command_request", CODEX)
        request["params"]["threadId"] = SESSION
        event = adapter.receive(request)[0]
        self.assertEqual((event.kind, event.tool, event.options), ("approval", "Command", ("allow_once", "deny")))
        self.assertTrue(adapter.answer(event.request_id, "allow_once"))
        self.assertEqual(sent[-1]["result"], {"decision": "accept"})
        again = copy.deepcopy(request)
        again["id"] = 8
        again["params"]["availableDecisions"] = ["accept", "acceptForSession", "cancel"]
        event = adapter.receive(again)[0]
        self.assertEqual(event.options, ("allow_once", "allow_session", "deny"))
        self.assertTrue(adapter.answer(8, "allow_session"))
        self.assertEqual(sent[-1]["result"], {"decision": "acceptForSession"})

    def test_file_changes_offer_session_scope_except_for_config_paths(self):  # S10
        adapter, sent = self.ready()
        started = frame("file_change_item_started", CODEX)
        started["params"]["threadId"] = SESSION
        adapter.receive(started)
        request = frame("file_change_request", CODEX)
        request["params"]["threadId"] = SESSION
        event = adapter.receive(request)[0]
        self.assertEqual((event.tool, event.options), ("File change", ("allow_once", "allow_session", "deny")))
        adapter.answer(event.request_id, "allow_session")
        self.assertEqual(sent[-1]["result"], {"decision": "acceptForSession"})
        config = copy.deepcopy(started)
        config["params"]["item"]["id"] = "patch-2"
        config["params"]["item"]["changes"][0]["path"] = "/home/u/.codex/config.toml"
        adapter.receive(config)
        second = copy.deepcopy(request)
        second["id"] = 9
        second["params"]["itemId"] = "patch-2"
        self.assertEqual(adapter.receive(second)[0].options, ("allow_once", "deny"))
        adapter.answer(9, "deny", "no")
        self.assertEqual(sent[-1]["result"], {"decision": "decline"})

    def test_harness_resolving_a_request_expires_it_with_its_reason(self):  # S45
        adapter, _ = self.ready()
        request = frame("command_request", CODEX)
        request["params"]["threadId"] = SESSION
        event = adapter.receive(request)[0]
        resolved = frame("resolved", CODEX)
        resolved["params"]["threadId"] = SESSION
        resolved["params"]["requestId"] = event.request_id
        closed = adapter.receive(resolved)[0]
        self.assertEqual(
            (closed.kind, closed.outcome, closed.text), ("approval_closed", "expired", "codex resolved the request")
        )

    def test_automatic_review_denial_is_a_notice(self):  # S159
        adapter, _ = self.ready("--approve-for-me", reviewer="auto_review")
        approved = frame("review_approved", CODEX)
        approved["params"]["threadId"] = SESSION
        self.assertEqual(adapter.receive(approved), ())
        denied = frame("review_denied", CODEX)
        denied["params"]["threadId"] = SESSION
        event = adapter.receive(denied)[0]
        self.assertEqual(event.kind, "blocked")
        self.assertEqual(event.tool, "Command")
        self.assertEqual(event.arguments["command"], "git push --force origin HEAD:main")
        self.assertEqual(event.text, "The command rewrites shared history and no one asked for it.")

    def test_unknown_requests_are_refused(self):  # S33
        adapter, sent = self.ready()
        unknown = adapter.receive({"method": "vendor/notification", "params": {"threadId": SESSION}})
        self.assertEqual([(event.kind, event.text) for event in unknown], [("unknown", "vendor/notification")])
        adapter.receive({"method": "vendor/call", "id": 40, "params": {}})
        self.assertEqual(sent[-1]["error"]["code"], -32601)
        adapter.receive({"method": "item/vendor/requestApproval", "id": 41, "params": {}})
        self.assertEqual(sent[-1]["error"]["message"], "permission denied")


class OtherHarnessesOfferTheirOwnSessionScope(unittest.TestCase):
    def test_acp_offers_allow_always_when_the_agent_does(self):  # S10
        plan = candidate("cursor", {}, lambda _: "/bin/agent")
        sent = []
        adapter = plan.codec(sent.append, "s", None)
        adapter.session_id = "sess_one"
        params = {
            "sessionId": "sess_one",
            "toolCall": {"toolCallId": "t1", "kind": "execute", "name": "Run", "rawInput": {"command": "pwd"}},
            "options": [
                {"optionId": "always", "kind": "allow_always"},
                {"optionId": "once", "kind": "allow_once"},
                {"optionId": "no", "kind": "reject_once"},
            ],
        }
        event = adapter.receive({"id": "p", "method": "session/request_permission", "params": params})[0]
        self.assertEqual(event.options, ("allow_once", "allow_session", "deny"))
        adapter.answer("p", "allow_session")
        self.assertEqual(sent[-1]["result"], {"outcome": {"outcome": "selected", "optionId": "always"}})
        params["options"] = params["options"][1:]
        params["toolCall"] = {**params["toolCall"], "toolCallId": "t2", "rawInput": {"file_path": "/r/.opencode/x"}}
        self.assertEqual(
            adapter.receive({"id": "q", "method": "session/request_permission", "params": params})[0].options,
            ("allow_once", "deny"),
        )

    def test_droid_offers_proceed_always_when_the_agent_does(self):  # S10
        sent = []
        adapter = DroidAdapter(sent.append)
        adapter.session_id = "droid-session"
        header = {
            "jsonrpc": "2.0",
            "type": "request",
            "factoryApiVersion": "1.0.0",
            "factoryProtocolVersion": "1.332.0",
        }
        request = {
            **header,
            "id": "r1",
            "method": "droid.request_permission",
            "params": {
                "toolUses": [{"toolUse": {"name": "Execute", "input": {"command": "ls"}}}],
                "options": [{"value": "proceed_once"}, {"value": "proceed_always"}, {"value": "cancel"}],
            },
        }
        event = adapter.receive(request)[0]
        self.assertEqual(event.options, ("allow_once", "allow_session", "deny"))
        adapter.answer("r1", "allow_session")
        self.assertEqual(sent[-1]["result"], {"selectedOption": "proceed_always"})


def acp_option(config_id, value):
    return [{"id": config_id, "name": config_id, "type": "select", "currentValue": value, "options": []}]


def open_cursor(reported, *chat):
    """Cursor ACP: approvalMode values allowlist, auto-review and unrestricted (cursor.com/docs/cli/reference/configuration)."""
    sent = []
    adapter = candidate("cursor", {}, lambda _: "/bin/agent", chat_argv=("agent", *chat)).codec(sent.append, "s", None)
    adapter.open("/repo", None)
    adapter.receive({"id": sent[-1]["id"], "result": {"protocolVersion": 1, "authMethods": [{"id": "cursor_login"}]}})
    adapter.receive({"id": sent[-1]["id"], "result": {}})
    events = adapter.receive(
        {
            "id": sent[-1]["id"],
            "result": {"sessionId": "cs1", "configOptions": acp_option("approvalMode", reported) if reported else []},
        }
    )
    return adapter, sent, events


def open_devin(reported, *chat):
    """Devin permission modes normal, accept-edits, smart, dangerous (docs.devin.ai/cli/reference/permissions)."""
    sent = []
    adapter = candidate("devin", {}, lambda _: "/bin/devin", chat_argv=("devin", *chat)).codec(sent.append, "s", None)
    adapter.open("/repo", None)
    adapter.receive({"id": sent[-1]["id"], "result": {"protocolVersion": 1}})
    new = sent[-1]["id"]
    request = {
        "sessionId": "ds1",
        "toolCall": {"toolCallId": "c", "name": "Bash", "rawInput": {"command": "pwd"}},
        "options": [{"kind": "allow_once", "optionId": "once"}, {"kind": "reject_once", "optionId": "no"}],
    }
    adapter.receive({"id": "perm", "method": "session/request_permission", "params": request})
    events = adapter.receive(
        {"id": new, "result": {"sessionId": "ds1", "configOptions": acp_option("permission_mode", reported)}}
    )
    return adapter, sent, events


def open_droid(autonomy, *chat):
    """Droid autonomy levels off, low, medium, high (docs.factory.com/cli/user-guides/auto-run)."""
    sent = []
    adapter = candidate("droid", {}, lambda _: "/bin/droid", chat_argv=("droid", *chat)).codec(sent.append, "s", None)
    adapter.open("/repo", None)
    start = sent[-1]
    header = {"jsonrpc": "2.0", "factoryApiVersion": "1.0.0", "factoryProtocolVersion": "1.332.0"}
    events = adapter.receive(
        {
            **header,
            "type": "response",
            "id": start["id"],
            "result": {
                "sessionId": "droid-1",
                "settings": {"autonomyLevel": autonomy, "interactionMode": "auto"},
            },
        }
    )
    return adapter, start, events, header


class OtherHarnessModes(unittest.TestCase):
    def test_cursor_maps_every_reported_approval_mode(self):  # S11 L1
        for value, label in (("allowlist", "manual"), ("auto-review", "auto"), ("unrestricted", "unrestricted")):
            with self.subTest(value=value):
                _, _, events = open_cursor(value)
                self.assertEqual((events[0].kind, events[0].mode), ("ready", label))
        _, _, events = open_cursor("something-new")
        self.assertEqual((events[0].kind, events[0].outcome), ("failed", "unsafe-mode"))
        _, _, events = open_cursor(None)
        self.assertEqual((events[0].kind, events[0].outcome), ("failed", "no-approvals"))

    def test_a_forced_cursor_chat_passes_force_on(self):  # S11 B1
        for flag in ("--force", "-f", "--yolo"):
            with self.subTest(flag=flag):
                plan = candidate("cursor", {}, lambda _: "/bin/agent", chat_argv=("agent", flag))
                self.assertEqual(plan.argv, ("/bin/agent", "--force", "acp"))
                adapter, sent, events = open_cursor("allowlist", flag)
                self.assertNotIn("session/set_config_option", [frame.get("method") for frame in sent])
                self.assertEqual((events[0].kind, events[0].mode), ("ready", "skip approvals"))

    def test_cursor_accepts_a_matching_update_and_refuses_another_mode(self):  # S11
        adapter, _, _ = open_cursor("auto-review")
        update = lambda value: {  # noqa: E731
            "method": "session/update",
            "params": {
                "sessionId": "cs1",
                "update": {"sessionUpdate": "config_option_update", "configOptions": acp_option("approvalMode", value)},
            },
        }
        self.assertEqual(adapter.receive(update("auto-review")), ())
        self.assertEqual(adapter.receive(update("unrestricted"))[0].outcome, "unsafe-mode")

    def test_devin_maps_every_reported_permission_mode(self):  # S11 L1
        for value, label in (
            ("normal", "manual"),
            ("accept-edits", "accept edits"),
            ("smart", "auto"),
            ("dangerous", "skip approvals"),
        ):
            with self.subTest(value=value):
                _, _, events = open_devin(value)
                self.assertEqual((events[0].kind, events[0].mode), ("ready", label))
        _, _, events = open_devin("autonomous")
        self.assertEqual((events[0].kind, events[0].mode), ("ready", "autonomous"))
        _, _, events = open_devin("something-new")
        self.assertEqual((events[0].kind, events[0].outcome), ("failed", "unsafe-mode"))

    def test_devin_is_set_to_the_chat_mode(self):  # S11
        adapter, sent, events = open_devin("normal", "--permission-mode", "smart")
        self.assertEqual(events, ())
        self.assertEqual(sent[-1]["params"], {"sessionId": "ds1", "configId": "permission_mode", "value": "smart"})
        ready = adapter.receive(
            {"id": sent[-1]["id"], "result": {"configOptions": acp_option("permission_mode", "smart")}}
        )
        self.assertEqual((ready[0].kind, ready[0].mode), ("ready", "auto"))

    def test_droid_maps_autonomy_and_sets_the_chat_mode(self):  # S11 L1
        for value, label in (("off", "manual"), ("low", "low"), ("medium", "medium"), ("high", "high")):
            with self.subTest(value=value):
                _, start, events, _ = open_droid(value)
                self.assertNotIn("autonomyLevel", start["params"])
                self.assertEqual((events[0].kind, events[0].mode), ("ready", label))
        _, _, events, _ = open_droid("ultra")
        self.assertEqual((events[0].kind, events[0].outcome), ("failed", "unsafe-mode"))
        sent = []
        adapter = DroidAdapter(sent.append, "low")
        adapter.open("/repo", None)
        self.assertEqual(sent[-1]["params"]["autonomyLevel"], "low")
        header = {"jsonrpc": "2.0", "factoryApiVersion": "1.0.0", "factoryProtocolVersion": "1.332.0"}
        settings = {"autonomyLevel": "low", "interactionMode": "auto"}
        ready = adapter.receive(
            {
                **header,
                "type": "response",
                "id": sent[-1]["id"],
                "result": {"sessionId": "droid-1", "settings": settings},
            }
        )
        self.assertEqual((ready[0].kind, ready[0].mode), ("ready", "low"))
        update = {
            **header,
            "type": "notification",
            "method": "droid.session_notification",
            "params": {"sessionId": "droid-1", "notification": {"type": "settings_updated", "settings": settings}},
        }
        self.assertEqual(adapter.receive(update), ())
        update["params"]["notification"]["settings"] = {"autonomyLevel": "off", "interactionMode": "auto"}
        self.assertEqual(adapter.receive(update)[0].outcome, "unsafe-mode")

    def test_chat_mode_of_devin_and_cursor_comes_from_their_flags(self):  # S11
        self.assertEqual(chat_mode("devin", ("devin", "--permission-mode", "accept-edits")), "accept edits")
        self.assertEqual(chat_mode("devin", ("devin", "--permission-mode=yolo")), "skip approvals")
        self.assertEqual(chat_mode("devin", ("devin", "--permission-mode", "normal")), "manual")
        self.assertEqual(chat_mode("devin", ("devin", "--permission-mode", "auto")), "manual")
        self.assertEqual(chat_mode("devin", ("devin", "--sandbox", "--permission-mode", "autonomous")), "autonomous")
        self.assertEqual(chat_mode("cursor", ("agent", "--yolo")), "skip approvals")
        self.assertIsNone(chat_mode("cursor", ("agent", "--auto-review")))


class ClaudeGrantsAndPaths(unittest.TestCase):
    def test_a_set_mode_grant_changes_the_mode_the_session_may_report(self):  # F2 L3
        _, adapter, _, _ = open_claude()
        edit = adapter.receive(frame("edit_request"))[0]
        adapter.answer(edit.request_id, "allow_session")
        self.assertEqual(adapter.mode, "accept edits")
        init = frame("system_init_auto", session_id=CLAUDE_SESSION, permissionMode="acceptEdits")
        events = adapter.receive(init)
        self.assertEqual([(event.kind, event.mode) for event in events], [("mode", "accept edits")])  # N4
        self.assertEqual(adapter.receive(init), ())
        self.assertEqual(adapter.session_id, CLAUDE_SESSION)

    def test_a_grant_without_a_mode_keeps_the_mode(self):  # F2
        _, adapter, _, _ = open_claude()
        event = adapter.receive(frame("bash_prefix_request"))[0]
        adapter.answer(event.request_id, "allow_session")
        self.assertEqual(adapter.mode, "manual")

    def test_config_paths_in_every_real_form_offer_no_session_scope(self):  # F3 L2
        paths = (
            "/home/u/.claude.json",
            "~/.claude.json",
            "/repo/.mcp.json",
            "/home/u/.config/opencode/opencode.json",
            "~/.config/opencode/agents/x.md",
            "/repo/.claude/settings.json",
            ".claude/settings.local.json",
            "~/.codex/config.toml",
        )
        commands = (
            "echo {} >.claude/settings.local.json",
            "echo {} >>.claude/settings.local.json",
            "tee ~/.claude.json",
            "cat x>.mcp.json",
            "cp a '.cursor/rules/x'",
        )
        _, adapter, _, _ = open_claude()
        for number, path in enumerate(paths):
            request = frame("write_request", request_id=f"w{number}")
            request["request"]["input"]["file_path"] = path
            self.assertEqual(adapter.receive(request)[0].options, ("allow_once", "deny"), path)
        for number, command in enumerate(commands):
            request = frame("bash_prefix_request", request_id=f"b{number}")
            request["request"]["input"]["command"] = command
            self.assertEqual(adapter.receive(request)[0].options, ("allow_once", "deny"), command)

    def test_ordinary_paths_still_offer_session_scope(self):  # F3
        _, adapter, _, _ = open_claude()
        for number, path in enumerate(
            ("/repo/notes.txt", "/repo/src/claude.py", "/repo/docs/.claude-plugin-notes.md", "/repo/mcp.json")
        ):
            request = frame("write_request", request_id=f"o{number}")
            request["request"]["input"]["file_path"] = path
            self.assertIn("allow_session", adapter.receive(request)[0].options, path)


class ChatCommandLine(unittest.TestCase):
    def ps(self, table):
        def run(command, **_):
            self.assertIn("-ww", command)
            line = table.get(command[-1], "")
            return subprocess.CompletedProcess(command, 0 if line else 1, stdout=line + "\n", stderr="")

        return run

    def test_an_apostrophe_in_the_command_line_keeps_the_mode(self):  # N1
        table = {"3": "2 /bin/zsh -c x", "2": "1 claude --append-system-prompt it's --permission-mode auto"}
        self.assertEqual(chat_mode("claude", chat_argv("claude", 3, self.ps(table))), "auto")

    def test_a_node_run_harness_is_found(self):  # N1
        table = {"3": "2 /bin/zsh -c x", "2": "1 node /opt/lib/node_modules/@anthropic/claude --permission-mode auto"}
        self.assertEqual(chat_mode("claude", chat_argv("claude", 3, self.ps(table))), "auto")

    def test_a_missing_ps_gives_no_command_line(self):  # N1
        def missing(*_, **__):
            raise FileNotFoundError("ps")

        self.assertEqual(chat_argv("claude", 3, missing), ())


class CodexWithoutAChatMode(unittest.TestCase):
    def test_no_reviewer_is_sent_and_either_is_accepted(self):  # N2
        for reviewer, label in (("user", "manual"), ("auto_review", "auto")):
            with self.subTest(reviewer=reviewer):
                _, _, sent, events = open_codex(reviewer=reviewer)
                self.assertNotIn("approvalsReviewer", sent[-1]["params"])
                self.assertEqual((events[0].kind, events[0].mode), ("ready", label))
        _, _, _, events = open_codex(reviewer="guardian_subagent")
        self.assertEqual((events[0].kind, events[0].mode), ("ready", "auto"))


class HarnessTable(unittest.TestCase):
    """One walk over every harness fact the adapters rely on (D12, L1, L2)."""

    SOURCE = re.compile(r"(https://\S+\.\S+|`[a-z]+ [^`]+`|tests/fixtures/\S+)")

    def entries(self):
        for name, harness in HARNESS_FACTS.items():
            yield name, harness.set_by
            yield from ((name, entry) for entry in harness.chat_flags)
            yield from ((name, entry) for entry in harness.reported)
            yield from ((name, entry) for entry in harness.config)

    def test_every_entry_names_its_source(self):  # L1
        self.assertEqual(set(HARNESS_FACTS), {"claude", "codex", "cursor", "opencode", "droid", "devin"})
        for name, entry in self.entries():
            with self.subTest(name=name, entry=entry):
                self.assertRegex(entry.source, self.SOURCE)

    def test_every_chat_flag_maps_and_is_passed_on(self):  # S11 B1
        for name, harness in HARNESS_FACTS.items():
            binary = {"cursor": "agent"}.get(name, name)
            for flag in harness.chat_flags:
                spellings = [(spelling,) for spelling in flag.names]
                if flag.value is not None:
                    spellings = [(spelling, flag.value) for spelling in flag.names]
                    spellings += [(f"{spelling}={flag.value}",) for spelling in flag.names if spelling.startswith("--")]
                for spelling in spellings:
                    argv = (binary, "--verbose", *spelling)
                    with self.subTest(name=name, argv=argv):
                        self.assertEqual(chat_mode(name, argv), flag.mode)
                        plan = candidate(name, {}, lambda found: f"/bin/{found}", chat_argv=argv)
                        self.assertEqual(plan.mode, flag.mode)
                        for token in flag.argv:
                            self.assertIn(token, plan.argv)
                        adapter = plan.codec(lambda _: None, CLAUDE_SESSION, None)
                        self.assertEqual(adapter.chat.protocol, flag.protocol)
                        if not flag.argv and flag.protocol is None:
                            self.assertIn("no documented way", harness.set_by.text)
            with self.subTest(name=name, argv="none"):
                self.assertIsNone(chat_mode(name, (binary, "--verbose")))

    def ready_mode(self, name, field, value):
        if name == "claude":
            init = copy.deepcopy(CLAUDE["initialize_default"])
            init["response"]["response"]["current_permission_mode"] = value
            sent = []
            adapter = claude_plan().codec(sent.append, CLAUDE_SESSION, None)
            adapter.open("/repo", None)
            init["response"]["request_id"] = sent[-1]["request_id"]
            return adapter.receive(init)[0]
        if name == "codex":
            if field == "approvalsReviewer":
                return open_codex(reviewer=value)[3][0]
            return open_codex(reviewer="user", policy=value)[3][0]
        if name == "cursor":
            return open_cursor(value)[2][0]
        if name == "devin":
            return open_devin(value)[2][0]
        return open_droid(value)[2][0]

    def test_every_reported_mode_is_accepted_by_its_own_name(self):  # S11 S157
        for name, harness in HARNESS_FACTS.items():
            for reported in harness.reported:
                with self.subTest(name=name, value=reported.value):
                    event = self.ready_mode(name, reported.field, reported.value)
                    self.assertEqual((event.kind, event.mode), ("ready", reported.mode or "manual"))

    def forms(self, path):
        sample = path + "settings.json" if path.endswith("/") else path
        if sample.startswith("~/"):
            rest = sample[2:]
            bases = [f"/Users/u/{rest}", f"~/{rest}", f"$HOME/{rest}", rest]
        elif sample.startswith("/"):
            bases = [sample]
        else:
            bases = [f"/repo/{sample}", f"./{sample}", sample, f"/repo/sub/dir/{sample}"]
        forms = []
        for base in bases:
            forms += [base, base.upper(), f"echo x >{base}", f"echo x >> {base}", f"echo x>>{base}", f"cp a '{base}'"]
        if path.endswith("/") and not path.startswith("/"):
            forms.append(f"rm -rf {path.removeprefix('~/').rstrip('/')}")
        return forms

    def test_every_config_location_matches_in_every_real_form(self):  # S10 L2 B2
        for name, harness in HARNESS_FACTS.items():
            for location in harness.config:
                for form in self.forms(location.path):
                    with self.subTest(name=name, form=form):
                        self.assertTrue(touches_config({"command": form}), form)

    def test_ordinary_paths_are_not_config(self):  # S10
        for path in (
            "claude.py",
            "src/opencode.py",
            "my-opencode.json",
            "mcp.json",
            "/repo/notes.txt",
            "/repo/docs/.claude-plugin-notes.md",
            "/repo/src/claude/settings.py",
            "/repo/devin/config.json",
            "opencode.json.md",
        ):
            with self.subTest(path=path):
                self.assertFalse(touches_config({"file_path": path}), path)

    def test_the_named_locations_are_in_the_table(self):  # B2
        for path in (
            "~/.config/devin/config.json",
            "/repo/.devin/config.local.json",
            "/repo/opencode.json",
            "/repo/opencode.jsonc",
            "/repo/.opencode/opencode.jsonc",
            "~/.config/opencode/opencode.json",
            "~/.claude.json",
            "/repo/.mcp.json",
            "/Library/Application Support/ClaudeCode/managed-settings.json",
            "~/.factory/settings.json",
            "~/.cursor/cli-config.json",
        ):
            with self.subTest(path=path):
                self.assertTrue(touches_config(path), path)


class UnknownMessages(unittest.TestCase):
    """D11: a message the protocol does not define is reported as unknown; a defined one that is not used is not."""

    def kinds(self, events):
        return [event.kind for event in events]

    def test_claude(self):
        _, adapter, _, _ = open_claude()
        renamed = {**frame("result_auto_blocked"), "type": "turn_result"}
        self.assertEqual(self.kinds(adapter.receive(renamed)), ["unknown"])
        self.assertEqual(adapter.receive({"type": "rate_limit_event", "rate_limit_info": {}}), ())
        self.assertEqual(adapter.receive({"type": "system", "subtype": "hook_started"}), ())

    def test_codex(self):
        _, adapter, _, _ = open_codex()
        renamed = {"method": "turn/finished", "params": {"threadId": SESSION, "turn": {"id": "t1"}}}
        self.assertEqual([(e.kind, e.text) for e in adapter.receive(renamed)], [("unknown", "turn/finished")])
        known = {"method": "thread/tokenUsage/updated", "params": {"threadId": SESSION}}
        self.assertEqual(adapter.receive(known), ())

    def test_acp_harnesses(self):
        for name in ("cursor", "devin", "opencode"):
            with self.subTest(name=name):
                adapter = candidate(name, {}, lambda found: f"/bin/{found}").codec(lambda _: None, "s", None)
                renamed = {"jsonrpc": "2.0", "method": "session/changed", "params": {"sessionId": "s"}}
                self.assertEqual(self.kinds(adapter.receive(renamed)), ["unknown"])
                known = {"jsonrpc": "2.0", "method": "session/update", "params": {"sessionId": "other"}}
                self.assertEqual(adapter.receive(known), ())
                self.assertEqual(adapter.receive({"jsonrpc": "2.0", "method": "_vendor/notice", "params": {}}), ())

    def test_documented_vendor_messages_are_not_unknown(self):
        # verifier-t5c V1: Cursor's ACP extensions (https://cursor.com/docs/cli/acp) and Claude's
        # SDKConversationResetMessage are defined messages, so they must never count as unknown.
        cursor = candidate("cursor", {}, lambda found: f"/bin/{found}").codec(lambda _: None, "s", None)
        for method in ("cursor/update_todos", "cursor/task", "cursor/generate_image"):
            with self.subTest(method=method):
                self.assertEqual(cursor.receive({"jsonrpc": "2.0", "method": method, "params": {"sessionId": "s"}}), ())
        for number, method in enumerate(("cursor/ask_question", "cursor/create_plan")):
            with self.subTest(method=method):
                request = {"jsonrpc": "2.0", "id": 900 + number, "method": method, "params": {"sessionId": "s"}}
                self.assertEqual(cursor.receive(request), ())
        _, claude, _, _ = open_claude()
        self.assertEqual(claude.receive({"type": "conversation_reset", "session_id": SESSION}), ())

    def test_droid(self):
        adapter = DroidAdapter(lambda _: None)
        header = {"jsonrpc": "2.0", "factoryApiVersion": "1.0.0", "factoryProtocolVersion": "1.332.0"}
        renamed = {**header, "type": "notification", "method": "droid.session_event", "params": {}}
        self.assertEqual(self.kinds(adapter.receive(renamed)), ["unknown"])
        known = {**header, "type": "notification", "method": "droid.session_notification", "params": {}}
        self.assertEqual(adapter.receive(known), ())


class OneProcessAcrossTurns(unittest.TestCase):
    STUB = """
import json, sys
init = json.load(open(sys.argv[1]))
for line in sys.stdin:
    msg = json.loads(line)
    if msg["type"] == "control_request":
        init["response"]["request_id"] = msg["request_id"]
        print(json.dumps(init), flush=True)
    elif msg["type"] == "user":
        print(json.dumps({"type": "user", "uuid": msg["uuid"], "isReplay": True, "parent_tool_use_id": None,
                          "message": {"role": "user", "content": msg["message"]["content"]}}), flush=True)
        print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "done"}), flush=True)
"""

    def test_one_claude_process_serves_every_turn(self):  # S50 S96
        with tempfile.TemporaryDirectory() as tmp:
            stub, fixture = Path(tmp, "stub.py"), Path(tmp, "init.json")
            stub.write_text(self.STUB)
            fixture.write_text(json.dumps(CLAUDE["initialize_default"]))
            plan = claude_plan()
            transport = ProcessTransport(
                (sys.executable, "-I", str(stub), str(fixture)),
                tmp,
                {"PATH": os.environ.get("PATH", "")},
                lambda send: plan.codec(send, CLAUDE_SESSION, None),
            )
            try:
                transport.open(tmp, None)
                self.assertEqual(self.next_kind(transport, "ready", "failed"), "ready")
                pid = transport.pid
                for number in range(2):
                    uuid = f"0000000{number}-2222-4333-8444-555555555555"
                    transport.codec.prompt(f"turn {number}", uuid)
                    seen = []
                    while "turn_ended" not in seen:
                        seen.append(self.next_kind(transport))
                    self.assertIn("prompt_echoed", seen)
                    self.assertEqual(transport.pid, pid)
                    self.assertIsNone(transport._proc.poll())
            finally:
                transport.close()

    def next_kind(self, transport, *wanted):
        for _ in range(200):
            event = transport.poll(0.05)
            if (
                event is not None
                and getattr(event, "kind", None) not in ("output", None)
                and (not wanted or event.kind in wanted)
            ):
                return event.kind
        self.fail("no event")


if __name__ == "__main__":
    unittest.main()
