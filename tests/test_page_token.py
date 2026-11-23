"""The page token: `serve` makes a random token, keeps it in a private state file, gives it to the browser only in the
opened URL's fragment, and requires it (a header) on every request that reads or writes the conversation. `wait` sends
it from the state file; a server from before the token still answers a `wait` that sends it."""

import http.server
import json
import os
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
import better  # noqa: E402

HEADER = "X-Page-Token"
OUT_OF_DATE = "page out of date: reload"
NOTE = {"id": "m-x", "text": "hi", "to": None, "on": {"slide": 1, "part": None}}
SHOW = {
    "type": "slides",
    "title": "The answer is yes.",
    "question": "Why?",
    "panels": [{"headline": "The slide states one clear point.", "source": "test", "kind": "text", "body": ["One."]}],
}


def get(url, token=None):
    request = urllib.request.Request(url, headers={HEADER: token} if token else {})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def rpc(url, token=None):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "note", "params": NOTE}).encode()
    headers = {"Content-Type": "application/json", "Origin": url.rstrip("/")}
    if token:
        headers[HEADER] = token
    with urllib.request.urlopen(urllib.request.Request(url + "rpc", body, headers), timeout=10) as response:
        return json.loads(response.read())


class Served(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(os.path.realpath(tmp.name))
        (self.root / ".git").mkdir()
        done = better.call("show-better", "create", ".show/deck", "--by", "t", stdin=json.dumps(SHOW), cwd=self.root)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.folder = self.root / ".show" / "deck"

    def serve(self):
        process = subprocess.Popen(
            better.command("serve", str(self.folder), "--no-browser", "--linger", "0.2"),
            cwd=self.root,
            env={**os.environ, "BETTER_AI_SKILL": "show-better"},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.addCleanup(process.stdout.close)
        self.addCleanup(process.kill)
        for _ in range(100):
            if (self.folder / ".server").exists() and (self.folder / ".server").read_text().strip():
                break
            time.sleep(0.1)
        self.process = process
        self.url = (self.folder / ".server").read_text().strip()
        self.token = (self.folder / ".server-token").read_text().strip()
        return process

    def log(self):
        path = self.folder / "conversation.jsonl"
        return path.read_text().splitlines() if path.exists() else []


class TokenTest(Served):
    def test_the_token_is_random_private_and_not_in_the_address_file(self):
        self.serve()
        mode = stat.S_IMODE((self.folder / ".server-token").stat().st_mode)
        self.assertEqual(mode, 0o600)
        self.assertGreaterEqual(len(self.token), 32)
        self.assertNotIn("#", self.url)
        self.assertNotIn(self.token, self.url)
        self.process.send_signal(signal.SIGTERM)
        self.process.communicate(timeout=20)
        self.assertFalse((self.folder / ".server-token").exists())
        first = self.token
        self.serve()
        self.assertNotEqual(first, self.token)

    def test_the_address_serve_prints_carries_the_token_in_its_fragment(self):
        self.serve()
        self.process.send_signal(signal.SIGTERM)
        out = self.process.communicate(timeout=20)[0]
        self.assertIn(f"{self.url}#t={self.token}", out)

    def test_a_request_without_the_token_is_out_of_date_and_reads_and_writes_nothing(self):
        self.serve()
        for path in ("data", "events?after=0", "wait?after=0&seconds=1"):
            for token in (None, "wrong"):
                status, body = get(self.url + path, token)
                self.assertEqual((status, body.strip()), (401, OUT_OF_DATE), f"{path} with {token}")
        for token in (None, "wrong"):
            answer = rpc(self.url, token)
            self.assertEqual(answer["error"]["message"], OUT_OF_DATE)
        self.assertEqual(self.log(), [])

    def test_a_request_with_the_token_is_answered(self):
        self.serve()
        self.assertEqual(rpc(self.url, self.token)["result"], "saved")
        self.assertEqual(get(self.url + "data", self.token)[0], 200)
        self.assertEqual(get(self.url + "events?after=0", self.token)[0], 200)
        self.assertEqual(get(self.url + "wait?after=0&seconds=1", self.token)[0], 200)
        self.assertEqual(len(self.log()), 1)

    def test_the_page_its_files_and_the_listening_state_stay_open(self):
        self.serve()
        for path in ("", "page.js", "page.css", "listening", "rev"):
            self.assertEqual(get(self.url + path)[0], 200, path)

    def test_wait_sends_the_token_and_returns_what_the_user_sent(self):
        self.serve()
        rpc(self.url, self.token)
        done = better.call("show-better", "wait", str(self.folder), "--timeout", "10", cwd=self.root)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn('"type": "note"', done.stdout)

    def test_wait_still_works_against_a_server_from_before_the_token(self):
        seen = []

        class Old(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # ignores every header, as a server from before the token does
                seen.append(self.headers.get(HEADER))
                body = b"0"
                self.send_response(200)
                self.send_header("Content-Length", "1")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), Old)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        (self.folder / ".server").write_text(f"http://127.0.0.1:{server.server_address[1]}/")
        (self.folder / ".conversation-seen").write_text("0")
        done = better.call("show-better", "wait", str(self.folder), "--timeout", "1", cwd=self.root)
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)  # timed out: it did get an answer
        self.assertEqual(seen[0], None)  # no state file, so no header
        (self.folder / ".server-token").write_text("abc")
        better.call("show-better", "wait", str(self.folder), "--timeout", "1", cwd=self.root)
        self.assertEqual(seen[-1], "abc")


if __name__ == "__main__":
    unittest.main()
