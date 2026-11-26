"""The user-facing serving contract and the wait fallback."""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

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

    def launch_driven(self, *, enrolled=True, hanging=False):
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        stub = bin_dir / "opencode"
        stub.write_text(
            f"#!{sys.executable}\n"
            + """
import json, pathlib, sys, time

if sys.argv[1:] == ["--version"]:
    print("opencode 2.4.1")
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
""".replace("HANGING", repr(hanging))
        )
        stub.chmod(0o700)
        bootstrap = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv.pop(1))
from better_ai.page import approvals
from better_ai import cli, page
approvals.credential_file = lambda: Path("test-credential")
if sys.argv.pop(1) == "True":
    approvals.load_credential = lambda path: {"id": "stub"}
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
                "serve",
                str(self.folder),
                "--drive",
                "opencode",
                "--no-browser",
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
        self.assertEqual(self.request(main + "agent", token=conversation["secret"], site="cross-site")[0], 401)
        self.assertEqual(self.request(main + "data", token=paired["secret"])[0], 401)
        self.assertEqual(self.request(panel + "agent", token=conversation["secret"])[0], 403)
        self.assertEqual(self.request(panel + "data", token=paired["secret"])[0], 404)
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
        self.assertEqual(self.request(main + "agent", token=conversation["secret"])[0], 401)
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

    def test_hanging_start_falls_back_without_start(self):
        process = self.launch_driven(hanging=True)
        self.assertEqual(process.stdout.readline().strip(), "driver: off crashed")
        address = process.stdout.readline().split(" at ", 1)[1].strip()
        url, token = address.split("#t=")
        self.assertEqual(self.request(url + "agent", token=token)[0], 404)
        self.assertTrue((self.root / "harness-started").exists())

    def test_orphan_cleanup_checks_the_exact_process_birth(self):

        from better_ai.page.transport import process_birth

        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)"], start_new_session=True)
        self.addCleanup(child.wait, timeout=3)
        self.addCleanup(child.kill)
        birth = process_birth(child.pid)
        if not birth:
            self.skipTest("Process birth is not available on this OS")
        state_file = self.folder / ".driver"
        state = {
            "version": 1,
            "harness": "opencode",
            "session": "session-old",
            "child_pid": child.pid,
        }
        for recorded in ("from-a-previous-boot", birth):
            state_file.write_text(json.dumps({**state, "child_started": recorded}))
            state_file.chmod(0o600)
            server = self.serve()
            server.terminate()
            server.communicate(timeout=3)
            if recorded != birth:
                self.assertIsNone(child.poll())
            else:
                self.assertLess(child.wait(timeout=3), 0)
