"""Tests for the shared live page in src/better_ai/page/: the shell, the server, the conversation and the verbs `serve`,
`reply`, `status` and `pending`.

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
        for name in ("offline",):
            start = text.index(f'id="{name}"')
            start = text.index(">", start) + 1
            found[name] = text[start : text.index("</p>", start)]
        return found

    def test_the_strips_are_the_same_text_for_every_page_except_the_role_S45(self):
        # No agent is listening: the strips are hidden but their text is what the page shows when it needs them.
        a, b = self.strips("coordinator"), self.strips("architect")
        self.assertEqual(a["offline"].replace("coordinator", "ROLE"), b["offline"].replace("architect", "ROLE"))
        self.assertIn("is closed", a["offline"])

    def test_shell_holds_head_header_conversation_and_both_strips(self):
        text = page.shell(self.spec)
        for part in (
            'href="/page.css"',
            'src="/page.js"',
            "<header",
            'class="notes"',
            'class="offline"',
        ):
            self.assertIn(part, text)
        self.assertNotIn("unwatched", text)  # no not-watching notice: every served page has its own agent
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
        self.assertEqual(spec.tracked(), ("note", "comment", "answer", "approve"))  # a confirmation needs no reply (D8)
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


# What `pending` shows for a thread beyond its state, by the name of the case in the table, as (thread, field, value).
EXTRAS = {
    "an answer to a question the agent asked ends the wait": (
        "m1",
        "thread",
        [{"from": "coordinator", "id": "r1", "text": "t"}, {"from": "user", "id": "m2", "text": "t"}],
    ),
    "a comment sent again keeps its state, and is the same item": ("c2", "text", "edited"),
    "a reopened item is work again": ("c1", "reopened_because", "still wrong"),
    "an answer to what a worker closed is an item": ("x1", "about", "worker-2 closed Q4 as answered"),
    "transition: you reopen a report the agent posted on its own": ("r1", "reopened_because", "why"),
}
TABLE = json.loads((HERE / "fixtures" / "threads.json").read_text())
DEFAULT_KINDS = ("comment", "note")


def shape(thread: dict) -> list:
    return [thread["id"], thread["state"], thread["step"], thread.get("closed_by_user", thread.get("closedByUser"))]


class ThreadsTest(unittest.TestCase):
    def test_the_shared_table_of_logs_gives_each_thread_the_state_page_js_gives_it(self):
        """The same logs are run on page.js `pageThreads` in tests/page.test.js: both give the same threads."""
        for case in TABLE:
            with self.subTest(case["name"]):
                got = [
                    t for t in page.threads(case["log"], tuple(case.get("items", DEFAULT_KINDS))) if not t["deleted"]
                ]
                self.assertEqual([shape(t) for t in got], [shape(t) for t in case["threads"]])
                for thread, expected in zip(got, case["threads"], strict=True):
                    if "since" in expected:
                        self.assertEqual(thread["since"], expected["since"], thread["id"])

    def test_a_thread_holds_its_messages_the_latest_form_of_its_first_one_and_your_latest_event(self):
        log = [
            {"type": "comment", "id": "c1", "n": 1, "text": "first", "by": "user"},
            {"type": "reply", "id": "r1", "to": "c1", "text": "ok", "by": "coordinator"},
            {"type": "note", "id": "m1", "to": "r1", "text": "more", "by": "user"},
            {"type": "comment", "id": "c1", "n": 1, "text": "edited", "by": "user"},
            {"type": "comment", "id": "c2", "n": 2, "text": "gone", "by": "user"},
            {"type": "delete", "to": "c2", "by": "user"},
        ]
        c1, c2 = page.threads(log, DEFAULT_KINDS)
        self.assertEqual(c1["root"]["text"], "edited")
        self.assertEqual([m["id"] for m in c1["messages"]], ["c1", "r1", "m1"])
        self.assertEqual(c1["user_at"], 2)
        self.assertTrue(c2["deleted"])
        self.assertEqual([e["id"] for e, _, _ in page.all_items(log, DEFAULT_KINDS, "coordinator")], ["c1"])


class VerbsTest(Fixture):
    def test_reply_reads_its_text_from_stdin_with_an_apostrophe_S34(self):
        code_, out, err = self.cli("reply", self.unit_arg, stdin='It\'s done, "quoted" and `ticked`\n')
        self.assertEqual((code_, err), (0, ""))
        self.assertIn("Reply saved", out)
        event = self.log()[0]  # then the report's own done status
        self.assertEqual(
            (event["type"], event["by"], event["text"], event["to"]),
            ("reply", "coordinator", 'It\'s done, "quoted" and `ticked`', None),
        )

    def test_reply_says_the_page_shows_it_only_while_a_server_answers(self):
        server, host = self.serve()
        code_, out, _ = self.cli("reply", self.unit_arg, "--to", "m1", stdin="ok")
        self.assertEqual(code_, 1)  # no such item
        self.seed({"type": "note", "by": "user", "id": "m1", "text": "q", "to": None})
        self.assertIn(
            "Reply shown in the page.", self.cli("reply", self.unit_arg, "--to", "m1", "--read", "0", stdin="ok")[1]
        )
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
        self.assertEqual(self.cli("reply", self.unit_arg, "--to", "m1", "--read", "0", stdin="Which size?")[0], 0)
        self.assertEqual([e["type"] for e in self.log()], ["note", "reply", "status"])
        self.assertEqual(self.log()[-1]["status"], "done")
        self.assertEqual(
            self.cli("reply", self.unit_arg, "--to", "m1", "--state", "asked", "--read", "0", stdin="More?")[0], 0
        )
        self.assertEqual(self.log()[-1]["status"], "asked")
        code_, _, err = self.cli("reply", self.unit_arg, "--to", "nope", stdin="x")
        self.assertEqual(code_, 1)
        self.assertIn("no comment or message with id nope", err)
        self.assertEqual(self.cli("reply", self.unit_arg, "--to", "m1", "--state", "accepted", stdin="x")[0], 2)

    def test_status_marks_items_and_accepted_needs_the_users_words_on_stdin(self):
        self.seed({"type": "note", "by": "user", "id": "m1", "text": "q", "to": None})
        self.assertEqual(self.cli("status", self.unit_arg, "working", "m1", "--read", "0")[0], 0)
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
        self.assertEqual(self.cli("status", self.unit_arg, "working", "m2", "--read", "3")[0], 0)
        last = self.log()[before]
        self.assertEqual(
            (last["type"], last["to"], last["status"], last["by"]), ("status", "m2", "working", "coordinator")
        )
        self.assertEqual(self.cli("status", self.unit_arg, "accepted", "c1")[0], 1)  # the user's words are missing
        self.assertEqual(len(self.log()), before + 1)

    def test_status_closes_the_agents_own_message_but_not_a_reply_under_an_item(self):
        self.seed({"type": "note", "by": "user", "id": "m1", "text": "q", "to": None})
        self.assertEqual(self.cli("reply", self.unit_arg, stdin="Which size?")[0], 0)
        self.assertEqual(self.cli("reply", self.unit_arg, "--to", "m1", "--read", "1", stdin="Done.")[0], 0)
        started, under = [e["id"] for e in self.log() if e["type"] == "reply"]
        code_, out, _ = self.cli("status", self.unit_arg, "done", started, "--read", "3")
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

    def test_pending_lists_the_threads_of_the_shared_table_that_are_the_agents_turn(self):
        """`pending` prints each thread that is the agent's turn, with its step as `status`, and the thread under it."""
        for case in TABLE:
            if "items" in case:
                continue  # the fixture page tracks comments and notes, and approvals
            with self.subTest(case["name"]):
                (self.unit_dir / "conversation.jsonl").unlink(missing_ok=True)
                self.seed(*case["log"])
                code_, out, _ = self.cli("pending", self.unit_arg)
                lines = out.splitlines()
                self.assertEqual(code_, 0)
                items = [json.loads(line) for line in lines[:-1]]
                expected = [[t["id"], t["step"]] for t in case["threads"] if t["state"] == "agent"]
                self.assertEqual([[e["id"], e["status"]] for e in items], expected)
                read = len(case["log"]) - 1
                self.assertEqual(lines[-1], f"{len(items)} not done. Pass --read {read} to status and reply.")
                for name, (item, field, value) in EXTRAS.items():
                    if name == case["name"]:
                        got = next(e[field] for e in items if e["id"] == item)
                        if field == "thread":
                            got = [{k: v for k, v in t.items() if k != "at"} for t in got]
                        self.assertEqual(got, value)

    def test_a_status_read_is_a_whole_number_in_the_schema(self):
        conv = page.Conversation(self.unit(), self.spec, self.docs)
        base = {"type": "status", "at": "2026-11-28T10:00:00Z", "by": "coordinator", "to": "m1", "status": "seen"}
        conv.check({**base, "read": 3})
        for bad in ("3", -1, 1.5):
            with self.subTest(read=bad), self.assertRaises(page.EventError):
                conv.check({**base, "read": bad})

    def test_a_report_carries_its_own_done_status_with_its_own_line_as_read_D13(self):
        """A new report is done by the agent and stays in Open until the user's check; an old one, with no status, starts
        closed (D13)."""
        self.seed(
            {"type": "note", "by": "user", "id": "m1", "text": "a", "to": None},
            {"type": "reply", "by": "coordinator", "id": "r0", "text": "old report", "to": None},
        )
        self.assertEqual(self.cli("reply", self.unit_arg, stdin="Built it.")[0], 0)
        report, status = self.log()[2:]
        self.assertEqual(
            (status["type"], status["to"], status["status"], status["read"]), ("status", report["id"], "done", 2)
        )
        shown = {t["id"]: (t["state"], t["closed_by_user"]) for t in page.threads(self.log(), DEFAULT_KINDS)}
        self.assertEqual((shown["r0"], shown[report["id"]]), (("done", True), ("done", False)))

    def test_an_acceptance_the_agent_records_is_not_the_user_writing_in_the_thread(self):
        self.seed({"type": "note", "by": "user", "id": "m1", "text": "a", "to": None})
        self.assertEqual(self.cli("status", self.unit_arg, "accepted", "m1", "--text", stdin="Looks right")[0], 0)
        code_, _, err = self.cli("reply", self.unit_arg, "--to", "m1", "--read", "0", stdin="Thanks.")
        self.assertEqual(code_, 0, err)

    def test_reply_without_to_is_a_report_unless_asked_which_sets_asked_on_its_own_id_S6(self):
        self.assertEqual(self.cli("reply", self.unit_arg, stdin="Built it.")[0], 0)
        self.assertEqual([e["type"] for e in self.log()], ["reply", "status"])
        self.assertEqual(self.cli("reply", self.unit_arg, "--state", "asked", stdin="Which size?")[0], 0)
        question, status = self.log()[2:]
        self.assertEqual((status["type"], status["to"], status["status"]), ("status", question["id"], "asked"))
        states = [(t["state"], t["step"]) for t in page.threads(self.log(), DEFAULT_KINDS)]
        self.assertEqual(states, [("done", "new"), ("you", "new")])

    def test_the_agent_can_reply_to_and_mark_a_thread_it_started(self):
        self.seed(
            {"type": "reply", "by": "coordinator", "id": "r1", "text": "Which?", "to": None},
            {"type": "closed", "by": "worker-2", "id": "x1", "question": "Q4", "status": "answered"},
            {"type": "note", "by": "user", "id": "m1", "text": "this", "to": "r1"},
        )
        self.assertEqual(self.cli("reply", self.unit_arg, "--to", "r1", "--read", "2", stdin="Done.")[0], 0)
        self.assertEqual((self.log()[-1]["to"], self.log()[-1]["status"]), ("r1", "done"))
        self.assertEqual(self.cli("status", self.unit_arg, "done", "x1", "--read", "4")[0], 0)

    def last(self, thread_id):
        return next(t for t in page.threads(self.log(), DEFAULT_KINDS) if t["id"] == thread_id)

    def test_pending_prints_the_read_index_last_S2(self):
        self.seed(
            {"type": "note", "by": "user", "id": "m1", "text": "a", "to": None},
            {"type": "reply", "by": "coordinator", "id": "r1", "text": "ok", "to": None},
            {"type": "note", "by": "user", "id": "m2", "text": "b", "to": None},
        )
        code_, out, _ = self.cli("pending", self.unit_arg)
        self.assertEqual(code_, 0)
        self.assertEqual(out.splitlines()[-1], "2 not done. Pass --read 2 to status and reply.")
        self.assertFalse((self.unit_dir / ".conversation-read").exists())  # no marker: the agent passes what it read

    def test_status_and_reply_write_the_read_they_are_given_S2(self):
        self.seed(
            {"type": "note", "by": "user", "id": "m1", "text": "a", "to": None},
            {"type": "note", "by": "user", "id": "m2", "text": "b", "to": None},
        )
        self.assertEqual(self.cli("status", self.unit_arg, "working", "m1", "m2", "--read", "1")[0], 0)
        self.assertEqual([e.get("read") for e in self.log()[-2:]], [1, 1])
        self.assertEqual(self.cli("reply", self.unit_arg, "--to", "m1", "--read", "3", stdin="Done.")[0], 0)
        self.assertEqual((self.log()[-1]["status"], self.log()[-1]["read"]), ("done", 3))
        self.assertEqual(self.last("m1")["state"], "done")

    def test_status_and_reply_to_without_read_are_refused_and_write_nothing_S2(self):
        self.seed({"type": "note", "by": "user", "id": "m1", "text": "a", "to": None})
        for argv, stdin in (
            (("status", self.unit_arg, "seen", "m1"), ""),
            (("reply", self.unit_arg, "--to", "m1"), "x"),
        ):
            with self.subTest(argv[0]):
                code_, _, err = self.cli(*argv, stdin=stdin)
                self.assertEqual(code_, 1, err)
                self.assertIn("--read", err)
                self.assertIn("pending", err)
                self.assertEqual(len(self.log()), 1)
        # A new subject and the user's acceptance in words need no --read.
        self.assertEqual(self.cli("reply", self.unit_arg, "--state", "asked", stdin="Which size?")[0], 0)
        self.assertEqual(self.cli("reply", self.unit_arg, stdin="Built it.")[0], 0)
        self.assertEqual(self.cli("status", self.unit_arg, "accepted", "m1", "--text", stdin="Fine by me")[0], 0)

    def test_a_read_before_the_users_latest_event_in_a_named_thread_is_refused_and_names_it_S2(self):
        self.seed(
            {"type": "note", "by": "user", "id": "m1", "text": "a", "to": None},
            {"type": "note", "by": "user", "id": "m2", "text": "b", "to": None},
            {"type": "note", "by": "user", "id": "m3", "text": "more", "to": "m1"},
        )
        before = len(self.log())
        for argv, stdin in (
            (("status", self.unit_arg, "seen", "m1", "m2", "--read", "1"), ""),
            (("reply", self.unit_arg, "--to", "m1", "--read", "1"), "Done."),
        ):
            with self.subTest(argv[0]):
                code_, _, err = self.cli(*argv, stdin=stdin)
                self.assertEqual(code_, 1, err)
                self.assertIn("m1", err)
                self.assertNotIn("m2", err)
                self.assertIn("run pending", err)
                self.assertIn("to read them, then send this again with the --read it prints", err)
                self.assertEqual(len(self.log()), before)
        # Only the named threads count: m2 has nothing newer than line 1.
        self.assertEqual(self.cli("status", self.unit_arg, "seen", "m2", "--read", "1")[0], 0)
        self.assertEqual(self.cli("reply", self.unit_arg, "--to", "m1", "--read", "2", stdin="Done.")[0], 0)
        self.assertEqual(self.last("m1")["state"], "done")

    def test_an_edited_comment_and_a_note_under_the_agents_reply_are_writes_in_the_thread_S2(self):
        self.seed(
            {"type": "comment", "by": "user", "id": "c1", "n": 1, "text": "big"},
            {"type": "reply", "by": "coordinator", "id": "r1", "text": "ok", "to": "c1"},
            {"type": "comment", "by": "user", "id": "c1", "n": 1, "text": "bigger"},
        )
        code_, _, err = self.cli("status", self.unit_arg, "done", "c1", "--read", "1")
        self.assertEqual(code_, 1, err)
        self.assertIn("c1", err)
        self.seed({"type": "note", "by": "user", "id": "m1", "text": "and red", "to": "r1"})
        code_, _, err = self.cli("reply", self.unit_arg, "--to", "c1", "--read", "2", stdin="Done.")
        self.assertEqual(code_, 1, err)
        self.assertEqual(self.cli("reply", self.unit_arg, "--to", "c1", "--read", "3", stdin="Done.")[0], 0)

    def test_a_read_past_the_log_or_not_a_whole_number_is_refused(self):
        self.seed({"type": "note", "by": "user", "id": "m1", "text": "a", "to": None})
        code_, _, err = self.cli("status", self.unit_arg, "seen", "m1", "--read", "5")
        self.assertEqual(code_, 1, err)
        self.assertIn("no line 5", err)
        self.assertEqual(self.cli("status", self.unit_arg, "seen", "m1", "--read", "-1")[0], 2)
        self.assertEqual(self.cli("status", self.unit_arg, "seen", "m1", "--read", "x")[0], 2)
        self.assertEqual(len(self.log()), 1)

    def test_status_help_says_it_marks_threads(self):
        code_, out, _ = self.cli("--help")
        self.assertNotIn("mark the user's items", out)

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
