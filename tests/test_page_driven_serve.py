"""The user-facing serving contract and the wait fallback."""

import os
import subprocess

import better
from test_page_token import Served, rpc


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
            self.assertEqual(first.strip(), "driver: off none", first + process.stderr.read() if not first else first)
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
        self.serve()
        for args in ((), ("--link",)):
            with self.subTest(args=args):
                result = better.run("show-better", "serve", str(self.folder), "--once", *args, cwd=self.root)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(self.url, result.stderr)

    def test_unknown_drive_value_is_a_usage_error(self):
        result = better.run("show-better", "serve", str(self.folder), "--drive", "unknown", cwd=self.root)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
