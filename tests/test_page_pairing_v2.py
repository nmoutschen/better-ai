"""The page server's pairing, its routes and `link` (T2 of the page protocol).

Two kinds of check. The ones on `Pairing` and on a server in this process, with a fake driver, are fast and look at
single routes. The ones on `serve` and `link` run the real command with the stub harness (tests/fixtures/stub-harness) and
the stub browser (tests/fixtures/stub-browser, which pairs the way the page does, called in place of webbrowser.open): nothing opens a real
browser, and every unit is a fresh one, with no .server, .server-token, .driver or .driver.log of another run."""

import concurrent.futures
import http.client
import json
import os
import signal
import socket
import stat
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))
from test_page_cli_v2 import BOOT, NOTE, UUID, Unit, alive, better_unit, stub_env, wait_for  # noqa: E402

BROWSER = HERE / "fixtures" / "stub-browser"
# What a served page's `webbrowser.open` is in these tests: the stub browser and nothing else. The environment's BROWSER
# is not enough: when its command fails, `webbrowser` goes on to the next browser it knows, the user's real one.
BROWSER_BOOT = """
import os, subprocess, webbrowser

def stub_open(url, new=0, autoraise=True):
    return subprocess.run([os.environ["STUB_BROWSER"], url], check=False).returncode == 0

webbrowser.open = stub_open
"""
AGENT_FIELDS = {"state", "since", "kind", "text", "mark_age", "approvals", "workers", "blocked", "auto_approved_once"}


def rpc(method, params=None, rid=1):
    return {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}


class Tabs(Unit):
    """A unit, and a way to talk to a server as a tab and as something that is not one."""

    def raw(self, method, path, *, host=None, origin="same", fetch="same-origin", secret=None, body=None, address=None):
        base = (address or self.address()).split("//")[1].rstrip("/")
        headers = {"Host": host or base}
        if origin == "same":
            headers["Origin"] = f"http://{base}"
        elif origin:
            headers["Origin"] = origin
        if fetch:
            headers["Sec-Fetch-Site"] = fetch
        if secret:
            headers["X-Page-Token"] = secret
        if body is not None:
            headers["Content-Type"] = "application/json"
        connection = http.client.HTTPConnection(base, timeout=15)
        connection.request(method, path, json.dumps(body) if body is not None else None, headers)
        reply = connection.getresponse()
        text = reply.read().decode()
        connection.close()
        return reply.status, text

    def call(self, secret, method, params=None, rid=1):
        status, text = self.request("POST", "/rpc", rpc(method, params, rid), secret)
        self.assertEqual(status, 200, text)
        return json.loads(text)

    def log_lines(self):
        path = self.folder / "conversation.jsonl"
        return path.read_text().splitlines() if path.exists() else []


class Browser(Tabs):
    """A real `serve` and `link`, with the stub browser as the user's browser."""

    def setUp(self):
        super().setUp()
        self.out = self.root / "browser.out"
        self.dump = self.root / "stub.dump"

    def env(self, mode="pair", **changes):
        values = {
            "STUB_BROWSER": str(BROWSER),
            "STUB_BROWSER_OUT": str(self.out),
            "STUB_BROWSER_MODE": mode,
            "STUB_DUMP": str(self.dump),
            **changes,
        }
        return stub_env(**values)

    def serve(self, *args, boot=None, **kw):
        return super().serve(*args, boot=BROWSER_BOOT + (boot or ""), **kw)

    def browser_lines(self, kind):
        if not self.out.exists():
            return []
        return [line.split(" ", 1)[1] for line in self.out.read_text().splitlines() if line.startswith(kind + " ")]

    def serve_in_browser(self, env, boot=None, timeout=90):
        """`serve` as a person runs it, with no --no-browser: the server opens the browser itself."""
        script = self.root / "boot.py"
        script.write_text(BROWSER_BOOT + (boot or ""))
        argv = [sys.executable, "-I", "-c", BOOT, str(ROOT / "src"), str(script), "serve", str(self.folder)]
        return subprocess.run(
            argv, cwd=self.root, env=env, input="", capture_output=True, text=True, timeout=timeout, check=False
        )

    def link(self, env=None):
        return self.verb("link", ".show/deck", env=env or self.env())

    def everything_the_unit_holds(self):
        text = ""
        for path in sorted(self.folder.rglob("*")):
            if path.is_file():
                text += path.read_text(errors="replace")
        return text


class PairingTest(unittest.TestCase):
    ORIGIN = "http://127.0.0.1:54321"

    def pairing(self):
        from better_ai.page.approvals import Pairing

        return Pairing(self.ORIGIN)

    def test_a_token_is_exchanged_once(self):  # S7, S83
        pairing = self.pairing()
        token = pairing.issue()
        secret = pairing.exchange(token, self.ORIGIN)
        self.assertTrue(pairing.valid(secret, self.ORIGIN))
        with self.assertRaises(ValueError):
            pairing.exchange(token, self.ORIGIN)
        self.assertTrue(pairing.valid(secret, self.ORIGIN))  # the refused second use pairs nothing and unpairs nothing

    def test_a_token_from_another_origin_or_forged_is_refused(self):  # S83
        pairing = self.pairing()
        token = pairing.issue()
        for origin, given in (
            (self.ORIGIN.replace("54321", "1"), token),
            (self.ORIGIN, "x" * len(token)),
            (self.ORIGIN, ""),
        ):
            with self.assertRaises(ValueError):
                pairing.exchange(given, origin)
        with self.assertRaises(ValueError):
            self.pairing().exchange("anything", self.ORIGIN)  # none issued
        self.assertTrue(pairing.exchange(token, self.ORIGIN))  # still good for the one that holds it

    def test_a_new_token_leaves_the_old_tab_paired_until_the_new_one_pairs(self):  # S84, S85
        pairing = self.pairing()
        old = pairing.exchange(pairing.issue(), self.ORIGIN)
        token = pairing.issue()
        self.assertTrue(pairing.valid(old, self.ORIGIN), "issuing a token must not unpair the old tab")
        new = pairing.exchange(token, self.ORIGIN)
        self.assertFalse(pairing.valid(old, self.ORIGIN))
        self.assertTrue(pairing.valid(new, self.ORIGIN))

    def test_a_revoked_token_pairs_nothing_and_the_old_tab_stays(self):  # S85
        pairing = self.pairing()
        old = pairing.exchange(pairing.issue(), self.ORIGIN)
        token = pairing.issue()
        pairing.revoke()
        with self.assertRaises(ValueError):
            pairing.exchange(token, self.ORIGIN)
        self.assertTrue(pairing.valid(old, self.ORIGIN))

    def test_waiting_for_a_pairing_sees_only_a_later_one(self):  # S68
        pairing = self.pairing()
        pairing.exchange(pairing.issue(), self.ORIGIN)
        before = pairing.generation
        self.assertFalse(pairing.wait_after(before, 0.2))
        token = pairing.issue()
        threading.Timer(0.2, lambda: pairing.exchange(token, self.ORIGIN)).start()
        self.assertTrue(pairing.wait_after(before, 5))


class FakeDriver:
    """What the handlers need of the driver, with an answer that comes when the test says."""

    session = "s-1"
    tag = "t-1"

    def __init__(self):
        self.events, self.stops, self.starts, self.answers = [], 0, 0, []
        self.pending = {}
        self.hold = False
        self.approvals = [{"id": "a1", "options": ["allow_once", "deny"]}]

    def agent(self):
        return {
            "state": "idle",
            "since": "2026-11-28T10:00:00Z",
            "kind": None,
            "text": None,
            "mark_age": 0.1,
            "approvals": self.approvals,
            "workers": [],
            "blocked": [],
            "auto_approved_once": False,
        }

    def snapshot(self):
        return {"state": "idle", "since": 1.0, "age": 0.1, "waiting": False, "open_approvals": len(self.approvals)}

    def answer_approval(self, approval_id, choice, reason=""):
        future = concurrent.futures.Future()
        self.answers.append((approval_id, choice))
        if not self.hold:
            future.set_result(approval_id in {a["id"] for a in self.approvals})
        self.pending[approval_id] = future
        return future

    def enqueue(self, event):
        self.events.append(event)

    def request_stop(self):
        self.stops += 1

    def request_start(self):
        self.starts += 1

    def close(self, *args):
        pass


class InProcess(Tabs):
    """A page server in this process, with a fake driver: single routes, fast."""

    def setUp(self):
        super().setUp()
        from better_ai import page, resources

        unit = better_unit(self.root, self.folder)
        spec = page.spec_of(unit.skill)
        conv = page.Conversation(unit, spec, page.load_docs(unit.skill))
        self.server = page.make_server(unit, spec, conv, resources.build_info())
        self.driven = page.DrivenPage(self.server, unit)
        self.driver = self.driven.driver = FakeDriver()
        self.driven.ready = True
        page.run_http(self.server)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.page = page
        self.base = f"http://127.0.0.1:{self.server.server_port}/"
        self.secret = self.tab()

    def address(self):
        return self.base

    def tab(self):
        pairing = self.driven.pairing
        return pairing.exchange(pairing.issue(), self.driven.origin)

    def post(self, body, secret=None):
        return self.request("POST", "/rpc", body, secret or self.secret, address=self.base)

    def test_the_server_listens_only_on_the_loopback_interface(self):  # S46
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_alive_has_exactly_its_five_fields_and_no_secret_is_needed(self):  # S86
        status, text = self.raw("GET", "/alive", fetch=None, origin=None)
        self.assertEqual(status, 200)
        body = json.loads(text)
        self.assertEqual(set(body), {"unit", "session", "state", "mark_age", "waiting"})
        self.assertEqual(body["waiting"], 1)  # the number of open approvals, as a number
        self.assertNotIn("tool", text)
        self.assertNotIn("arguments", text)

    def test_only_alive_and_pair_are_open_without_the_secret(self):  # S86, S83
        for path in ("/data", "/events", "/old", "/rev", "/agent"):
            self.assertEqual(self.raw("GET", path)[0], 403, path)
        self.assertEqual(self.raw("GET", "/")[0], 200)
        self.assertEqual(self.raw("GET", "/page.js")[0], 200)
        self.assertEqual(self.raw("GET", "/page.css")[0], 200)
        for path in ("/approvals.html", "/approvals.js", "/approvals.css", "/webauthn", "/reconnect", "/listening"):
            self.assertEqual(self.raw("GET", path)[0], 404, path)
            self.assertEqual(self.raw("POST", path, body={})[0], 404, path)

    def test_each_route_refuses_a_call_without_the_secret_or_from_another_origin(self):  # S46, S69
        routes = [("GET", p, None) for p in ("/data", "/events?after=0", "/old", "/rev", "/agent")]
        for method in ("note", "permission_answer", "agent_stop", "agent_start"):
            routes.append(
                ("POST", "/rpc", rpc(method, {"id": "a1", "choice": "deny"} if method == "permission_answer" else NOTE))
            )
        for method, path, body in routes:
            shapes = {
                "no secret": dict(secret=None),
                "forged Origin": dict(secret=self.secret, origin="http://evil.example"),
                "no Origin on a post": dict(secret=self.secret, origin=None) if method == "POST" else None,
                "forged Host": dict(secret=self.secret, host="evil.example"),
                "cross-site": dict(secret=self.secret, fetch="cross-site"),
                "no Fetch Metadata": dict(secret=self.secret, fetch=None),
                "wrong secret": dict(secret="x" * 43),
            }
            for name, kwargs in shapes.items():
                if kwargs is None:
                    continue
                with self.subTest(route=f"{method} {path}", call=name):
                    status, text = self.raw(method, path, body=body, **kwargs)
                    self.assertEqual(status, 403, text)
        self.assertEqual(self.log_lines(), [])
        self.assertEqual(
            (self.driver.events, self.driver.stops, self.driver.starts, self.driver.answers), ([], 0, 0, [])
        )

    def test_the_right_call_is_answered(self):  # S46, S69
        self.call(self.secret, "note", NOTE)  # /events waits for news when the log holds none
        for path in ("/data", "/events?after=0", "/old", "/rev", "/agent"):
            self.assertEqual(self.raw("GET", path, secret=self.secret)[0], 200, path)

    def test_agent_serves_what_the_driver_builds_as_it_is(self):  # S152
        status, text = self.raw("GET", "/agent", secret=self.secret)
        self.assertEqual(json.loads(text), self.driver.agent())
        self.assertEqual(set(json.loads(text)), AGENT_FIELDS)

    def test_a_permission_answer_sent_twice_gives_the_first_result(self):  # S5
        first = self.call(self.secret, "permission_answer", {"id": "a1", "choice": "allow_once"})
        again = self.call(self.secret, "permission_answer", {"id": "a1", "choice": "allow_once"})
        self.assertEqual((first["result"], again["result"]), (True, True))
        self.assertEqual(len(self.driver.answers), 1, "the second send must not reach the driver")

    def test_a_different_choice_for_an_answered_approval_is_an_error(self):  # S5
        self.call(self.secret, "permission_answer", {"id": "a1", "choice": "allow_once"})
        again = self.call(self.secret, "permission_answer", {"id": "a1", "choice": "deny"})
        self.assertEqual(again["error"]["code"], -32602)
        self.assertIn("answered", again["error"]["message"])
        self.assertEqual(len(self.driver.answers), 1)

    def test_an_approval_that_is_no_longer_waiting_is_an_error_not_a_relay(self):  # S81
        answer = self.call(self.secret, "permission_answer", {"id": "gone", "choice": "allow_once"})
        self.assertEqual(answer["error"]["code"], -32602)
        self.assertNotIn("result", answer)

    def test_a_bad_approval_id_or_choice_is_a_json_rpc_error_not_a_500(self):  # S5
        for params in (
            {"id": 5, "choice": "deny"},
            {"id": None, "choice": "deny"},
            {"id": ["a1"], "choice": "deny"},
            {"choice": "deny"},
            {"id": "a1", "choice": 7},
            {"id": "a1"},
        ):
            with self.subTest(params):
                answer = self.call(self.secret, "permission_answer", params)
                self.assertEqual(answer["error"]["code"], -32602)

    def test_a_slow_driver_gives_an_error_and_the_server_goes_on_answering(self):  # S5
        self.driver.hold = True
        with mock.patch.object(self.page, "ANSWER_WAIT", 0.5):
            started = time.monotonic()
            answer = self.call(self.secret, "permission_answer", {"id": "a1", "choice": "allow_once"})
        self.assertLess(time.monotonic() - started, 5)
        self.assertIn("error", answer)
        self.assertIn(answer["error"]["code"], (-32602, -32603))
        again = self.call(self.secret, "permission_answer", {"id": "a1", "choice": "deny"})
        self.assertIn("answered", again["error"]["message"])  # the first choice stands

    def test_a_waiting_answer_does_not_stop_other_requests(self):  # verifier-t1 note: no lock held while waiting
        self.driver.hold = True
        done = []
        with mock.patch.object(self.page, "ANSWER_WAIT", 3):
            thread = threading.Thread(
                target=lambda: done.append(self.call(self.secret, "permission_answer", {"id": "a1", "choice": "deny"}))
            )
            thread.start()
            self.assertTrue(wait_for(lambda: self.driver.answers, 5))
            started = time.monotonic()
            self.assertEqual(self.raw("GET", "/agent", secret=self.secret)[0], 200)
            self.assertEqual(self.call(self.secret, "agent_stop")["result"], True)
            self.assertEqual(self.call(self.secret, "note", NOTE)["result"], "saved")
            self.assertLess(time.monotonic() - started, 2)
            thread.join(10)
        self.assertEqual(len(done), 1)

    def test_a_resent_event_is_saved_once(self):  # S127
        first = self.call(self.secret, "note", NOTE)
        again = self.call(self.secret, "note", NOTE)
        self.assertEqual((first["result"], again["result"]), ("saved", "saved"))
        self.assertEqual(len(self.log_lines()), 1)
        self.assertEqual(len(self.driver.events), 1)

    def test_an_event_edited_and_then_sent_as_before_is_a_new_line(self):  # S127
        a, b = dict(NOTE, text="A"), dict(NOTE, text="B")
        for params in (a, b, a):
            self.assertEqual(self.call(self.secret, "note", params)["result"], "saved")
        self.assertEqual([json.loads(line)["text"] for line in self.log_lines()], ["A", "B", "A"])
        self.call(self.secret, "note", a)  # the last one again, as after a lost reply
        self.assertEqual(len(self.log_lines()), 3)

    def test_a_failure_while_opening_a_tab_is_answered_and_revokes_the_token(self):  # N4
        self.driven.open_tab = mock.Mock(side_effect=RuntimeError("boom"))
        with self.page.link_control(self.driven):
            path = (self.folder / ".page-link").read_text()
            with socket.socket(socket.AF_UNIX) as control:
                control.settimeout(5)
                control.connect(path)
                control.sendall(f"open-tab {self.driven.identity}\n".encode())
                reply = control.makefile("rb").readline(300).decode().strip()
        self.assertRegex(reply, r"^off no-server: \S")
        self.assertFalse(self.driven.pairing.token)

    def test_stop_and_start_twice_are_success(self):  # S128
        for method in ("agent_stop", "agent_stop", "agent_start", "agent_start"):
            self.assertEqual(self.call(self.secret, method)["result"], True, method)

    def test_the_permission_methods_are_never_in_the_log_or_tracked(self):  # S82
        self.call(self.secret, "permission_answer", {"id": "a1", "choice": "allow_once"})
        self.call(self.secret, "agent_stop")
        self.call(self.secret, "agent_start")
        self.assertEqual(self.log_lines(), [])
        self.assertEqual(self.driver.events, [])

    def test_an_unpaired_secret_gets_403_on_every_route(self):  # S84
        old = self.secret
        new = self.tab()
        self.assertNotEqual(old, new)
        for path in ("/data", "/events?after=0", "/agent"):
            self.assertEqual(self.raw("GET", path, secret=old)[0], 403, path)
        for path in ("/data", "/agent"):
            self.assertEqual(self.raw("GET", path, secret=new)[0], 200, path)
        self.assertEqual(self.raw("POST", "/rpc", body=rpc("agent_stop"), secret=old)[0], 403)

    def test_pair_pairs_only_a_valid_unused_token(self):  # S7, S83
        token = self.driven.pairing.issue()
        origin = {"Origin": self.driven.origin}
        bad = self.raw("POST", "/pair", body={"token": "x" * len(token)})
        self.assertEqual(bad[0], 403)
        self.assertEqual(self.raw("POST", "/pair", body={})[0], 403)
        self.assertEqual(self.raw("POST", "/pair", body={"token": 5})[0], 403)
        self.assertEqual(self.raw("POST", "/pair", body={"token": token}, origin="http://evil.example")[0], 403)
        self.assertEqual(self.raw("GET", "/pair")[0], 404)
        self.assertEqual(self.raw("GET", "/agent", secret=self.secret)[0], 200, "no failed pairing may unpair the tab")
        status, text = self.raw("POST", "/pair", body={"token": token})
        self.assertEqual(status, 200, (text, origin))
        secret = json.loads(text)["secret"]
        self.assertEqual(self.raw("POST", "/pair", body={"token": token})[0], 403)  # used
        self.assertEqual(self.raw("GET", "/agent", secret=secret)[0], 200)
        self.assertEqual(self.raw("GET", "/agent", secret=self.secret)[0], 403)

    def test_a_reload_with_the_kept_secret_stays_paired(self):  # S89
        self.assertEqual(self.raw("GET", "/", secret=None)[0], 200)  # the reload loads the shell without the secret
        for _ in range(3):
            self.assertEqual(self.raw("GET", "/agent", secret=self.secret)[0], 200)
            self.assertEqual(self.call(self.secret, "agent_stop")["result"], True)
        source = (ROOT / "src" / "better_ai" / "page" / "page.js").read_text()
        self.assertIn("sessionStorage.setItem('pageToken'", source)
        self.assertNotIn("localStorage", source)


class VerbsKnowThePageAgentTest(Unit):
    def notice_for(self, session):
        from unittest import mock

        from better_ai import cli, page, resources

        unit = better_unit(self.root, self.folder)
        (self.folder / ".driver").write_text("{}")
        found = {"tag": "the-tag", "alive": {"session": "the-session", "state": "idle", "waiting": 0}}
        run = cli.Run(cli.load(resources.build_info()), resources.build_info())
        out = []
        run.out = run.err = out.append
        verb = next(v for v in cli.VERBS if v.name == "check")
        args = type("Args", (), {"_verb": verb, "unit": str(unit.path)})()
        env = {"BETTER_PAGE_SESSION": session} if session else {}
        with (
            mock.patch.object(page, "live_server", return_value=found),
            mock.patch.dict(os.environ, env),
            mock.patch.dict(os.environ, {} if session else {"BETTER_PAGE_SESSION": ""}),
        ):
            page.drive_guard(args, run)
        return out

    def test_the_page_agent_is_known_by_its_tag_or_its_session(self):  # S37, S86
        self.assertTrue(self.notice_for(None))
        self.assertTrue(self.notice_for("another"))
        self.assertEqual(self.notice_for("the-tag"), [])
        self.assertEqual(self.notice_for("the-session"), [])


class LiveServerTest(Unit):
    def test_a_server_pid_that_is_not_a_serve_of_this_unit_is_no_live_server(self):  # N2
        from better_ai import page

        unit = better_unit(self.root, self.folder)
        (self.folder / ".driver").write_text(json.dumps({"version": 1, "server_pid": os.getpid()}))
        (self.folder / ".driver").chmod(0o600)
        answer = {"unit": page.unit_identity(unit), "session": "s", "state": "idle", "mark_age": 0, "waiting": 0}
        with mock.patch.object(page, "server_answer", return_value=answer):
            self.assertEqual(page.live_server(unit), {})
            with mock.patch.object(page, "is_serve_of", return_value=True):
                self.assertTrue(page.live_server(unit))

    def test_the_tag_is_written_by_the_driver_not_by_start_driver(self):  # N1
        import inspect

        from better_ai.page import driver, start_driver

        self.assertNotIn("save_state", inspect.getsource(start_driver))
        self.assertIn('"tag"', inspect.getsource(driver.Driver._checkpoint))


class StaticTest(unittest.TestCase):
    def test_no_webauthn_and_no_separate_approval_surface_in_the_source(self):  # S3, S71, S172
        for path in (ROOT / "src" / "better_ai" / "page").iterdir():
            if path.is_file() and path.suffix in (".py", ".js", ".html", ".css", ".md"):
                text = path.read_text().lower()
                self.assertNotIn("webauthn", text, path.name)
                self.assertNotIn("approvals.html", text, path.name)
                self.assertNotIn("passkey", text, path.name)

    def test_the_unused_approval_gate_is_gone(self):
        from better_ai.page import approvals

        for name in ("ApprovalGate", "Request"):
            self.assertFalse(hasattr(approvals, name), name)

    def test_the_page_never_asks_listening_in_a_driven_session(self):  # S152
        source = (ROOT / "src" / "better_ai" / "page" / "page.js").read_text()
        self.assertIn("if (!pageDriven) (function watch() {\n      pageFetch('/listening')", source)
        self.assertIn("pageFetch('/agent'", source)


class ServedTest(Browser):
    def test_serve_opens_one_tab_prints_no_token_and_says_on_only_after_the_page_paired(self):  # S2, S76, S172
        done = self.serve_in_browser(self.env())
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        lines = done.stdout.splitlines()
        self.assertEqual(len(lines), 2, done.stdout)
        self.assertRegex(lines[0], rf"^driver: on claude {UUID}$")
        self.assertRegex(lines[1], r"^Serving \.show/deck at http://127\.0\.0\.1:\d+/$")
        (url,) = self.browser_lines("url")  # one tab
        (secret,) = self.browser_lines("secret")
        token = url.split("#p=")[1]
        stub = self.dump.read_text()
        for where, text in (
            ("serve stdout", done.stdout),
            ("serve stderr", done.stderr),
            ("the unit's files", self.everything_the_unit_holds()),
            ("the harness's environment and prompts", stub),
        ):
            for name, value in (("token", token), ("secret", secret)):
                self.assertNotIn(value, text, f"{name} in {where}")
        self.assertEqual(sorted(p.name for p in self.folder.glob(".server*")), [".server"])
        self.assertEqual(self.request("GET", "/agent", secret=secret)[0], 200)

    def test_a_browser_that_opens_but_never_loads_the_page_is_driver_off(self):  # S76
        boot = "import better_ai.page as page\npage.START_TIMEOUT = 5\n"
        done = self.serve_in_browser(self.env("none"), boot=boot)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertEqual(done.stdout.strip(), "driver: off timeout: pairing the page in the browser")
        self.assertEqual(len(self.browser_lines("url")), 1)
        self.assertNotIn('"type": "user"', self.dump.read_text() if self.dump.exists() else "", "no turn without a tab")
        self.assertFalse((self.folder / ".server").exists())

    def test_a_launcher_that_fails_is_driver_off_no_browser(self):  # S76, S75
        done = self.serve_in_browser(self.env("fail"))
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertRegex(done.stdout.strip(), r"^driver: off no-browser: \S")

    def test_the_link_socket_is_the_users_and_is_gone_after_exit(self):  # S154
        self.served(env=self.env())
        recorded = Path((self.folder / ".page-link").read_text())
        self.assertRegex(str(recorded), r"^/tmp/better-page-[^/]+/link$")
        self.assertEqual(stat.S_IMODE(recorded.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(recorded.parent.stat().st_mode), 0o700)
        self.assertEqual(recorded.parent.stat().st_uid, os.getuid())
        before = self.request("GET", "/alive")[1]
        for request in (b"hello\n", b"open-tab wrong\n", b"GET / HTTP/1.0\r\n\r\n", b"", b"x" * 5000):
            with self.subTest(request=request[:12]), socket.socket(socket.AF_UNIX) as control:
                control.settimeout(5)
                control.connect(str(recorded))
                control.sendall(request)
                control.shutdown(socket.SHUT_WR)
                reply = control.makefile("rb").readline(200)
                self.assertNotIn(b"p=", reply)
                self.assertFalse(reply.startswith(b"on"), reply)
        self.assertEqual(self.browser_lines("url"), [], "a refused request opens no tab")
        self.assertEqual(json.loads(self.request("GET", "/alive")[1])["unit"], json.loads(before)["unit"])
        pid = self.state()["server_pid"]
        os.kill(pid, signal.SIGTERM)
        self.assertTrue(wait_for(lambda: not alive(pid)))
        self.assertTrue(wait_for(lambda: not recorded.exists() and not recorded.parent.exists()))
        self.assertFalse((self.folder / ".page-link").exists())

    def test_the_tag_is_kept_in_driver_state_not_in_alive(self):  # S86
        self.served(env=self.env())
        self.assertRegex(self.state()["tag"], UUID)
        self.assertNotIn("tag", json.loads(self.request("GET", "/alive")[1]))

    def test_link_with_no_server_says_so(self):  # S68
        done = self.link()
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertRegex(done.stdout.strip(), r"^link: off no-server: \S")
        self.assertIn("serve .show/deck again", done.stdout)
        self.assertEqual(done.stdout.count("\n"), 1)

    def test_link_with_a_stale_record_of_a_server_says_no_server(self):  # S68
        self.served(env=self.env())
        pid = self.state()["server_pid"]
        os.kill(pid, signal.SIGKILL)
        self.assertTrue(wait_for(lambda: not alive(pid)))
        done = self.link()
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertRegex(done.stdout.strip(), r"^link: off no-server: \S")

    def test_link_opens_a_new_tab_unpairs_the_old_one_and_prints_no_token(self):  # S68, S84, S2
        old = self.pair(self.served(env=self.env()))
        done = self.link()
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "link: on\n", ""))
        (url,) = self.browser_lines("url")
        (new,) = self.browser_lines("secret")
        self.assertNotIn(url.split("#p=")[1], done.stdout + done.stderr + self.everything_the_unit_holds())
        self.assertEqual(self.request("GET", "/agent", secret=old)[0], 403)
        self.assertEqual(self.request("GET", "/agent", secret=new)[0], 200)
        self.assertEqual(self.call(new, "agent_stop")["result"], True)
        self.assertEqual(self.request("POST", "/rpc", rpc("agent_stop"), old)[0], 403)

    def test_link_twice_leaves_only_the_last_tab(self):  # S68, S84
        self.served(env=self.env())
        for _ in range(2):
            done = self.link()
            self.assertEqual((done.returncode, done.stdout), (0, "link: on\n"))
        first, second = self.browser_lines("secret")
        self.assertEqual(self.request("GET", "/agent", secret=first)[0], 403)
        self.assertEqual(self.request("GET", "/agent", secret=second)[0], 200)

    def test_a_launcher_that_fails_gives_no_browser_and_the_old_tab_stays(self):  # S85, S68
        old = self.pair(self.served(env=self.env("fail")))
        done = self.link()
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertRegex(done.stdout.strip(), r"^link: off no-browser: \S")
        self.assertEqual(self.request("GET", "/agent", secret=old)[0], 200)
        self.assertEqual(self.call(old, "agent_stop")["result"], True)

    def test_a_tab_that_never_pairs_times_out_keeps_the_old_one_and_cannot_pair_late(self):  # S85, S68, S83
        boot = "import better_ai.page as page\npage.LINK_WAIT = 1\n"
        old = self.pair(self.served(env=self.env("none"), boot=boot))
        done = self.link()
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertRegex(done.stdout.strip(), r"^link: off timeout: \S")
        self.assertEqual(self.request("GET", "/agent", secret=old)[0], 200)
        (url,) = self.browser_lines("url")
        address, token = url.split("#p=")
        status, _ = self.request("POST", "/pair", {"token": token}, address=address)
        self.assertEqual(status, 403, "a token the server gave up on must pair nothing")
        self.assertEqual(self.request("GET", "/agent", secret=old)[0], 200)

    def test_stop_and_start_through_the_stack_twice(self):  # S128
        secret = self.pair(self.served(env=self.env()))
        for method, state in (
            ("agent_stop", "stopped"),
            ("agent_stop", "stopped"),
            ("agent_start", "idle"),
            ("agent_start", "idle"),
        ):
            self.assertEqual(self.call(secret, method)["result"], True)
            self.assertTrue(
                wait_for(
                    lambda state=state: json.loads(self.request("GET", "/agent", secret=secret)[1])["state"] == state,
                    20,
                ),
                (method, state),
            )

    def test_an_allow_with_only_the_session_secret_is_relayed_and_the_log_stays_clean(self):  # S3, S82
        secret = self.pair(self.served(env=self.env(STUB_MODE="ask")))
        self.call(secret, "note", NOTE)

        def approvals():
            return json.loads(self.request("GET", "/agent", secret=secret)[1])["approvals"]

        self.assertTrue(wait_for(approvals, 20))
        (approval,) = approvals()
        self.assertEqual(json.loads(self.request("GET", "/alive")[1])["waiting"], 1)
        answer = self.call(secret, "permission_answer", {"id": approval["id"], "choice": "allow_once"})
        self.assertEqual(answer["result"], True)
        again = self.call(secret, "permission_answer", {"id": approval["id"], "choice": "allow_once"})
        self.assertEqual(again["result"], True)
        self.assertTrue(wait_for(lambda: not approvals(), 20))
        self.call(secret, "agent_stop")
        self.call(secret, "agent_start")
        for line in self.log_lines():
            self.assertNotIn(json.loads(line)["type"], ("permission_answer", "agent_stop", "agent_start"))

    def test_an_answer_after_the_harness_cancelled_the_request_is_not_relayed(self):  # S81
        secret = self.pair(self.served(env=self.env(STUB_MODE="cancel")))
        self.call(secret, "note", NOTE)

        def agent():
            return json.loads(self.request("GET", "/agent", secret=secret)[1])

        self.assertTrue(wait_for(lambda: agent()["approvals"], 20))
        (approval,) = agent()["approvals"]
        self.assertTrue(wait_for(lambda: not agent()["approvals"], 20), "the harness cancelled the request")
        answer = self.call(secret, "permission_answer", {"id": approval["id"], "choice": "allow_once"})
        self.assertEqual(answer["error"]["code"], -32602)
        log = (self.folder / ".driver.log").read_text()
        self.assertNotIn('"answer": "allow_once"', log)

    def test_an_agent_body_has_the_shared_fields(self):  # S152
        secret = self.pair(self.served(env=self.env()))
        body = json.loads(self.request("GET", "/agent", secret=secret)[1])
        self.assertLessEqual(AGENT_FIELDS, set(body))
        self.assertLessEqual(set(body) - AGENT_FIELDS, {"problems"})  # D21: T3 adds the list of unreadable lines


if __name__ == "__main__":
    unittest.main()
