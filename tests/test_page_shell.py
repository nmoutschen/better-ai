"""Tests for the shared live page in src/better_ai/page/: the shell, the server, the conversation and the verbs `serve`,
`wait`, `reply`, `status` and `pending`.

The page under test is a minimal fixture, not a skill's: its spec is put in `page.PAGES` for the skill whose unit kind it
borrows (`code-better`, `.code/<slug>`), and its main section and events schema live in this test, not in a skill package.
"""

import contextlib
import http.client
import inspect
import io
import json
import os
import socket
import struct
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

import better  # noqa: E402

from better_ai import cli, code, page, paths, resources, schema  # noqa: E402

assert code  # imported so its own registration, if any, happens before the tests replace it

FIXTURE_MAIN = '<section id="fixture-main"><h2>Fixture</h2></section>'
FIXTURE_JS = "document.title = 'fixture';"
EVENTS = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "fixture-events.schema.json",
    "x-files": ["conversation.jsonl"],
    "type": "object",
    "properties": {"type": {"enum": ["comment", "note", "approve", "reply", "status", "accepted", "accept", "answer"]}},
    "allOf": [
        {
            "if": {"required": ["type"], "properties": {"type": {"const": "approve"}}},
            "then": {
                "type": "object",
                "required": ["type", "at", "by", "id", "text"],
                "additionalProperties": False,
                "properties": {
                    "type": {"const": "approve"},
                    "at": {"type": "string"},
                    "by": {"const": "user"},
                    "id": {"type": "string"},
                    "text": {"type": "string", "minLength": 1},
                },
            },
        }
    ],
}


def fixture_spec(agent="coordinator", capabilities=("pins", "approve"), **more):
    return page.PageSpec(
        title="Fixture page",
        agent=agent,
        main="fixture/main.html",
        load=lambda unit: {"unit": unit.slug, "items": [1, 2]},
        events="fixture-events.schema.json",
        assets={"/fixture.js": "fixture/fixture.js"},
        js=("/fixture.js",),
        capabilities=tuple(capabilities),
        **more,
    )


class FakeDriver:
    """What the page server needs of the driver, with nothing behind it."""

    session = tag = "00000000-0000-4000-8000-000000000000"
    harness = "claude"

    def snapshot(self):
        return {"state": "idle", "since": time.time(), "age": 0.0, "open_approvals": 0}

    def agent(self):
        return {"state": "idle", "mark_age": 0.0, "approvals": []}

    def check_alive(self):
        return True

    @property
    def error(self):
        return None

    def idle_expired(self):
        return False

    def can_linger(self):
        return True

    def enqueue(self, event):
        pass

    def tab_paired(self):
        pass


class Fixture(unittest.TestCase):
    """A scratch unit `.code/fix` with a page spec registered for code-better, and no real browser."""

    spec_agent = "coordinator"
    capabilities = ("pins", "approve")

    def setUp(self):
        environment = mock.patch.dict(os.environ, better.stub_env("code-better"))  # a stub harness is the user's own
        environment.start()
        self.addCleanup(environment.stop)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(os.path.realpath(tmp.name))
        self.unit_dir = self.root / ".code" / "fix"
        self.unit_dir.mkdir(parents=True)
        (self.unit_dir / "code.json").write_text("{}\n")
        self.unit_arg = str(self.unit_dir)
        schemas = self.root / "fixture-schemas"
        schemas.mkdir()
        (schemas / "fixture-events.schema.json").write_text(json.dumps(EVENTS))
        self.docs = schema.load_schemas(resources.path("schemas"), schemas)
        self.spec = fixture_spec(self.spec_agent, self.capabilities)
        bundled = {"fixture/main.html": FIXTURE_MAIN, "fixture/fixture.js": FIXTURE_JS}
        real_text, real_bytes = resources.read_text, resources.read_bytes

        def text(name):
            return bundled[name] if name in bundled else real_text(name)

        def data(name):
            return bundled[name].encode() if name in bundled else real_bytes(name)

        for target in (
            mock.patch.object(page, "PAGES", {"code-better": self.spec}),
            mock.patch.object(page, "load_docs", lambda skill: self.docs),
            mock.patch.object(resources, "read_text", text),
            mock.patch.object(resources, "read_bytes", data),
            mock.patch.object(page.webbrowser, "open", return_value=True),  # never a real browser
            mock.patch.object(page, "TICK", 0.05),
            mock.patch.dict(os.environ, {"BETTER_AI_SKILL": "code-better"}),
            mock.patch.object(sys, "stdout", io.StringIO()),  # the server prints each user event, as `serve` does
        ):
            target.start()
            self.addCleanup(target.stop)
        self.opened = page.webbrowser.open
        self.tokens = {}

    # --- helpers

    def cli(self, *argv, stdin=""):
        done = better.call("code-better", *argv, stdin=stdin)
        return done.returncode, done.stdout, done.stderr

    def unit(self):
        return paths.resolve_unit(self.unit_arg, cli.load(resources.build_info()))

    def serve(self, spec=None):
        """A started server for the unit, as (server, host:port)."""
        unit = self.unit()
        spec = spec or self.spec
        conv = page.Conversation(unit, spec, self.docs)
        info = resources.build_info()
        server = page.make_server(unit, spec, conv, info)
        threading.Thread(target=server.serve_forever, kwargs={"poll_interval": page.POLL}, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.conv = conv
        host = f"127.0.0.1:{server.server_address[1]}"
        driven = page.DrivenPage(server, unit)
        driven.driver, driven.ready = FakeDriver(), True
        paths.write_state(unit, ".server", f"http://{host}/".encode())
        self.tokens[host] = driven.pairing.exchange(driven.pairing.issue(), driven.origin)  # a paired tab
        return server, host

    def with_token(self, host, headers):
        if host not in self.tokens:
            return headers
        return {**headers, "X-Page-Token": self.tokens[host], "Sec-Fetch-Site": "same-origin"}

    def get(self, host, path, with_type=False):
        connection = http.client.HTTPConnection(host, timeout=10)
        connection.request("GET", path, headers=self.with_token(host, {"Host": host}))
        response = connection.getresponse()
        body = response.read()
        return (
            (response.status, body, response.getheader("Content-Type") or "") if with_type else (response.status, body)
        )

    def rpc(self, host, method, params, origin=True):
        connection = http.client.HTTPConnection(host, timeout=10)
        headers = {"Host": host, "Content-Type": "application/json"}
        if origin:
            headers["Origin"] = f"http://{host}"
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
        connection.request("POST", "/rpc", body, self.with_token(host, headers))
        return json.loads(connection.getresponse().read())

    def log(self):
        path = self.unit_dir / "conversation.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def seed(self, *events):
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with (self.unit_dir / "conversation.jsonl").open("a") as handle:
            for event in events:
                handle.write(json.dumps({"at": stamp, **event}) + "\n")


class ShellTest(Fixture):
    def strips(self, agent):
        text = page.shell(fixture_spec(agent))
        found = {}
        for name in ("offline", "unwatched"):
            start = text.index(f'id="{name}"')
            start = text.index(">", start) + 1
            found[name] = text[start : text.index("</p>", start)]
        return found

    def test_the_strips_are_the_same_text_for_every_page_except_the_role_S45(self):
        # No `wait` is connected: the strips are hidden but their text is what the page shows when it needs them.
        a, b = self.strips("coordinator"), self.strips("architect")
        self.assertEqual(a["unwatched"].replace("coordinator", "ROLE"), b["unwatched"].replace("architect", "ROLE"))
        self.assertEqual(a["offline"].replace("coordinator", "ROLE"), b["offline"].replace("architect", "ROLE"))
        self.assertIn("is not watching this page", a["unwatched"])
        self.assertIn("is closed", a["offline"])
        self.assertNotEqual(a["unwatched"], b["unwatched"])

    def test_shell_holds_head_header_conversation_and_both_strips(self):
        text = page.shell(self.spec)
        for part in (
            'href="/page.css"',
            'src="/page.js"',
            "<header",
            'class="notes"',
            'class="offline"',
            'class="unwatched"',
        ):
            self.assertIn(part, text)
        self.assertIn(FIXTURE_MAIN, text)
        self.assertIn('<script src="/fixture.js">', text)
        self.assertNotIn("%%", text)

    def test_the_shell_escapes_constants_and_fills_no_record_data_S44(self):
        spec = fixture_spec(agent="a<b>&")
        spec = page.PageSpec(**{**spec.__dict__, "title": "T</title><script>alert(1)</script>"})
        text = page.shell(spec)
        self.assertNotIn("<script>alert(1)", text)
        self.assertIn("T&lt;/title&gt;&lt;script&gt;", text)
        config = text.split('id="page-config">')[1].split("</script>")[0]
        self.assertNotIn("<", config)
        self.assertEqual(json.loads(config)["title"], spec.title)
        self.assertEqual(json.loads(config)["capabilities"], ["pins", "approve"])
        spec = page.PageSpec(
            **{**self.spec.__dict__, "title": "%%MAIN%%"}
        )  # a marker inside a value is not filled twice
        self.assertEqual(page.shell(spec).count(FIXTURE_MAIN), 1)

    def test_a_static_page_holds_its_files_and_its_data_and_links_nothing(self):
        data = {"note": "</script><b>&", "n": [1, 2]}
        text = page.static_page(self.spec, data)
        for link in ('href="/page.css"', 'src="/page.js"', 'src="/fixture.js"'):
            self.assertNotIn(link, text)
        self.assertIn(FIXTURE_JS, text)
        self.assertIn("function pageConversation", text)
        element = text.split('id="page-data">')[1].split("</script>")[0]
        self.assertNotIn("<", element)
        self.assertEqual(json.loads(element), {**data, "quiet_after": 1800})  # every page's data holds the threshold
        self.assertLess(text.index('id="page-data"'), text.index('id="page-config"'))
        with (
            mock.patch.object(page, "shell", return_value="<p>no links</p>"),
            self.assertRaisesRegex(ValueError, "does not link /page.css"),
        ):
            page.static_page(self.spec, data)

    def test_the_research_board_lists_its_agents_in_the_side_column_above_the_conversation_not_under_the_map(self):
        from better_ai.research import board

        text = page.shell(board.SPEC)
        main = text[text.index("<main") : text.index("</main>")]
        aside = text[text.index('<aside class="notes"') : text.index("</aside>")]
        self.assertNotIn('id="agents"', main)
        self.assertLess(aside.index('id="agents"'), aside.index('id="notes-h"'))


class ServerTest(Fixture):
    def test_the_assets_of_the_table_are_served_and_nothing_else_S44(self):
        _, host = self.serve()
        for path, kind in (
            ("/", "text/html"),
            ("/page.js", "text/javascript"),
            ("/page.css", "text/css"),
            ("/fixture.js", "text/javascript"),
        ):
            status, body, header = self.get(host, path, with_type=True)
            self.assertEqual(status, 200, path)
            self.assertTrue(body, path)
            self.assertTrue(header.startswith(kind), path)
        for path in (
            "/../src",
            "/unknown.js",
            "/%2e%2e/src",
            "/page.js/../x",
            "/..%2fsrc%2fbetter_ai",
            "//etc/passwd",
            "/shell.html",
            "/page/page.js",
        ):
            self.assertEqual(self.get(host, path)[0], 404, path)

    def test_data_carries_the_page_data(self):
        _, host = self.serve()
        status, body = self.get(host, "/data")
        data = json.loads(body)
        self.assertEqual((status, data["unit"], data["items"]), (200, "fix", [1, 2]))
        self.assertIsInstance(data["now"], float)

    def test_a_request_for_another_host_is_refused(self):
        server, host = self.serve()
        connection = http.client.HTTPConnection(host, timeout=10)
        connection.request("GET", "/", headers={"Host": "evil.example"})
        self.assertEqual(connection.getresponse().status, 403)

    def test_the_user_sends_a_note_and_the_server_sets_by_and_at(self):
        _, host = self.serve()
        answer = self.rpc(host, "note", {"id": "m1", "text": "hello", "to": None})
        self.assertEqual(answer["result"], "saved")
        (event,) = self.log()
        self.assertEqual((event["type"], event["by"], event["text"]), ("note", "user", "hello"))
        self.assertEqual(
            self.rpc(host, "note", {"id": "m2", "text": "x", "to": None, "by": "coordinator"})["error"]["code"], -32602
        )

    def test_a_saved_event_is_not_a_bug_when_stdout_is_closed(self):
        _, host = self.serve()

        class Closed:
            def write(self, text):
                raise OSError(9, "Bad file descriptor")

            def flush(self):
                raise OSError(9, "Bad file descriptor")

        with mock.patch.object(sys, "stdout", Closed()):
            answer = self.rpc(host, "note", {"id": "m1", "text": "kept", "to": None})
        self.assertEqual(answer["result"], "saved")
        self.assertEqual(len(self.log()), 1)

    def test_a_client_that_closes_mid_request_leaves_no_traceback(self):
        server, host = self.serve()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            for _ in range(3):
                client = socket.create_connection(server.server_address)
                client.sendall(f"GET /data HTTP/1.1\r\nHost: {host}\r\n\r\n".encode())
                client.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))  # close with a reset
                client.close()
            with (
                mock.patch.object(page.Handler, "send_json", side_effect=BrokenPipeError(32, "Broken pipe")),
                mock.patch.object(page.Handler, "send", side_effect=ConnectionResetError(54, "reset")),
            ):
                for path in ("/data", "/rev"):
                    with contextlib.suppress(http.client.RemoteDisconnected):
                        self.get(host, path)
            time.sleep(0.3)
        self.assertNotIn("Traceback", err.getvalue())
        self.assertNotIn("page server", err.getvalue())

    def test_the_event_stream_keeps_invalid_positions_and_sends_the_valid_events_after_them(self):
        _, host = self.serve()
        self.seed({"type": "note", "by": "user", "id": "m1", "text": "before", "to": None})
        with (self.unit_dir / "conversation.jsonl").open("a") as handle:
            handle.write('{"type": "note", "text": NaN}\n{"type": "note", "text": 1e999}\nnot json\n')
        self.seed({"type": "note", "by": "user", "id": "m2", "text": "after", "to": None})
        status, body = self.get(host, "/events?after=1")
        self.assertEqual(status, 200)
        events = json.loads(body)
        self.assertEqual(events["total"], 5)
        self.assertEqual(events["events"][:3], [{}, {}, {}])
        self.assertEqual(len(events["events"]), 4)
        self.assertEqual(events["events"][-1]["id"], "m2")

    def test_a_log_that_is_a_folder_is_answered_as_the_file_error_in_every_reader(self):
        server, host = self.serve()
        (self.unit_dir / "conversation.jsonl").mkdir()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            status, body = self.get(host, "/events?after=0")
            self.assertEqual(status, 500)
            self.assertIn("conversation.jsonl", body.decode())
            self.assertNotIn("hit a bug", body.decode())
            sent = self.rpc(host, "note", {"id": "m1", "text": "hi", "to": None})
            self.assertIn("conversation.jsonl", sent["error"]["message"])
            self.assertNotIn("hit a bug", sent["error"]["message"])
        self.assertNotIn("Traceback", err.getvalue())
        self.assertNotIn("bug", err.getvalue())

    def test_serve_refuses_to_start_on_a_log_that_is_a_folder(self):
        (self.unit_dir / "conversation.jsonl").mkdir()
        code_, out, err = self.cli("serve", self.unit_arg, "--no-browser", "--once")
        self.assertEqual(code_, 1, err)
        self.assertRegex(out, r"^driver: off refused: .*conversation\.jsonl")
        self.assertFalse((self.unit_dir / ".server").exists())

    def test_a_post_from_another_origin_is_refused(self):
        _, host = self.serve()
        connection = http.client.HTTPConnection(host, timeout=10)
        connection.request(
            "POST", "/rpc", "{}", {"Host": host, "Content-Type": "application/json", "Origin": "http://evil.example"}
        )
        self.assertEqual(connection.getresponse().status, 403)

    def test_approve_is_accepted_where_declared_and_refused_where_not_S47(self):
        _, host = self.serve()
        sent = {"id": "approval-1", "text": "Approved"}
        self.assertEqual(self.rpc(host, "approve", sent)["result"], "saved")
        self.assertEqual(self.log()[-1]["type"], "approve")
        bad = self.rpc(host, "approve", {"id": "approval-2"})  # the page's own schema still applies
        self.assertEqual(bad["error"]["code"], -32602)
        plain = fixture_spec(capabilities=("pins",))
        _, other = self.serve(plain)
        before = len(self.log())
        refused = self.rpc(other, "approve", sent)
        self.assertEqual(refused["error"]["code"], -32601)
        self.assertEqual(len(self.log()), before)
        self.assertNotIn("approve", plain.tracked())
        self.assertIn("approve", self.spec.tracked())

    def test_the_methods_follow_the_capabilities(self):
        spec = fixture_spec(capabilities=("pins", "accept", "decisions", "confirm", "approve"))
        self.assertEqual(
            spec.sendable(), ("note", "comment", "delete", "accept", "reopen", "answer", "confirm", "approve")
        )
        self.assertEqual(spec.tracked(), ("note", "comment", "answer", "confirm", "approve"))
        self.assertEqual(fixture_spec(capabilities=()).sendable(), ("note",))

    def test_a_failing_data_handler_prints_the_traceback_with_skill_and_hash_and_answers_500_S46(self):
        spec = page.PageSpec(**{**self.spec.__dict__, "load": mock.Mock(side_effect=RuntimeError("boom"))})
        _, host = self.serve(spec)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            status, body = self.get(host, "/data")
        self.assertEqual(status, 500)
        self.assertIn(page.BUG_TEXT, body.decode())
        text = err.getvalue()
        self.assertIn("code-better source", text)
        self.assertIn("RuntimeError: boom", text)
        self.assertIn("Traceback", text)

    def test_a_failing_page_event_shows_the_bug_text_and_the_server_prints_the_traceback_S46(self):
        _, host = self.serve()
        err = io.StringIO()
        with (
            mock.patch.object(page.Conversation, "append", side_effect=RuntimeError("disk gone")),
            contextlib.redirect_stderr(err),
        ):
            answer = self.rpc(host, "note", {"id": "m1", "text": "keep me", "to": None})
        self.assertEqual(answer["error"]["code"], -32603)
        self.assertEqual(answer["error"]["message"], "The page hit a bug: ask the agent to restart it and report it")
        self.assertIn("RuntimeError: disk gone", err.getvalue())
        self.assertIn("code-better source", err.getvalue())
        # the server is still up
        self.assertEqual(self.get(host, "/")[0], 200)


class ConversationTest(Fixture):
    def test_a_log_that_is_a_folder_or_unreadable_is_a_file_error_not_a_bug(self):
        log = self.unit_dir / "conversation.jsonl"
        log.mkdir()
        for argv in (("pending", self.unit_arg), ("reply", self.unit_arg)):
            with self.subTest(argv[0]):
                code_, _, err = self.cli(*argv, stdin="hi")
                self.assertEqual(code_, 1, err)
                self.assertIn("conversation.jsonl", err)
                self.assertNotIn("bug in", err)
        log.rmdir()
        log.write_text("")
        log.chmod(0)
        self.addCleanup(log.chmod, 0o644)
        if os.access(log, os.R_OK):  # running as root: nothing is unreadable
            return
        code_, _, err = self.cli("pending", self.unit_arg)
        self.assertEqual(code_, 1, err)
        self.assertIn("conversation.jsonl", err)
        self.assertNotIn("bug in", err)

    def test_events_are_checked_against_the_shared_and_the_page_schema_before_a_write(self):
        conv = page.Conversation(self.unit(), self.spec, self.docs)
        with self.assertRaises(page.EventError):
            conv.append({"type": "note", "by": "user", "id": "m1"})  # no text
        with self.assertRaises(page.EventError):
            conv.append({"type": "approve", "by": "user", "id": "a1"})  # the fixture's schema wants text
        self.assertEqual(self.log(), [])
        conv.append({"type": "note", "by": "user", "id": "m1", "text": "  split?", "to": None})
        self.assertEqual(len(self.log()), 1)  # one line: U+2028 is escaped

    def test_an_event_gets_the_time_in_utc_with_z_and_an_unreadable_line_keeps_its_position(self):
        conv = page.Conversation(self.unit(), self.spec, self.docs)
        conv.append({"type": "note", "by": "user", "id": "m1", "text": "hi", "to": None})
        self.assertRegex(conv.events()[0]["at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertRegex(page.now(), r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        (self.unit_dir / "conversation.jsonl").write_text('{"type": "note"}\nnot json\n{"type": "reply"}\n')
        self.assertEqual([e.get("type") for e in conv.events()], ["note", None, "reply"])

    def test_clean_keeps_json_values_and_cuts_long_text_and_from_user_is_what_the_page_sent(self):
        value = page.clean({"text": "x" * 6000, "n": 1, "ok": True, "list": list(range(60)), "obj": object()})
        self.assertEqual(len(value["text"]), 5000)
        self.assertEqual((value["n"], value["ok"], len(value["list"]), value["obj"]), (1, True, 50, None))
        self.assertTrue(page.from_user({"type": "note", "by": "user"}))
        for event in ({"type": "reply", "by": "agent"}, {"type": "closed", "by": "w2"}, {"type": "note"}, {}):
            self.assertFalse(page.from_user(event), event)

    def test_concurrent_appends_never_interleave_inside_a_line_S62(self):
        conv = page.Conversation(self.unit(), self.spec, self.docs)

        def worker(n):
            for i in range(25):
                conv.append({"type": "note", "by": "user", "id": f"m{n}-{i}", "text": "x" * 200, "to": None})

        threads = [threading.Thread(target=worker, args=(n,)) for n in range(6)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(len(self.log()), 150)
        # a second writer that is not this process's lock: the agent's `reply` from another process-like caller
        other = page.Conversation(self.unit(), self.spec, self.docs)
        threads = [
            threading.Thread(
                target=lambda: [
                    other.write({"type": "reply", "by": "coordinator", "id": f"r{k}", "text": "y", "to": None})
                    for k in range(25)
                ]
            )
            for _ in range(4)
        ]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(len(self.log()), 250)

    def test_the_log_and_the_state_files_are_opened_without_following_a_symlink_S62(self):
        target = self.root / "elsewhere.jsonl"
        target.write_text("")
        os.symlink(target, self.unit_dir / "conversation.jsonl")
        conv = page.Conversation(self.unit(), self.spec, self.docs)
        with self.assertRaises(paths.Refused):
            conv.append({"type": "note", "by": "user", "id": "m1", "text": "x", "to": None})
        self.assertEqual(target.read_text(), "")
        os.symlink(target, self.unit_dir / ".conversation-seen")
        with self.assertRaises(paths.Refused):
            paths.write_state(self.unit(), ".conversation-seen", b"3")
        self.assertEqual(target.read_text(), "")


# What `pending` shows for an item beyond its state, by the name of the case in the table, as (item, field, value).
EXTRAS = {
    "an answer to a question the agent asked ends the wait": (
        "m1",
        "thread",
        [{"from": "coordinator", "text": "t"}, {"from": "user", "text": "t"}],
    ),
    "a comment sent again keeps its state, and is the same item": ("c2", "text", "edited"),
    "a reopened item is work again": ("c1", "reopened_because", "still wrong"),
    "an answer to what a worker closed is an item": ("m1", "about", "worker-2 closed Q4 as answered"),
}


class VerbsTest(Fixture):
    def test_reply_reads_its_text_from_stdin_with_an_apostrophe_S34(self):
        code_, out, err = self.cli("reply", self.unit_arg, stdin='It\'s done, "quoted" and `ticked`\n')
        self.assertEqual((code_, err), (0, ""))
        self.assertIn("Reply saved", out)
        (event,) = self.log()
        self.assertEqual(
            (event["type"], event["by"], event["text"], event["to"]),
            ("reply", "coordinator", 'It\'s done, "quoted" and `ticked`', None),
        )

    def test_reply_says_the_page_shows_it_only_while_a_server_answers(self):
        server, host = self.serve()
        code_, out, _ = self.cli("reply", self.unit_arg, "--to", "m1", stdin="ok")
        self.assertEqual(code_, 1)  # no such item
        self.seed({"type": "note", "by": "user", "id": "m1", "text": "q", "to": None})
        self.assertIn("Reply shown in the page.", self.cli("reply", self.unit_arg, "--to", "m1", stdin="ok")[1])
        server.shutdown()
        server.server_close()  # the address file stays, as after a SIGKILL
        self.assertTrue((self.unit_dir / ".server").exists())
        out = self.cli("reply", self.unit_arg, stdin="later")[1]
        self.assertIn("Reply saved; the page shows it when served.", out)
        self.assertEqual([e["text"] for e in self.log() if e["type"] == "reply"], ["ok", "later"])

    def test_reply_without_text_is_refused_and_writes_nothing(self):
        code_, out, err = self.cli("reply", self.unit_arg, stdin="  \n")
        self.assertEqual(code_, 1)
        self.assertIn("no text on stdin", err)
        self.assertEqual(self.log(), [])

    def test_reply_to_an_item_sets_its_state_in_the_same_write_and_reply_state_is_shared(self):
        self.seed({"type": "note", "by": "user", "id": "m1", "text": "q", "to": None})
        self.assertEqual(self.cli("reply", self.unit_arg, "--to", "m1", stdin="Which size?")[0], 0)
        self.assertEqual([e["type"] for e in self.log()], ["note", "reply", "status"])
        self.assertEqual(self.log()[-1]["status"], "done")
        self.assertEqual(self.cli("reply", self.unit_arg, "--to", "m1", "--state", "asked", stdin="More?")[0], 0)
        self.assertEqual(self.log()[-1]["status"], "asked")
        code_, _, err = self.cli("reply", self.unit_arg, "--to", "nope", stdin="x")
        self.assertEqual(code_, 1)
        self.assertIn("no comment or message with id nope", err)
        self.assertEqual(self.cli("reply", self.unit_arg, "--to", "m1", "--state", "accepted", stdin="x")[0], 2)

    def test_status_marks_items_and_accepted_needs_the_users_words_on_stdin(self):
        self.seed({"type": "note", "by": "user", "id": "m1", "text": "q", "to": None})
        self.assertEqual(self.cli("status", self.unit_arg, "working", "m1")[0], 0)
        self.assertEqual(self.log()[-1]["status"], "working")
        code_, _, err = self.cli("status", self.unit_arg, "accepted", "m1")
        self.assertEqual(code_, 1)
        self.assertIn("accepted needs the user's words", err)
        code_, out, _ = self.cli("status", self.unit_arg, "accepted", "m1", "--text", stdin="Looks right to me")
        self.assertEqual(code_, 0)
        self.assertEqual((self.log()[-1]["type"], self.log()[-1]["text"]), ("accepted", "Looks right to me"))
        self.assertEqual(self.cli("status", self.unit_arg, "done", "zzz")[0], 1)

    def test_status_refuses_an_unknown_id_and_an_answer_under_an_item_and_marks_an_answer_to_the_agent(self):
        self.seed(
            {"type": "comment", "by": "user", "id": "c1", "n": 1, "text": "too big"},
            {"type": "note", "by": "user", "id": "m1", "to": "c1", "text": "an answer"},
            {"type": "reply", "by": "coordinator", "id": "r1", "to": None, "text": "a question"},
            {"type": "note", "by": "user", "id": "m2", "to": "r1", "text": "answer to the agent"},
        )
        code_, _, err = self.cli("status", self.unit_arg, "done", "nope")
        self.assertEqual(code_, 1)
        self.assertIn("no comment or message with id nope", err)
        code_, _, err = self.cli("status", self.unit_arg, "done", "m1")
        self.assertEqual(code_, 1)
        self.assertIn("m1 answers c1", err)
        before = len(self.log())
        self.assertEqual(self.cli("status", self.unit_arg, "working", "m2")[0], 0)
        last = self.log()[before]
        self.assertEqual(
            (last["type"], last["to"], last["status"], last["by"]), ("status", "m2", "working", "coordinator")
        )
        self.assertEqual(self.cli("status", self.unit_arg, "accepted", "c1")[0], 1)  # the user's words are missing
        self.assertEqual(len(self.log()), before + 1)

    def test_status_closes_the_agents_own_message_but_not_a_reply_under_an_item(self):
        self.seed({"type": "note", "by": "user", "id": "m1", "text": "q", "to": None})
        self.assertEqual(self.cli("reply", self.unit_arg, stdin="Which size?")[0], 0)
        self.assertEqual(self.cli("reply", self.unit_arg, "--to", "m1", stdin="Done.")[0], 0)
        started, under = [e["id"] for e in self.log() if e["type"] == "reply"]
        code_, out, _ = self.cli("status", self.unit_arg, "done", started)
        self.assertEqual(code_, 0, out)
        self.assertEqual(
            {k: self.log()[-1][k] for k in ("type", "to", "status")},
            {"type": "status", "to": started, "status": "done"},
        )
        before = len(self.log())
        code_, _, err = self.cli("status", self.unit_arg, "done", under)  # a reply under an item: mark the item
        self.assertEqual(code_, 1)
        self.assertIn(f"no comment or message with id {under}", err)
        self.assertEqual(len(self.log()), before)

    def test_pending_selects_deliverable_items_from_the_shared_table_of_logs(self):
        """The page shows all open items. Pending only delivers states that need the agent in a fresh turn."""
        table = json.loads((HERE / "fixtures" / "threads.json").read_text())
        for case in table:
            with self.subTest(case["name"]):
                (self.unit_dir / "conversation.jsonl").unlink(missing_ok=True)
                self.seed(*case["log"])
                code_, out, _ = self.cli("pending", self.unit_arg)
                lines = out.splitlines()
                self.assertEqual(code_, 0)
                items = [event for event in map(json.loads, lines[:-1]) if "status" in event]
                expected = [item for item in case["work"] if item[1] in ("new", "replied", "followup", "reopened")]
                if case["name"] == "a comment sent again keeps its state, and is the same item":
                    expected = [["c2", "new"]]  # an edit of a settled item is not delivered (S15)
                self.assertEqual([[e["id"], e["status"]] for e in items], expected)
                self.assertEqual(lines[-1], f"{len(items)} not done.")
                for name, (item, field, expected) in EXTRAS.items():
                    if name == case["name"]:
                        got = next(e[field] for e in items if e["id"] == item)
                        if field == "thread":
                            got = [{k: v for k, v in t.items() if k != "at"} for t in got]
                        self.assertEqual(got, expected)

    def test_a_skill_without_a_page_refuses(self):
        with mock.patch.object(page, "PAGES", {}):
            code_, _, err = self.cli("pending", self.unit_arg)
        self.assertEqual(code_, 1)
        self.assertIn("has no page", err)


class ServeTest(Fixture):
    def run_serve(self, *flags):
        """`serve` on a thread, until its address file is there; returns (thread, result list, url)."""
        result = []
        out, err = io.StringIO(), io.StringIO()

        def go():
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                result.append(cli.main(["serve", self.unit_arg, *flags], stdin=io.StringIO("")))

        thread = threading.Thread(target=go, daemon=True)
        thread.start()
        deadline = time.time() + 15
        address = self.unit_dir / ".server"
        while not address.exists() and time.time() < deadline:
            time.sleep(0.05)
        self.assertTrue(address.exists(), "serve did not start")
        return thread, result, address.read_text(), out, err

    def test_once_serves_one_request_then_exits_and_opens_no_browser_S72_S34(self):
        thread, result, url, out, _ = self.run_serve("--no-browser", "--once")
        status, body = self.get(url.removeprefix("http://").rstrip("/"), "/")
        self.assertEqual(status, 200)
        self.assertIn("Fixture page", body.decode())
        thread.join(15)
        self.assertEqual(result, [0])
        self.assertFalse((self.unit_dir / ".server").exists())
        self.opened.assert_not_called()

    def test_a_port_in_use_is_a_refusal_in_one_line_not_a_bug(self):
        """S29, S30: an address that is taken is not an internal error, as it was not for the scripts before."""
        busy = socket.socket()
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        self.addCleanup(busy.close)
        code_, out, err = self.cli("serve", self.unit_arg, "--no-browser", "--port", str(busy.getsockname()[1]))
        self.assertEqual(code_, 1)
        self.assertNotIn("bug in better.pyz", err)
        lines = [line for line in out.splitlines() if line.startswith("driver:")]
        self.assertEqual(len(lines), 1, out)
        self.assertRegex(lines[0], r"^driver: off refused: .*cannot be served on port \d+ \(.*(in use|ddress).*\)\. ")
        self.assertFalse((self.unit_dir / ".server").exists())

    def test_serve_warns_on_an_invalid_record_and_still_serves_S72(self):
        self.seed({"type": "note", "by": "user", "id": "m1"})  # no text
        thread, result, url, out, err = self.run_serve("--once")
        self.assertEqual(self.get(url.removeprefix("http://").rstrip("/"), "/")[0], 200)
        thread.join(15)
        self.assertEqual(result, [0])
        self.assertIn("warning: ", err.getvalue())
        self.assertIn("conversation.jsonl:1", err.getvalue())

    def test_linger_ends_the_server_after_the_unit_stops(self):
        flag = {"stopped": False}
        spec = page.PageSpec(**{**self.spec.__dict__, "stopped": lambda unit: flag["stopped"]})
        page.PAGES["code-better"] = spec
        thread, result, url, out, _ = self.run_serve("--linger", "0.2")
        time.sleep(0.6)
        self.assertTrue(thread.is_alive())  # not stopped: it serves on
        flag["stopped"] = True
        thread.join(20)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result, [0])
        self.assertFalse((self.unit_dir / ".server").exists())


class EndingTest(Fixture):
    """How a served page ends: the reason of a driver failure, and the closed state a planned exit leaves the page."""

    def driven_page(self, driver):
        unit = self.unit()
        conv = page.Conversation(unit, self.spec, self.docs)
        server = page.make_server(unit, self.spec, conv, resources.build_info())
        serving = page.run_http(server)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        driven = page.DrivenPage(server, unit)
        driven.driver, driven.ready = driver, True
        host = f"127.0.0.1:{server.server_port}"
        self.tokens[host] = driven.pairing.exchange(driven.pairing.issue(), driven.origin)
        driven.tab_paired()
        return unit, conv, server, serving, driven, host

    def test_a_driver_failure_keeps_its_reason_B2(self):
        class Failed(FakeDriver):
            def check_alive(self):
                return False

            @property
            def error(self):
                return "boom"

        unit, conv, _, _, driven, _ = self.driven_page(Failed())
        run = mock.Mock(skill=code.SKILL)
        args = mock.Mock(once=False, linger=60)
        with mock.patch.object(page, "DRIVER_GRACE", 0):
            self.assertEqual(page.wait_until_done(args, run, unit, conv, driven), ("driver", "boom"))

    def test_after_a_planned_exit_the_server_still_answers_closed_for_one_poll_B1_S105(self):
        published = threading.Event()

        class Closing(FakeDriver):
            state = "idle"

            def agent(self):
                return {**super().agent(), "state": self.state}

            def close(self, kind="stopped", reason="server stopped"):
                self.state = "closed"
                published.set()

        unit, _, server, serving, driven, host = self.driven_page(Closing())
        stopper = threading.Thread(
            target=page.stop_serving,
            args=(server, serving, driven, unit, None, ("idle", "no page was open")),
            daemon=True,
        )
        with mock.patch.object(page, "CLOSED_GRACE", 10, create=True):
            stopper.start()
            self.assertTrue(published.wait(5))
            time.sleep(0.5)  # longer than the server takes to shut down at once
            status, body = self.get(host, "/agent")
            self.assertEqual((status, json.loads(body)["state"]), (200, "closed"))
            stopper.join(5)
        self.assertFalse(stopper.is_alive(), "the server waits for no more than the page's poll of closed")


class LinkReplyTest(Fixture):
    def reply_to_link(self, reply):
        """link_request against a socket that answers REPLY, as the unit's server does."""
        from better_ai.page.driver_state import write_private

        folder = tempfile.TemporaryDirectory(prefix="better-page-", dir="/tmp")
        self.addCleanup(folder.cleanup)
        path = os.path.join(folder.name, "link")
        listener = socket.socket(socket.AF_UNIX)
        self.addCleanup(listener.close)
        listener.bind(path)
        listener.listen(1)

        def answer():
            connection, _ = listener.accept()
            with connection:
                connection.makefile("rb").readline()
                connection.sendall(reply.encode() + b"\n")

        thread = threading.Thread(target=answer, daemon=True)
        thread.start()
        unit = self.unit()
        write_private(unit, page.LINK_SOCKET, path.encode())
        answered = page.link_request(unit)
        thread.join(5)
        return answered

    def test_link_passes_on_every_kind_the_server_answers_N7(self):
        for reply in (
            "on",
            "off no-browser: could not open a browser on this machine; run link where your browser runs",
            "off timeout: the new tab did not open the page in time; the old tab is still paired",
            "off no-server: the page server could not open a tab; run serve again",
        ):
            with self.subTest(reply):
                self.assertEqual(self.reply_to_link(reply), reply)

    def test_link_does_not_pass_on_an_answer_of_another_shape(self):
        self.assertRegex(self.reply_to_link("refused"), r"^off no-server: no page is being served for ")


class FakeDriverShapeTest(unittest.TestCase):
    def test_each_fake_driver_has_the_members_of_driver_in_the_same_shape(self):
        """A fake that calls a property as a method, or the reverse, hides a TypeError of the real one (B2)."""
        import test_page_pairing_v2

        from better_ai.page.driver import Driver

        source = inspect.getsource(Driver)

        def shape(cls, name):
            member = inspect.getattr_static(cls, name, None)
            if member is None:
                return "value" if f"self.{name} =" in source or f"self.{name}," in source else None
            if isinstance(member, property):
                return "property"
            return "method" if callable(member) else "value"

        for fake in (FakeDriver, test_page_pairing_v2.FakeDriver):
            for name in [n for n in vars(fake) if not n.startswith("_")]:
                self.assertEqual(shape(fake, name), shape(Driver, name), f"{fake.__module__}.FakeDriver.{name}")


class RegisterTest(unittest.TestCase):
    def test_a_bad_spec_is_a_bug_found_at_registration(self):
        skill = code.SKILL
        base = {"title": "t", "agent": "a", "main": "page/shell.html", "load": lambda unit: {}}
        for fields, message in (
            ({"capabilities": ("nope",)}, "unknown page capability"),
            ({"assets": {"/x.exe": "page/page.js"}}, "known file type"),
            ({"assets": {"/../x.js": "page/page.js"}}, "known file type"),
            ({"assets": {"/page.js": "page/page.js"}}, "shared page's own"),
            ({"assets": {"/x.js": "page/missing.js"}}, "not bundled"),
            ({"js": ("/x.js",)}, "not in the asset table"),
            ({"main": "page/missing.html"}, "not bundled"),
        ):
            with mock.patch.object(page, "PAGES", {}), self.assertRaises(ValueError, msg=str(fields)) as caught:
                page.register(skill, page.PageSpec(**{**base, **fields}))
            self.assertIn(message, str(caught.exception))

    def test_a_good_spec_registers_and_the_shared_files_are_bundled(self):
        with mock.patch.object(page, "PAGES", {}):
            spec = page.register(
                code.SKILL, page.PageSpec(title="t", agent="a", main="page/shell.html", load=lambda unit: {})
            )
            self.assertIs(page.PAGES["code-better"], spec)
        for name in ("page/shell.html", "page/page.js", "page/page.css"):
            self.assertTrue(resources.exists(name), name)


if __name__ == "__main__":
    unittest.main()
