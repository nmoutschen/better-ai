"""The user-facing serving contract and the wait fallback."""

import json
import os
import select
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import better
from test_page_token import NOTE, Served, rpc


class DrivenServeTest(Served):
    def test_auto_without_an_adapter_keeps_wait_mode(self):
        process = subprocess.Popen(
            better.command("serve", str(self.folder), "--drive", "auto", "--no-browser"),
            cwd=self.root,
            env={"PATH": os.defpath, "BETTER_AI_SKILL": "show-better"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            first = process.stdout.readline()
            self.assertEqual(first.strip(), "driver: off none", first or process.stderr.read())
            serving = process.stdout.readline().strip()
            self.assertIn("Each action the user takes is printed here as one JSON line. Serving", serving)
            url, token = serving.split(" at ", 1)[1].split("#t=")
            self.assertEqual(rpc(url, token)["result"], "saved")
            self.assertIn('"type":"note"', process.stdout.readline().replace(" ", ""))
            waited = better.run("show-better", "wait", str(self.folder), "--timeout", "2", cwd=self.root)
            self.assertEqual(waited.returncode, 0, waited.stderr)
            self.assertIn('"type":"note"', waited.stdout.replace(" ", ""))
        finally:
            process.terminate()
            process.communicate(timeout=10)

    def test_existing_page_refuses_a_second_server_and_link(self):
        process = self.serve()
        try:
            for args in ((), ("--link",)):
                with self.subTest(args=args):
                    result = better.run("show-better", "serve", str(self.folder), "--once", *args, cwd=self.root)
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn(self.url, result.stderr)
        finally:
            process.terminate()
            process.communicate(timeout=10)

    def test_unknown_drive_value_is_a_usage_error(self):
        result = better.run("show-better", "serve", str(self.folder), "--drive", "unknown", cwd=self.root)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def launch_driven(self, *, enrolled=True, hanging=False, once=False, delay=0, version="2.4.1", stale=False):
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        stub = bin_dir / "opencode"
        stub.write_text(
            f"#!{sys.executable}\n"
            + """
import json, pathlib, sys, time

if sys.argv[1:] == ["--version"]:
    print("opencode " + CLI_VERSION)
    sys.exit()
pathlib.Path("harness-started").touch()
for line in sys.stdin:
    msg = json.loads(line)
    if HANGING:
        time.sleep(60)
    replies = {
        "initialize": {"protocolVersion": 1, "agentInfo": {"version": "2.4.1"}},
        "session/new": {"sessionId": "session-test", "modes": {"currentModeId": "build"}},
        "session/prompt": {"stopReason": "end_turn"},
    }
    if msg["method"] in replies:
        print(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": replies[msg["method"]]}), flush=True)
""".replace("HANGING", repr(hanging)).replace("CLI_VERSION", repr(version))
        )
        stub.chmod(0o700)
        bootstrap = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv.pop(1))
from better_ai.page import approvals
from better_ai import cli, page
approvals.credential_file = lambda: Path("test-credential")
credential = sys.argv.pop(1)
if credential == "True":
    approvals.load_credential = lambda path: {"id": "stub"}
elif credential == "invalid":
    path = Path("test-credential")
    path.write_text("invalid")
    path.chmod(0o600)
stale = sys.argv.pop(1) == "True"
if stale:
    from better_ai.page.driver import Driver
    snapshot = Driver.snapshot
    Driver.snapshot = lambda self: {**snapshot(self), "age": 4}
wait_for_more = page.Conversation.wait_for_more
def marked_wait(self, after, seconds):
    Path("poll-started").touch()
    return wait_for_more(self, after, seconds)
page.Conversation.wait_for_more = marked_wait
delay = float(sys.argv.pop(1))
if delay:
    import time
    original = page.schema.check_paths
    def slow(*args, **kwargs):
        time.sleep(delay)
        return original(*args, **kwargs)
    page.schema.check_paths = slow
page.START_TIMEOUT = 1.2
page.ENROLL_TIMEOUT = 1.4
sys.exit(cli.main())
"""
        process = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-c",
                bootstrap,
                str(better.SRC),
                str(enrolled),
                str(stale),
                str(delay),
                "serve",
                str(self.folder),
                "--drive",
                "opencode",
                "--no-browser",
                *(["--once"] if once else []),
            ],
            cwd=self.root,
            env={"PATH": os.fspath(bin_dir), "BETTER_AI_SKILL": "show-better"},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        def cleanup():
            if process.poll() is None:
                process.terminate()
            process.communicate(timeout=10)

        self.addCleanup(cleanup)
        return process

    def request(self, url, *, token=None, body=None, site="same-origin", origin=None):
        headers = {"Sec-Fetch-Site": site}
        if token is not None:
            headers["X-Page-Token"] = token
        if body is not None:
            headers["Content-Type"] = "application/json"
            location = urllib.parse.urlsplit(url)
            headers["Origin"] = origin or f"{location.scheme}://{location.netloc}"
        request = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as response:
            return response.code, response.read().decode()

    def pair(self, url):
        parsed = urllib.parse.urlsplit(url)
        root = f"{parsed.scheme}://{parsed.netloc}/"
        code, result = self.request(root + "pair", body={"token": parsed.fragment.removeprefix("p=")})
        self.assertEqual(code, 200, result)
        return root, result

    def test_driven_routes_rotate_and_wait_refuses(self):
        process = self.launch_driven()
        first = process.stdout.readline().strip()
        self.assertEqual(first, "driver: on opencode session-test", first or process.stderr.read())
        panel, paired = self.pair(process.stdout.readline().strip().split(" at ", 1)[1])
        main, conversation = self.pair(paired["page"])
        self.assertFalse((self.folder / ".server-token").exists())
        self.assertEqual(self.request(main + "agent", token=conversation["secret"])[1]["state"], "idle")
        self.assertEqual(self.request(main + "agent", token=conversation["secret"], site="cross-site")[0], 403)
        self.assertEqual(self.request(main + "data", token=paired["secret"])[0], 403)
        self.assertEqual(self.request(panel + "agent", token=conversation["secret"])[0], 403)
        self.assertEqual(self.request(panel + "data", token=paired["secret"])[0], 404)
        with urllib.request.urlopen(main, timeout=3) as response:
            policy = response.headers["Content-Security-Policy"]
        for directive in (
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline' data: http: https:",
            "frame-src 'self' http: https:",
            "base-uri 'none'",
            "form-action 'self'",
        ):
            self.assertIn(directive, policy.split("; "))
        for verb, options in (
            ("wait", ()),
            ("serve", ("--once",)),
            ("pending", ()),
        ):
            with self.subTest(verb=verb):
                result = better.run("show-better", verb, str(self.folder), *options, cwd=self.root)
                self.assertIn("this unit's page is driven by session session-test", result.stderr)
                self.assertEqual(result.returncode, int(verb != "pending"))
        stopped = self.request(
            panel + "rpc",
            token=paired["secret"],
            body={"jsonrpc": "2.0", "id": 1, "method": "agent_stop", "params": {}},
        )
        self.assertTrue(stopped[1]["result"])
        sent = self.request(
            main + "rpc",
            token=conversation["secret"],
            body={"jsonrpc": "2.0", "id": 2, "method": "note", "params": NOTE},
        )
        self.assertEqual(sent[1]["result"], "saved")
        new = better.run("show-better", "serve", str(self.folder), "--link", cwd=self.root)
        self.assertEqual(new.returncode, 0, new.stderr)
        for endpoint in ("agent", "data", "events?after=0"):
            self.assertEqual(self.request(main + endpoint, token=conversation["secret"])[0], 403)
        self.assertEqual(self.request(main + "rpc", token=conversation["secret"], body={"jsonrpc": "2.0"})[0], 403)
        self.assertEqual(self.request(panel + "agent", token=paired["secret"])[0], 403)
        self.pair(new.stdout.strip())
        process.terminate()
        stdout, _ = process.communicate(timeout=10)
        self.assertEqual(stdout, "")

    def test_enrollment_timeout_prints_the_link_without_launching_the_harness(self):
        process = self.launch_driven(enrolled=False)
        first = process.stdout.readline().strip()
        self.assertTrue(first.startswith("Enrollment at http://localhost:"), first)
        panel, paired = self.pair(first.split(" at ", 1)[1])
        self.assertTrue(self.request(panel + "agent", token=paired["secret"])[1]["enrollment_needed"])
        self.assertEqual(process.stdout.readline().strip(), "driver: off no-approvals")
        self.assertIn("#t=", process.stdout.readline())
        self.assertFalse((self.root / "harness-started").exists())
        agent = self.request(panel + "agent", token=paired["secret"])[1]
        self.assertFalse(agent["can_start"])
        self.assertEqual(agent["kind"], "no-approvals")
        code, link = self.request(
            panel + "rpc",
            token=paired["secret"],
            body={"jsonrpc": "2.0", "id": 1, "method": "open_conversation", "params": {}},
        )
        self.assertEqual(code, 200)
        self.assertEqual(link["result"], agent["page"])

    def test_hanging_start_falls_back_without_start(self):
        process = self.launch_driven(hanging=True)
        self.assertEqual(process.stdout.readline().strip(), "driver: off crashed")
        address = process.stdout.readline().split(" at ", 1)[1].strip()
        url, token = address.split("#t=")
        self.assertEqual(self.request(url + "agent", token=token)[0], 404)
        self.assertTrue((self.root / "harness-started").exists())

    def test_orphan_cleanup_checks_the_exact_command_line(self):
        from better_ai.page.transport import process_command

        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)"], start_new_session=True)
        self.addCleanup(child.wait, timeout=3)
        self.addCleanup(child.kill)
        command = process_command(child.pid)
        if not command:
            self.skipTest("Process command lines are not available on this OS")
        state_file = self.folder / ".driver"
        state = {
            "version": 1,
            "harness": "opencode",
            "session": "session-old",
            "opened": 1.0,
            "child_pid": child.pid,
        }
        for argv in (["another", "command"], command.split(" ")):
            state_file.write_text(json.dumps({**state, "child_argv": argv}))
            state_file.chmod(0o600)
            server = self.serve()
            server.terminate()
            server.communicate(timeout=3)
            if argv[0] == "another":
                self.assertIsNone(child.poll())
            else:
                self.assertLess(child.wait(timeout=3), 0)

    def test_invalid_enrollment_file_preserves_wait_fallback(self):
        process = self.launch_driven(enrolled="invalid")
        self.assertEqual(process.stdout.readline().strip(), "driver: off no-approvals")
        self.assertIn("#t=", process.stdout.readline())
        self.assertFalse((self.root / "harness-started").exists())

    def test_validation_counts_toward_the_startup_deadline(self):
        process = self.launch_driven(delay=3)
        self.assertTrue(select.select([process.stdout], [], [], 2.5)[0])
        self.assertEqual(process.stdout.readline().strip(), "driver: off crashed")
        self.assertIn("#t=", process.stdout.readline())
        self.assertFalse((self.root / "harness-started").exists())

    def test_fallback_after_a_running_handshake_still_serves_once(self):
        process = self.launch_driven(hanging=True, once=True)
        self.assertEqual(process.stdout.readline().strip(), "driver: off crashed")
        address = process.stdout.readline().split(" at ", 1)[1].strip()
        with urllib.request.urlopen(address, timeout=3) as response:
            self.assertEqual(response.status, 200)
        self.assertEqual(process.wait(timeout=3), 0)

    def test_unsupported_version_reports_detected_and_required_versions(self):
        process = self.launch_driven(version="1.2.3", once=True)
        self.assertEqual(process.stdout.readline().strip(), "driver: off version")
        address = process.stdout.readline().split(" at ", 1)[1].strip()
        with urllib.request.urlopen(address, timeout=3):
            pass
        _, diagnostics = process.communicate(timeout=3)
        for detail in ("1.2.3", "2.4.1", "serve again"):
            self.assertIn(detail, diagnostics)
        self.assertNotIn("Start", diagnostics)

    def test_link_rotation_denies_events_already_waiting(self):
        import time

        process = self.launch_driven()
        self.assertIn("driver: on", process.stdout.readline())
        _, paired = self.pair(process.stdout.readline().strip().split(" at ", 1)[1])
        main, conversation = self.pair(paired["page"])
        with ThreadPoolExecutor() as pool:
            poll = pool.submit(self.request, main + "events?after=0", token=conversation["secret"])
            deadline = time.monotonic() + 2
            while not (self.root / "poll-started").exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue((self.root / "poll-started").exists())
            rotated = better.run("show-better", "serve", str(self.folder), "--link", cwd=self.root)
            self.assertEqual(rotated.returncode, 0, rotated.stderr)
            _, paired = self.pair(rotated.stdout.strip())
            main, new = self.pair(paired["page"])
            code, reply = self.request(
                main + "rpc",
                token=new["secret"],
                body={"jsonrpc": "2.0", "id": 1, "method": "note", "params": NOTE},
            )
            self.assertEqual(code, 200)
            self.assertEqual(reply["result"], "saved")
            self.assertEqual(poll.result(timeout=3)[0], 403)

    def test_a_live_server_can_pair_when_its_driver_is_stale(self):
        process = self.launch_driven(stale=True)
        self.assertIn("driver: on", process.stdout.readline())
        self.assertIn("Serving", process.stdout.readline())
        linked = better.run("show-better", "serve", str(self.folder), "--link", cwd=self.root)
        self.assertEqual(linked.returncode, 0, linked.stderr)
        panel, paired = self.pair(linked.stdout.strip())
        agent = self.request(panel + "agent", token=paired["secret"])[1]
        self.assertGreater(agent["age"], 3)
        self.assertFalse(agent["can_start"])

    def test_panel_reopens_the_conversation_without_repairing_itself(self):
        process = self.launch_driven()
        self.assertIn("driver: on", process.stdout.readline())
        panel, paired = self.pair(process.stdout.readline().strip().split(" at ", 1)[1])
        request = {"jsonrpc": "2.0", "id": 1, "method": "open_conversation", "params": {}}
        code, first = self.request(panel + "rpc", token=paired["secret"], body=request)
        self.assertEqual(code, 200)
        main, conversation = self.pair(first["result"])
        self.assertEqual(self.request(main + "agent", token=conversation["secret"])[0], 200)
        self.assertEqual(self.request(panel + "rpc", body=request)[0], 403)
        _, second = self.request(panel + "rpc", token=paired["secret"], body=request)
        self.assertNotEqual(first["result"], second["result"])
        new_main, new_conversation = self.pair(second["result"])
        self.assertEqual(new_main, main)
        self.assertEqual(self.request(main + "agent", token=conversation["secret"])[0], 403)
        self.assertEqual(self.request(main + "agent", token=new_conversation["secret"])[0], 200)
        self.assertEqual(self.request(panel + "agent", token=paired["secret"])[0], 200)
