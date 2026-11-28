"""`serve` and the verbs of a driven page: the one-line answer, the detached server, the notice a chat agent gets.

Every test serves a unit with the stub harness of tests/fixtures/stub-harness, as a real process (serve forks), and
ends what it left in `tearDown`. Nothing here opens a browser: `--no-browser` is honoured with the stub's marker.

Note for T2: the tests of `serve --link` (a new tab for a running server) went with test_page_driven_serve.py, whose
flow no longer exists; they are T2's to write again against the one-tab pairing."""

import contextlib
import http.client
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))
import better  # noqa: E402

STUB = HERE / "fixtures" / "stub-harness"
SHOW = {
    "type": "slides",
    "title": "The answer is yes.",
    "question": "Why?",
    "panels": [{"headline": "The slide states one clear point.", "source": "test", "kind": "text", "body": ["One."]}],
}
NOTE = {"id": "m-x", "text": "hi", "to": None, "on": {"slide": 1, "part": None}}
UUID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
BOOT = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv.pop(1))
exec(Path(sys.argv.pop(1)).read_text())
from better_ai._entry import main
sys.exit(main())
"""


def stub_env(**changes):
    return better.stub_env("show-better", BETTER_AI_CUTOFF=better.TEST_CUTOFF, **changes)


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    done = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True, check=False)
    return bool(done.stdout.strip()) and not done.stdout.strip().startswith("Z")


def wait_for(condition, seconds=10):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.05)
    return condition()


def first_turn_ended(unit):
    """Whether the unit's .driver.log holds a turn record with its end."""
    try:
        lines = (Path(unit) / ".driver.log").read_text().splitlines()
    except OSError:
        return False
    for line in lines:
        with contextlib.suppress(ValueError):
            record = json.loads(line)
            if isinstance(record, dict) and record.get("type") == "turn" and "end" in record:
                return True
    return False


class Unit(unittest.TestCase):
    """A repository with one show-better unit, and the servers a test starts."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(os.path.realpath(tmp.name))
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
        subprocess.run([*git, "init", "-q", "-b", "main"], cwd=self.root, check=True)
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "x"], cwd=self.root, check=True)
        done = better.call("show-better", "create", ".show/deck", "--by", "t", stdin=json.dumps(SHOW), cwd=self.root)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.folder = self.root / ".show" / "deck"
        self.addCleanup(self.end_everything)

    # ---------- running

    def serve(self, *args, env=None, stdin="", boot=None, unit=None, timeout=60):
        """`serve` as a caller runs it: the finished process, with its stdout and stderr."""
        argv = better.command("serve", str(unit or self.folder), "--no-browser", *args)
        if boot:
            script = self.root / "boot.py"
            script.write_text(boot)
            argv = [
                sys.executable,
                "-I",
                "-c",
                BOOT,
                str(ROOT / "src"),
                str(script),
                "serve",
                str(unit or self.folder),
                "--no-browser",
                *args,
            ]
        return subprocess.run(
            argv,
            cwd=self.root,
            env=env if env is not None else stub_env(),
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def verb(self, *args, stdin="", env=None):
        return subprocess.run(
            better.command(*args),
            cwd=self.root,
            env=env if env is not None else stub_env(),
            input=stdin,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def state(self):
        path = self.folder / ".driver"
        return json.loads(path.read_text()) if path.exists() else {}

    def end_everything(self):
        """End the servers a test started: SIGTERM first, so a server removes its link socket, then SIGKILL."""
        state = self.state()
        pids = [state.get("server_pid"), state.get("child_pid")]
        pids = [pid for pid in pids if type(pid) is int and pid > 1 and pid != os.getpid()]
        if type(state.get("server_pid")) is int and state["server_pid"] in pids:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(state["server_pid"], signal.SIGTERM)
            wait_for(lambda: not alive(state["server_pid"]), 5)
        for pid in pids:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                (os.killpg if pid == state.get("child_pid") else os.kill)(pid, signal.SIGKILL)

    def served(self, *args, **kw):
        done = self.serve(*args, **kw)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done

    # ---------- talking to a server

    def address(self):
        return (self.folder / ".server").read_text().strip()

    def request(self, method, path, body=None, secret=None, address=None):
        base = address or self.address()
        host = base.split("//")[1].rstrip("/")
        headers = {"Host": host, "Origin": f"http://{host}", "Sec-Fetch-Site": "same-origin"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if secret:
            headers["X-Page-Token"] = secret
        connection = http.client.HTTPConnection(host, timeout=10)
        connection.request(method, path, json.dumps(body) if body is not None else None, headers)
        reply = connection.getresponse()
        data = reply.read().decode()
        connection.close()
        return reply.status, data

    def pair(self, done):
        """Pair a tab with the address `serve` printed, as the page does; the secret it gets."""
        link = re.search(r"at (http://\S+)", done.stdout).group(1)
        address, token = link.split("#p=")
        status, data = self.request("POST", "/pair", {"token": token}, address=address)
        self.assertEqual(status, 200, data)
        return json.loads(data)["secret"]

    def drive_kinds(self, done):
        return [line for line in done.stdout.splitlines() if line.startswith("driver:")]


class NoBrowserTest(Unit):
    def test_the_suite_cannot_open_a_browser(self):
        import webbrowser

        with self.assertRaises(AssertionError):
            webbrowser.open("http://127.0.0.1:1/")

    def test_serve_called_from_a_program_serves_here_and_opens_no_browser(self):  # no fork of the test runner
        pid = os.getpid()
        args = ["serve", str(self.folder), "--once"]
        env = {k: v for k, v in stub_env().items()}
        result = {}

        def serve():
            import contextlib
            import io
            from unittest import mock

            from better_ai import cli

            text = io.StringIO()
            with mock.patch.dict(os.environ, env), contextlib.redirect_stdout(text):
                result["code"] = cli.main(args, stdin=io.StringIO(""))
            result["out"] = text.getvalue()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        self.assertTrue(wait_for(lambda: (self.folder / ".server").exists(), 20))
        self.assertEqual(os.getpid(), pid)
        status, _ = self.request("GET", "/")
        self.assertEqual(status, 200)
        thread.join(20)
        self.assertEqual(result["code"], 0)
        self.assertRegex(result["out"], r"^driver: on claude ")


class StartTest(Unit):
    def test_first_line_names_the_session_then_the_address(self):  # S25, S6, S137
        done = self.served()
        lines = done.stdout.splitlines()
        self.assertRegex(lines[0], rf"^driver: on claude {UUID}$")
        self.assertRegex(lines[1], r"^Serving \.show/deck at http://127\.0\.0\.1:\d+/#p=\S+$")
        self.assertEqual(len(lines), 2)
        self.assertFalse((self.folder / ".server-token").exists())
        self.assertEqual(self.drive_kinds(done), lines[:1])

    def test_a_comment_prints_nothing_and_writes_no_token_file(self):  # S6
        secret = self.pair(self.served())
        status, data = self.request(
            "POST", "/rpc", {"jsonrpc": "2.0", "id": 1, "method": "note", "params": NOTE}, secret
        )
        self.assertEqual((status, json.loads(data)["result"]), (200, "saved"))
        self.assertTrue(wait_for(lambda: "m-x" in (self.folder / "conversation.jsonl").read_text()))
        self.assertEqual(sorted(p.name for p in self.folder.glob(".server*")), [".server"])
        log = (self.folder / ".driver.log").read_text()
        self.assertNotIn('"type": "note"', log)

    def test_unit_gitignore_lists_the_driver_files(self):  # S143, N4
        self.served()
        self.assertEqual(
            (self.folder / ".gitignore").read_text().splitlines()[-5:],
            [".driver", ".driver.log", ".page-link", ".page-delivery", ".page-serve-lock"],
        )
        listed = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"], cwd=self.root, capture_output=True, text=True
        ).stdout
        self.assertNotIn(".driver", listed)
        self.assertNotIn(".page-", listed)

    def test_gitignore_that_lists_them_is_left_alone(self):  # S143
        text = "x\n.driver\n.driver.log\n.page-link\n.page-delivery\n.page-serve-lock\n"
        (self.folder / ".gitignore").write_text(text)
        self.served()
        self.assertEqual((self.folder / ".gitignore").read_text(), text)

    def test_serve_returns_and_the_server_goes_on_in_its_own_session(self):  # S91
        started = time.monotonic()
        self.served(stdin="we agreed on the second slide")
        self.assertLess(time.monotonic() - started, 25)
        pid = self.state()["server_pid"]
        self.assertTrue(alive(pid))
        self.assertNotEqual(os.getsid(pid), os.getsid(0))
        self.assertEqual(os.getpgid(pid), pid)
        status, data = self.request("GET", "/alive")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(data)["state"], "idle")

    def test_hand_off_note_is_read_to_end_of_input_within_two_seconds(self):  # S91
        process = subprocess.Popen(
            better.command("serve", str(self.folder), "--no-browser"),
            cwd=self.root,
            env=stub_env(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        process.stdin.write("note")  # stdin stays open: serve gives up on it after two seconds
        process.stdin.flush()
        started = time.monotonic()
        first = process.stdout.readline()
        self.assertGreaterEqual(time.monotonic() - started, 1.5)
        self.assertRegex(first, r"^driver: on ")
        process.stdin.close()
        out, err = process.communicate(timeout=30)
        self.assertEqual(process.returncode, 0, out + err)

    def test_the_server_writes_its_run_to_the_driver_state(self):  # S29, S150
        self.served()
        state = self.state()
        self.assertEqual(state["harness"], "claude")
        self.assertIsInstance(state["server_pid"], int)
        self.assertIsInstance(state["server_started"], str)
        self.assertEqual(state["child_argv"][0], str(STUB / "claude"))
        self.assertTrue(alive(state["child_pid"]))
        self.assertEqual(os.getpgid(state["child_pid"]), state["child_pid"])

    def test_no_file_is_written_in_a_harness_config_directory(self):  # S35, S36
        home = self.root / "home"
        (home / ".claude").mkdir(parents=True)
        (home / ".claude" / "settings.json").write_text("{}")
        (home / ".config" / "opencode").mkdir(parents=True)
        before = sorted((p.relative_to(home), p.stat().st_mtime_ns) for p in home.rglob("*"))
        self.served(env=stub_env(HOME=str(home)))
        state = self.state()
        os.kill(state["server_pid"], signal.SIGTERM)
        self.assertTrue(wait_for(lambda: not alive(state["server_pid"]) and not alive(state["child_pid"])))
        self.assertEqual(before, sorted((p.relative_to(home), p.stat().st_mtime_ns) for p in home.rglob("*")))

    def test_nothing_runs_after_the_server_ends(self):  # S36
        self.served()
        state = self.state()
        os.kill(state["server_pid"], signal.SIGTERM)
        self.assertTrue(wait_for(lambda: not alive(state["server_pid"])))
        self.assertTrue(wait_for(lambda: not alive(state["child_pid"])))
        self.assertFalse((self.folder / ".server").exists())
        ps = subprocess.run(["ps", "-ax", "-o", "args="], capture_output=True, text=True).stdout
        self.assertNotIn(f"serve {self.folder}", ps)

    def test_once_serves_one_request_and_exits(self):
        self.served("--once")
        status, _ = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertTrue(wait_for(lambda: not (self.folder / ".server").exists()))


class OffTest(Unit):
    def off(self, done, kind):
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        lines = self.drive_kinds(done)
        self.assertEqual(len(lines), 1, done.stdout)
        self.assertRegex(lines[0], rf"^driver: off {kind}: \S")
        self.assertEqual(done.stdout.strip(), lines[0])
        self.assertFalse((self.folder / ".server").exists())
        pid = self.state().get("child_pid")
        self.assertFalse(pid and alive(pid), "a harness process is left")
        return lines[0]

    def test_no_harness(self):  # S25, S26, S75
        done = self.serve(env=stub_env(CLAUDECODE=None))
        self.off(done, "no-harness")

    def test_not_installed_names_the_harness(self):  # S147
        done = self.serve(env=stub_env(PATH=""))
        self.assertEqual(self.off(done, "not-installed"), "driver: off not-installed: Claude Code CLI not found on PATH")

    def test_login(self):  # S75, N6
        line = self.off(self.serve(env=stub_env(STUB_MODE="login")), "login")
        self.assertEqual(line, "driver: off login: log in to Claude Code in a terminal, then run serve again")

    def test_version_too_old(self):  # S75
        self.off(self.serve(env=stub_env(STUB_MODE="old")), "version")

    def test_a_hanging_harness_times_out_and_leaves_no_process(self):  # S63, S26
        boot = "import better_ai.page as page\npage.START_TIMEOUT = 3\n"
        started = time.monotonic()
        done = self.serve(env=stub_env(STUB_MODE="hang"), boot=boot)
        self.assertLess(time.monotonic() - started, 20)
        self.assertRegex(self.off(done, "timeout"), r"timeout: starting the agent's session$")

    def test_newer_state_file_is_not_overwritten(self):  # S123
        path = self.folder / ".driver"
        path.write_text(json.dumps({"version": 2, "future": True}))
        path.chmod(0o600)
        done = self.serve()
        self.off(done, "state-version")
        self.assertEqual(json.loads(path.read_text()), {"version": 2, "future": True})

    def test_a_harness_without_approvals(self):  # S146
        boot = (
            "import dataclasses\nfrom better_ai.page import adapters\nreal = adapters.candidate\n"
            "adapters.candidate = lambda *a, **k: dataclasses.replace(real(*a, **k), codec_factory=None)\n"
        )
        self.off(self.serve(boot=boot), "no-approvals")

    def test_a_page_session_never_serves(self):  # S142
        done = self.serve(env=stub_env(BETTER_PAGE_SESSION="s"))
        self.assertEqual(done.returncode, 1)
        self.assertEqual(done.stdout.strip(), "driver: off refused: a page session never serves")

    def test_no_browser_needs_the_stub_marker_and_is_not_in_help(self):  # S137
        done = self.serve(env=stub_env(BETTER_AI_STUB_HARNESS=None))
        self.assertEqual(done.returncode, 1)
        self.assertRegex(done.stdout, r"^driver: off refused: ")
        self.assertFalse((self.folder / ".server").exists())
        helped = self.verb("serve", "--help").stdout
        self.assertNotIn("no-browser", helped)

    def test_a_note_is_ignored_when_the_driver_is_off(self):  # S141
        self.off(self.serve(env=stub_env(STUB_MODE="login"), stdin="what we agreed"), "login")
        self.assertNotIn("what we agreed", json.dumps(self.state()))
        self.assertFalse(self.state().get("note"))

    def test_each_exit_prints_one_driver_line(self):  # S75
        for changes in ({"CLAUDECODE": None}, {"PATH": ""}, {"STUB_MODE": "old"}, {"BETTER_PAGE_SESSION": "s"}):
            with self.subTest(changes):
                done = self.serve(env=stub_env(**changes))
                self.assertEqual(len(self.drive_kinds(done)), 1, done.stdout)


# The kinds of S75, and every other kind a harness start can fail with (the adapters' failures and the driver's).
S75_KINDS = (
    "no-harness",
    "login",
    "not-installed",
    "version",
    "state-version",
    "no-approvals",
    "no-browser",
    "crashed",
    "driver",
    "refused",
    "timeout",
)
START_KINDS = (*S75_KINDS, "limit", "protocol", "unsafe-mode", "missing-session", "something-new")


class OffTextTest(unittest.TestCase):
    def test_no_driver_off_line_repeats_its_kind_as_its_text(self):  # S25, S33, S75, S146
        from better_ai import page

        for kind in START_KINDS:
            for text in ("", kind):  # a StartError without text reads as its kind
                with self.subTest(kind=kind, text=text):
                    line = page.Off(kind, text).line()
                    match = re.fullmatch(r"driver: off ([a-z-]+): (\S.*\S)", line)
                    self.assertIsNotNone(match, line)
                    self.assertIn(match.group(1), S75_KINDS)
                    self.assertNotIn(match.group(2), START_KINDS, line)
                    self.assertGreater(len(match.group(2).split()), 3, line)

    def test_unsafe_mode_is_no_approvals_not_crashed(self):  # S75
        from better_ai import page

        self.assertRegex(page.Off("unsafe-mode", "").line(), r"^driver: off no-approvals: ")
        self.assertRegex(page.Off("unsafe-mode", "Fix the setting.").line(), r"^driver: off no-approvals: Fix the setting\.$")

    def test_a_given_text_is_kept(self):
        from better_ai import page

        self.assertEqual(page.Off("version", "found 1.0, need 2.0").line(), "driver: off version: found 1.0, need 2.0")


class StartFailureTest(Unit):
    def failed_start(self, kind):
        boot = (
            "from better_ai.page import driver\n\n"
            "def fail(self, deadline):\n    raise driver.StartError(%r)\n\n"
            "driver.Driver._open = fail\n" % kind
        )
        done = self.serve(boot=boot)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        lines = self.drive_kinds(done)
        self.assertEqual(len(lines), 1, done.stdout)
        return lines[0]

    def test_a_start_failure_without_text_names_the_problem_and_the_action(self):  # S25, S33, S146
        for kind, shown in (("version", "version"), ("no-approvals", "no-approvals"), ("unsafe-mode", "no-approvals")):
            with self.subTest(kind):
                line = self.failed_start(kind)
                self.assertTrue(line.startswith(f"driver: off {shown}: "), line)
                self.assertNotEqual(line, f"driver: off {shown}: {kind}")


class RunningServerTest(Unit):
    def test_a_second_serve_says_already_and_exits_3(self):  # S28
        first = self.served()
        session = re.match(rf"driver: on claude ({UUID})", first.stdout).group(1)
        second = self.serve()
        self.assertEqual(second.returncode, 3, second.stdout + second.stderr)
        self.assertEqual(second.stdout.strip(), f"driver: on claude {session} already")

    def test_a_server_that_does_not_answer_is_ended(self):  # S108
        self.served()
        old = self.state()["server_pid"]
        os.kill(old, signal.SIGSTOP)
        done = self.served()
        self.assertTrue(wait_for(lambda: not alive(old)))
        self.assertRegex(done.stdout, r"^driver: on claude ")
        self.assertNotEqual(self.state()["server_pid"], old)

    def test_a_pid_that_is_not_a_serve_of_this_unit_is_not_ended(self):  # S108
        other = subprocess.Popen(["sleep", "60"])
        self.addCleanup(other.kill)
        (self.folder / ".driver").write_text(json.dumps({"version": 1, "server_pid": other.pid}))
        (self.folder / ".driver").chmod(0o600)
        (self.folder / ".server").write_text("http://127.0.0.1:9/")
        self.served()
        self.assertIsNone(other.poll())

    def test_a_late_mark_is_waited_for(self):  # S109
        from better_ai import page

        class Late(BaseHTTPRequestHandler):
            def do_GET(self):
                body = json.dumps(
                    {"unit": page.unit_identity(unit), "session": "s", "state": "idle", "mark_age": 5, "waiting": 0}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Late)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        unit = better_unit(self.root, self.folder)
        (self.folder / ".server").write_text(f"http://127.0.0.1:{server.server_address[1]}/")
        threading.Timer(1.5, server.shutdown).start()
        started = time.monotonic()
        page.settle_old_server(unit, {"server_pid": os.getpid()})
        waited = time.monotonic() - started
        self.assertGreaterEqual(waited, 1.4)
        self.assertLess(waited, 9)

    def test_an_orphaned_harness_is_ended_by_the_next_serve(self):  # S29, S151
        self.served(env=stub_env(STUB_MODE="linger"))
        state = self.state()
        os.kill(state["server_pid"], signal.SIGKILL)
        self.assertTrue(wait_for(lambda: not alive(state["server_pid"])))
        child = state["child_pid"]
        self.assertTrue(wait_for(lambda: alive(child)))  # the stub ignores the closed pipe
        (self.folder / ".server").unlink()
        self.served()
        self.assertTrue(wait_for(lambda: not alive(child)))
        self.assertNotEqual(self.state()["child_pid"], child)

    def test_the_orphan_is_ended_only_if_its_command_is_the_recorded_one(self):  # S110
        other = subprocess.Popen(["sleep", "60"], start_new_session=True)
        self.addCleanup(lambda: os.killpg(other.pid, signal.SIGKILL))
        (self.folder / ".driver").write_text(
            json.dumps({"version": 1, "child_pid": other.pid, "child_argv": [str(STUB / "claude"), "-p"]})
        )
        (self.folder / ".driver").chmod(0o600)
        self.served()
        self.assertIsNone(other.poll())

    def test_a_server_killed_leaves_no_address_but_a_newer_one_stays(self):  # S29
        self.served()
        old = self.state()["server_pid"]
        os.kill(old, signal.SIGTERM)
        self.assertTrue(wait_for(lambda: not (self.folder / ".server").exists()))
        self.served()
        newer = (self.folder / ".server").read_text()
        self.assertTrue(newer.startswith("http://127.0.0.1:"))


def better_unit(root, folder):
    from better_ai import cli, paths, resources

    os.environ["BETTER_AI_SKILL"] = "show-better"
    info = resources.build_info()
    skill = cli.load(info)
    return paths.resolve_unit(str(folder), skill)


class DriverErrorTest(Unit):
    BOOT = "from better_ai.page import driver\n\ndef boom(self, *args):\n    raise RuntimeError('boom')\n\ndriver.Driver._open = boom\n"

    def test_the_same_driver_error_that_ended_two_serves_refuses_the_third(self):  # S106, S107
        first = self.serve(boot=self.BOOT)
        self.assertEqual(first.returncode, 1, first.stdout)
        self.assertRegex(first.stdout, r"^driver: off driver: boom; see \S+\.driver\.log\n$")
        self.assertNotIn("the last session ended", first.stderr)
        second = self.serve(boot=self.BOOT)
        self.assertRegex(second.stderr, r"the last session ended at \d\d:\d\d: .*boom")
        third = self.serve(boot=self.BOOT)
        self.assertEqual(third.returncode, 1)
        self.assertRegex(
            third.stdout,
            r"^driver: off driver: the same error came back: .*boom; see \S+; this is a better-ai problem\n$",
        )

    def test_a_changed_build_is_not_refused(self):  # S106
        for _ in range(2):
            self.serve(boot=self.BOOT)
        self.assertEqual(self.state()["ended"]["repeats"], 1)
        self.assertEqual(self.serve().returncode, 1)  # the same program: refused
        update = json.loads((self.folder / ".driver").read_text())
        update["ended"]["build"] = "an older build"
        (self.folder / ".driver").write_text(json.dumps(update))
        self.served()


class ServerErrorTest(Unit):
    def test_a_handler_error_after_detach_is_logged_once_per_window(self):  # S92
        boot = (
            "import better_ai.page as page\n"
            "def broken(self):\n    raise RuntimeError('handler broke')\n"
            "page.Handler.old_format_count = broken\n"
        )
        secret = self.pair(self.served(boot=boot))
        for _ in range(3):
            self.request("GET", "/old", secret=secret)
        self.assertTrue(wait_for(lambda: "server_error" in (self.folder / ".driver.log").read_text()))
        lines = [json.loads(x) for x in (self.folder / ".driver.log").read_text().splitlines() if x.startswith("{")]
        errors = [x for x in lines if x.get("type") == "server_error"]
        self.assertEqual(len(errors), 1)
        self.assertIn("handler broke", errors[0]["text"])


class VerbNoticeTest(Unit):
    def setUp(self):
        super().setUp()
        self.done = self.served()
        self.session = re.match(rf"driver: on claude ({UUID})", self.done.stdout).group(1)
        self.notice = (
            f"this page has its own agent (session {self.session}); tell the user to use the page, "
            f"or run `link .show/deck` to reopen it; do not work on this unit"
        )

    def test_a_chat_agent_gets_the_notice_on_stdout_for_a_read(self):  # S37
        done = self.verb("check", ".show/deck")
        self.assertIn(self.notice, done.stdout)
        self.assertNotIn("its own agent", done.stderr)

    def test_pending_prints_it_on_stderr_and_its_output_still_parses(self):  # S37
        done = self.verb("pending", ".show/deck")
        self.assertEqual(done.returncode, 0)
        self.assertIn(self.notice, done.stderr)
        self.assertEqual(done.stdout.strip(), "0 not done.")

    def test_the_notice_names_the_agents_state(self):  # S122
        done = self.verb("pending", ".show/deck")
        self.assertRegex(done.stderr, r"this page's agent is idle")

    def test_the_page_agent_gets_no_notice(self):  # S37
        done = self.verb("pending", ".show/deck", env=stub_env(BETTER_PAGE_SESSION=self.session))
        self.assertNotIn("its own agent", done.stdout + done.stderr)

    def test_a_chat_agents_writes_exit_4(self):  # S80
        for args, stdin in (
            (("reply", ".show/deck"), "hello"),
            (("status", ".show/deck", "seen", "m-x"), ""),
            (("set", ".show/deck", "x"), "{}"),
            (("add", ".show/deck", "x"), "{}"),
        ):
            with self.subTest(args):
                done = self.verb(*args, stdin=stdin)
                self.assertEqual(done.returncode, 4, done.stdout + done.stderr)
                self.assertIn(self.notice, done.stderr)
        self.assertNotIn(
            "hello",
            (self.folder / "conversation.jsonl").read_text() if (self.folder / "conversation.jsonl").exists() else "",
        )

    def test_after_the_server_ends_the_same_reply_succeeds_without_a_notice(self):  # S37, S80
        os.kill(self.state()["server_pid"], signal.SIGTERM)
        self.assertTrue(wait_for(lambda: not (self.folder / ".server").exists()))
        done = self.verb("reply", ".show/deck", stdin="hello")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("its own agent", done.stdout + done.stderr)

    def test_the_page_agent_cannot_record_an_acceptance(self):  # S79
        env = stub_env(BETTER_PAGE_SESSION=self.session)
        for args in (
            ("status", ".show/deck", "accepted", "m-x"),
            ("status", ".show/deck", "accepted", "--text", "m-x"),
        ):
            with self.subTest(args):
                done = self.verb(*args, stdin="yes", env=env)
                self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
                self.assertIn("cannot record an acceptance", done.stderr)


def session_in_log(log: Path) -> str:
    """The BETTER_PAGE_SESSION the last harness process started with, from the stub's log."""
    return log.read_text().splitlines()[-1].split()[1]


class PageAgentTest(Unit):
    def test_the_page_agent_may_write_after_a_resume(self):  # S80, round 1 B1
        log = self.root / "stub.log"
        env = stub_env(STUB_LOG=str(log))
        self.served(env=env)
        os.kill(self.state()["server_pid"], signal.SIGTERM)
        self.assertTrue(wait_for(lambda: not (self.folder / ".server").exists()))
        self.served(env=env)
        tag = session_in_log(log)
        done = self.verb("reply", ".show/deck", stdin="from the page agent", env=stub_env(BETTER_PAGE_SESSION=tag))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("its own agent", done.stdout + done.stderr)
        chat = self.verb("reply", ".show/deck", stdin="from the chat")
        self.assertEqual(chat.returncode, 4)


class SpellingsTest(Unit):
    """One unit has many spellings; each is the same unit to the notice, the refusal and the old-server check."""

    def spellings(self):
        if hasattr(self, "forms"):
            return self.forms
        link = self.root.parent / f"link-{self.root.name}"
        link.symlink_to(self.root)
        self.addCleanup(link.unlink)
        sub = self.root / "sub"
        sub.mkdir()
        self.forms = [
            (".show/deck/", self.root),
            ("./.show/deck", self.root),
            (str(self.folder), self.root),
            ("../.show/deck", sub),
            (str(link / ".show" / "deck"), self.root),
        ]
        return self.forms

    def run_in(self, cwd, *args, stdin=""):
        return subprocess.run(
            better.command(*args), cwd=cwd, env=stub_env(), input=stdin, capture_output=True, text=True, timeout=60
        )

    def serve_as(self, spelling, cwd):
        return subprocess.run(
            better.command("serve", spelling, "--no-browser"),
            cwd=cwd,
            env=stub_env(),
            input="",
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_a_chat_agent_is_refused_whatever_the_spelling_the_server_was_started_with(self):  # S37, S80
        for spelling, cwd in self.spellings():
            with self.subTest(spelling):
                done = self.serve_as(spelling, cwd)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                for other, other_cwd in self.spellings():
                    chat = self.run_in(other_cwd, "reply", other, stdin="hi")
                    self.assertEqual(chat.returncode, 4, f"{other}: {chat.stdout}{chat.stderr}")
                    self.assertIn("its own agent", chat.stderr)
                self.end_everything()
                (self.folder / ".server").unlink(missing_ok=True)

    def test_a_second_serve_in_any_spelling_finds_the_server(self):  # S28
        self.assertEqual(self.serve_as(".show/deck/", self.root).returncode, 0)
        for spelling, cwd in self.spellings():
            with self.subTest(spelling):
                done = self.serve_as(spelling, cwd)
                self.assertEqual(done.returncode, 3, done.stdout + done.stderr)

    def test_a_stopped_server_served_as_another_spelling_is_ended(self):  # S108
        for spelling, cwd in self.spellings():
            with self.subTest(spelling):
                self.assertEqual(self.serve_as(".show/deck/", self.root).returncode, 0)
                old = self.state()["server_pid"]
                os.kill(old, signal.SIGSTOP)
                done = self.serve_as(spelling, cwd)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertTrue(wait_for(lambda pid=old: not alive(pid)))
                self.end_everything()
                (self.folder / ".server").unlink(missing_ok=True)


class SpacedPathTest(Unit):
    """A unit whose path holds a space is the same unit to the old-server check (round 2 F2)."""

    def test_the_old_server_is_known_by_its_pid_and_start_time_not_its_command_line(self):  # S108, D22
        from types import SimpleNamespace
        from unittest import mock

        from better_ai import page

        unit = SimpleNamespace(path=Path('/tmp/ lead/"q" x/.show/deck'))
        recorded = "Sat Nov 28 12:00:00 2026"
        cases = {
            (recorded, recorded): True,
            (recorded, "Sat Nov 28 12:00:01 2026"): False,  # the pid was reused by another process
            (recorded, None): False,  # nothing runs at that pid
            (None, recorded): False,  # no start time recorded
        }
        for (stored, running), expected in cases.items():
            with (
                self.subTest(stored=stored, running=running),
                mock.patch.object(page, "current_state", return_value={"server_pid": 4242, "server_started": stored}),
                mock.patch.object(page, "process_started", return_value=running, create=True),
                mock.patch.object(page, "command_of", side_effect=AssertionError("no command line parsing")),
            ):
                self.assertIs(page.is_serve_of(4242, unit), expected)
        own = {"server_pid": os.getpid(), "server_started": recorded}
        with (
            mock.patch.object(page, "current_state", return_value=own),
            mock.patch.object(page, "process_started", return_value=recorded, create=True),
        ):
            self.assertIs(page.is_serve_of(os.getpid(), unit), False, "a serve never takes itself for the old server")

    def stopped_server_is_ended(self, name, spellings):
        spaced = self.root / name
        spaced.mkdir()
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
        subprocess.run([*git, "init", "-q", "-b", "main"], cwd=spaced, check=True)
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "x"], cwd=spaced, check=True)
        done = better.call("show-better", "create", ".show/deck", "--by", "t", stdin=json.dumps(SHOW), cwd=spaced)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.folder = spaced / ".show" / "deck"
        for spelling in spellings:
            with self.subTest(spelling):
                self.served()
                old = self.state()["server_pid"]
                os.kill(old, signal.SIGSTOP)
                # A shell runs the serve, so the quoted spelling is the shell's quoting, as a user would type it.
                done = subprocess.run(
                    " ".join([*map(shlex.quote, better.command("serve")), spelling, "--no-browser"]),
                    shell=True,
                    cwd=self.root,
                    env=stub_env(),
                    input="",
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertTrue(wait_for(lambda pid=old: not alive(pid)))
                self.end_everything()
                (self.folder / ".server").unlink(missing_ok=True)

    def test_a_stopped_server_of_a_unit_with_a_leading_space_is_ended(self):  # S108, round 3 B2
        self.stopped_server_is_ended(" lead decks", ("' lead decks/.show/deck'", '" lead decks/.show/deck/"'))

    def test_a_stopped_server_of_a_unit_with_a_space_is_ended(self):  # S108, round 2 F2
        spaced = self.root / "my decks"
        spaced.mkdir()
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
        subprocess.run([*git, "init", "-q", "-b", "main"], cwd=spaced, check=True)
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "x"], cwd=spaced, check=True)
        done = better.call("show-better", "create", ".show/deck", "--by", "t", stdin=json.dumps(SHOW), cwd=spaced)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.folder = spaced / ".show" / "deck"
        for spelling, cwd in ((str(self.folder), self.root), ("my decks/.show/deck/", self.root)):
            with self.subTest(spelling):
                self.served()
                old = self.state()["server_pid"]
                os.kill(old, signal.SIGSTOP)
                done = subprocess.run(
                    better.command("serve", spelling, "--no-browser"),
                    cwd=cwd,
                    env=stub_env(),
                    input="",
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertTrue(wait_for(lambda pid=old: not alive(pid)))
                self.end_everything()
                (self.folder / ".server").unlink(missing_ok=True)


class TestServersEndTest(unittest.TestCase):
    """A server a test serves is ended by `stop_page` even after its folder is gone, and one left running is found
    (round 2 F1, lesson L6)."""

    def serve_in_temp_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(os.path.realpath(tmp))
            done = better.call("show-better", "create", ".show/deck", "--by", "t", stdin=json.dumps(SHOW), cwd=root)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            folder = root / ".show" / "deck"
            better.serve_page("show-better", folder, cwd=root)
            # The first turn starts once the tab pairs (S77, S93); the folder is removed only after it ended, so the
            # driver's writes for that turn do not race the removal.
            self.assertTrue(wait_for(lambda: first_turn_ended(folder)))
            state = json.loads((folder / ".driver").read_text())
        return folder, state

    def test_stop_page_ends_the_server_after_its_folder_is_removed(self):
        folder, state = self.serve_in_temp_folder()
        self.assertFalse(folder.exists())
        better.stop_page(folder)
        self.assertTrue(wait_for(lambda: not alive(state["server_pid"])))
        self.assertTrue(wait_for(lambda: not alive(state["child_pid"])))
        self.assertEqual(better.leftover_servers(), [])

    def test_a_server_left_running_is_reported_and_ended(self):
        folder, state = self.serve_in_temp_folder()
        left = better.leftover_servers()
        self.assertEqual(left, [os.path.realpath(folder)])
        self.assertTrue(wait_for(lambda: not alive(state["server_pid"])))
        self.assertTrue(wait_for(lambda: not alive(state["child_pid"])))


class MachineOutputTest(Unit):
    def test_no_machine_read_verb_gets_the_notice_on_stdout(self):  # S37, round 1 B4
        from unittest import mock

        from better_ai import cli, page, resources

        machine = {}
        for skill in (
            "architect-better",
            "code-better",
            "design-better",
            "discover-better",
            "research-better",
            "show-better",
        ):
            os.environ["BETTER_AI_SKILL"] = skill
            loaded = cli.load(resources.build_info())
            for verb in cli._verbs_of(loaded):
                if verb.machine_output:
                    machine.setdefault(verb.name, []).append(skill)
        self.assertEqual(set(machine), {"pending", "render", "summary", "specs"})
        os.environ["BETTER_AI_SKILL"] = "show-better"
        unit = better_unit(self.root, self.folder)
        (self.folder / ".driver").write_text("{}")
        alive_state = {"alive": {"session": "s", "state": "idle", "waiting": 0}}
        for name in machine:
            with self.subTest(name), mock.patch.object(page, "live_server", return_value=alive_state):
                out, err = [], []
                run = cli.Run(cli.load(resources.build_info()), resources.build_info())
                run.out, run.err = out.append, err.append
                verb = next(v for v in cli.VERBS if v.name == name)
                args = type("Args", (), {"_verb": verb, "unit": str(unit.path)})()
                self.assertIsNone(page.drive_guard(args, run))
                self.assertEqual(out, [])
                self.assertTrue(err)


class WaitingNoticeTest(Unit):
    def test_the_notice_says_the_agent_waits_for_an_approval(self):  # S122
        from better_ai import page

        unit = better_unit(self.root, self.folder)
        state = {"alive": {"session": "s", "state": "idle", "waiting": 1}}
        self.assertIn("this page's agent is waiting for your approval", page.notice_text(unit, state))
        state = {"alive": {"session": "s", "state": "working", "waiting": 0}}
        self.assertIn("this page's agent is working", page.notice_text(unit, state))

    def test_a_real_open_approval_shows_in_the_notice(self):  # S122
        done = self.served(env=stub_env(STUB_MODE="ask"))
        secret = self.pair(done)
        self.request("POST", "/rpc", {"jsonrpc": "2.0", "id": 1, "method": "note", "params": NOTE}, secret)
        self.assertTrue(wait_for(lambda: json.loads(self.request("GET", "/alive")[1])["state"] == "waiting", 20))
        check = self.verb("check", ".show/deck")
        self.assertIn("this page's agent is waiting for your approval", check.stdout)


class PendingTest(Unit):
    def write(self, *events):
        with (self.folder / "conversation.jsonl").open("a") as log:
            for event in events:
                log.write(json.dumps({"at": "2026-11-28T10:00:00Z", "by": "user", **event}) + "\n")

    def test_pending_lists_by_state_and_ignores_the_seen_file(self):  # S58
        self.write(
            {"type": "note", "id": "n-new", "text": "new", "to": None, "on": {"slide": 1, "part": None}},
            {"type": "note", "id": "n-done", "text": "done", "to": None, "on": {"slide": 1, "part": None}},
        )
        self.write({"type": "status", "by": "presenter", "to": "n-done", "status": "done"})
        (self.folder / ".conversation-seen").write_text("99")
        done = self.verb("pending", ".show/deck")
        self.assertEqual(done.returncode, 0, done.stderr)
        ids = [json.loads(line)["id"] for line in done.stdout.splitlines() if line.startswith("{")]
        self.assertEqual(ids, ["n-new"])

    def test_pending_reads_the_delivered_position_of_driver_state(self):  # S58
        self.write({"type": "note", "id": "n-1", "text": "one", "to": None, "on": {"slide": 1, "part": None}})
        self.write({"type": "reopen", "to": "n-1", "text": "again"})
        (self.folder / ".driver").write_text(json.dumps({"version": 1, "delivered": {"id": None, "position": 2}}))
        (self.folder / ".driver").chmod(0o600)
        done = self.verb("pending", ".show/deck")
        events = [json.loads(line) for line in done.stdout.splitlines() if line.startswith("{")]
        self.assertEqual([e.get("id") for e in events if e.get("type") == "note"], ["n-1"])
        self.assertEqual([e for e in events if e.get("type") == "reopen"], [])


class SurfaceTest(Unit):
    def test_wait_and_the_drive_and_open_options_are_gone(self):  # S57
        self.assertEqual(self.verb("wait", ".show/deck").returncode, 2)
        for flag in ("--drive", "--open"):
            with self.subTest(flag):
                self.assertEqual(self.verb("serve", ".show/deck", flag, "auto").returncode, 2)
        for text in (self.verb("--help").stdout, self.verb("serve", "--help").stdout):
            for gone in ("--drive", "--open", "wait "):
                self.assertNotIn(gone, text)

    def test_the_removed_approval_files_are_in_no_archive(self):  # S138, S139
        for name in ("webauthn.py", "approvals.html", "approvals.js", "approvals.css"):
            self.assertFalse((ROOT / "src" / "better_ai" / "page" / name).exists(), name)
        seen = 0
        for pyz in sorted((ROOT / "skills").glob("*/scripts/better.pyz")):
            seen += 1
            names = zipfile.ZipFile(pyz).namelist()
            for name in ("webauthn.py", "approvals.html", "approvals.js", "approvals.css"):
                self.assertFalse([n for n in names if n.endswith(name)], f"{pyz}: {name}")
            for name in ("driver.py", "adapters.py", "page-agent.md"):
                self.assertTrue([n for n in names if n.endswith("page/" + name)], f"{pyz}: {name}")
        self.assertEqual(seen, 6)
        from better_ai.page import approvals

        self.assertNotIn("webauthn", Path(approvals.__file__).read_text())
        page_source = (ROOT / "src" / "better_ai" / "page" / "__init__.py").read_text()
        for gone in ("PANEL_ASSETS", "ApprovalHandler"):
            self.assertNotIn(gone, page_source)

    def test_the_stub_is_in_no_archive_and_smoke_sees_driver_on(self):  # S136, S40
        for pyz in sorted((ROOT / "skills").glob("*/scripts/better.pyz")):
            self.assertFalse([n for n in zipfile.ZipFile(pyz).namelist() if "stub" in n], str(pyz))
        self.assertTrue((STUB / "claude").exists())
        done = subprocess.run(
            [sys.executable, "-I", str(ROOT / "tools" / "smoke.py"), "show-better"],
            capture_output=True,
            text=True,
            env={k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "BETTER_AI_STUB_HARNESS")},
            timeout=180,
            check=False,
        )
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        for path in (ROOT / "src" / "better_ai" / "page").glob("*.py"):
            for line in path.read_text().splitlines():
                if line.startswith(("import ", "from ")) and not line.startswith(("from .", "from __future__")):
                    module = line.split()[1].split(".")[0]
                    self.assertIn(module, sys.stdlib_module_names | {"better_ai"}, f"{path.name}: {line}")


if __name__ == "__main__":
    unittest.main()
