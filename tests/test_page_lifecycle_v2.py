"""The page protocol's flows across its parts (task T8): serve, the server, the driver, the adapter and the verbs
together, with the stub harness of tests/fixtures/stub-harness as the user's own `claude`.

Each test serves a unit as a caller does and talks to the server as a paired tab does. Nothing here opens a browser:
`--no-browser`, or the stub browser as webbrowser.open (tests/fixtures/stub-browser). A test that needs time to pass
(20 idle minutes, 30 idle minutes) moves the driver's clock, not the wall clock: `CLOCK_BOOT` makes the driver's clock
the real one plus the number of seconds in the file STUB_CLOCK names.

Written from the spec, the design and the agreed interfaces (decisions D1, D8, D11 of the change); each test names its
requirements. A failing check marked FINDING is a bug of the code, kept on purpose."""

import json
import os
import shlex
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))
import better  # noqa: E402
from test_page_cli_v2 import NOTE, SHOW, UUID, Unit, alive, stub_env, wait_for  # noqa: E402
from test_page_pairing_v2 import Browser, rpc  # noqa: E402

CLOCK_BOOT = """
import os, pathlib, time
from better_ai.page import driver

_init = driver.Driver.__init__

def _clocked(self, *args, **kwargs):
    path = pathlib.Path(os.environ["STUB_CLOCK"])
    kwargs["clock"] = lambda: time.monotonic() + (float(path.read_text() or 0) if path.exists() else 0)
    _init(self, *args, **kwargs)

driver.Driver.__init__ = _clocked
"""
FIELDS = {
    "version",
    "harness",
    "session",
    "tag",
    "server_pid",
    "server_started",
    "child_pid",
    "child_argv",
    "opened",
    "delivered",
    "note",
    "fired",
    "handoff_delivered",
    "turn",
    "ended",
}
HEADER_RULES = "Rules: every word for the user through reply; end the turn when the items are handled; never serve."
PYZ = ROOT / "skills" / "show-better" / "scripts" / "better.pyz"


def note(ident, text="hello"):
    return {**NOTE, "id": ident, "text": text}


class Flow(Unit):
    """A served unit with a stub harness that records what it is sent, and a paired tab."""

    def setUp(self):
        super().setUp()
        self.dump = self.root / "stub.dump"
        self.log = self.root / "stub.log"
        self.clock = self.root / "stub.clock"
        self.result = self.root / "stub.result"

    def env(self, **changes):
        return stub_env(
            STUB_DUMP=str(self.dump),
            STUB_LOG=str(self.log),
            STUB_CLOCK=str(self.clock),
            STUB_RESULT=str(self.result),
            STUB_HANDLE=json.dumps(better.command()),
            **changes,
        )

    def start(self, mode=None, clocked=False, **changes):
        """Serve the unit with the stub in `mode`; the tab's secret."""
        env = self.env(**({"STUB_MODE": mode} if mode else {}), **changes)
        done = self.served(env=env, boot=CLOCK_BOOT if clocked else None)
        self.secret = self.pair(done)
        self.done = done
        return self.secret

    # ---------- what the harness was sent

    def prompts(self):
        """The text of each turn's prompt the stub received, in order."""
        found = []
        if not self.dump.exists():
            return found
        for line in self.dump.read_text().splitlines():
            if not line.startswith("{"):
                continue
            message = json.loads(line)
            if message.get("type") == "user":
                content = message["message"]["content"]
                found.append(content if isinstance(content, str) else "".join(p.get("text", "") for p in content))
        return found

    def launches(self):
        """One (pid, session tag, argv) for each harness process the stub saw start."""
        if not self.log.exists():
            return []
        return [line.split(" ", 2) for line in self.log.read_text().splitlines()]

    def turns(self, count, seconds=30):
        return wait_for(lambda: len(self.prompts()) >= count, seconds)

    # ---------- what the server says

    def agent(self, secret=None):
        status, text = self.request("GET", "/agent", secret=secret or self.secret)
        self.assertEqual(status, 200, text)
        return json.loads(text)

    def call(self, method, params=None, secret=None):
        status, text = self.request("POST", "/rpc", rpc(method, params), secret or self.secret)
        self.assertEqual(status, 200, text)
        return json.loads(text)

    def state_is(self, state, seconds=20):
        return wait_for(lambda: self.agent()["state"] == state, seconds)

    def an_approval(self, seconds=20):
        self.assertTrue(wait_for(lambda: self.agent()["approvals"], seconds), "no approval opened")
        return self.agent()["approvals"][0]

    def records(self, kind=None):
        text = (self.folder / ".driver.log").read_text()
        records = [json.loads(line) for line in text.splitlines() if line.startswith("{")]
        return [r for r in records if kind is None or r.get("type") == kind]

    def stopped_process(self, pid, seconds=5):
        return wait_for(lambda: not alive(pid), seconds)


class IdleTest(Flow):
    def test_a_comment_after_20_idle_minutes_starts_a_turn_within_30_seconds(self):  # S12, S14
        self.start(clocked=True)
        self.assertTrue(self.turns(1))
        self.assertTrue(self.state_is("idle"))
        self.clock.write_text("900")  # 15 simulated minutes with no trigger
        time.sleep(2)
        self.assertEqual(len(self.prompts()), 1, "no model call without a trigger (S14)")
        self.clock.write_text("1200")  # 20 minutes
        started = time.monotonic()
        self.assertEqual(self.call("note", note("m-late", "after twenty minutes"))["result"], "saved")
        self.assertTrue(self.turns(2, 30), "no turn started for a comment after 20 idle minutes")
        self.assertLess(time.monotonic() - started, 30)
        self.assertIn("m-late", self.prompts()[-1])

    def test_the_server_ends_30_minutes_after_the_tab_stops_polling(self):  # S104, S43
        self.start(clocked=True)
        self.assertTrue(self.turns(1))
        self.assertTrue(self.state_is("idle"))
        pid = self.state()["server_pid"]
        time.sleep(1)  # the last poll of the tab
        self.clock.write_text(str(29 * 60))
        time.sleep(3)
        self.assertTrue(alive(pid), "the server must not end before 30 minutes")
        self.clock.write_text(str(31 * 60))
        self.assertTrue(wait_for(lambda: not alive(pid), 30), "the server did not exit after 30 idle minutes")
        self.assertFalse((self.folder / ".server").exists())
        ended = self.state()["ended"]
        self.assertTrue(ended["reason"], "a planned exit records its reason")
        self.assertNotEqual(ended.get("kind"), "driver", "idle end is a planned exit, not a driver error")


class TurnsTest(Flow):
    def test_a_comment_during_a_turn_starts_the_next_turn_within_5_seconds_of_its_end(self):  # S13, S14
        self.start("ask")
        approval = self.an_approval()
        self.assertEqual(set(approval), {"id", "who", "tool", "arguments", "summary", "since", "options"})  # D1
        self.assertEqual(self.call("note", note("m-during", "sent while the turn runs"))["result"], "saved")
        time.sleep(1)
        self.assertEqual(len(self.prompts()), 1, "a comment during a turn waits for the turn to end")
        self.assertEqual(self.agent()["state"], "waiting")
        answered = time.monotonic()
        self.assertTrue(self.call("permission_answer", {"id": approval["id"], "choice": "allow_once"})["result"])
        self.assertTrue(self.turns(2, 10))
        self.assertLess(time.monotonic() - answered, 5 + 1)
        self.assertIn("m-during", self.prompts()[1])
        self.assertTrue(self.state_is("idle"))
        time.sleep(2)
        self.assertEqual(len(self.prompts()), 2, "no turn without a trigger")

    def test_an_approval_answered_in_the_pop_up_flow_through_rpc(self):  # S161, S5, S43
        self.start("ask")
        approval = self.an_approval()
        self.assertEqual(approval["tool"], "Bash")
        self.assertIsInstance(approval["arguments"], str)  # D7
        self.assertIsInstance(approval["summary"], str)
        self.assertIn("allow_once", approval["options"])
        self.assertIn("deny", approval["options"])
        self.assertEqual(json.loads(self.request("GET", "/alive")[1])["waiting"], 1)
        self.assertTrue(self.call("permission_answer", {"id": approval["id"], "choice": "deny"})["result"])
        self.assertTrue(wait_for(lambda: not self.agent()["approvals"], 20))
        self.assertTrue(self.state_is("idle"))
        self.assertEqual(json.loads(self.request("GET", "/alive")[1])["waiting"], 0)
        for line in (self.folder / "conversation.jsonl").read_text().splitlines() if self.has_log() else []:
            self.assertNotIn(json.loads(line)["type"], ("permission_answer", "approval"), "no copy in the conversation")

    def has_log(self):
        return (self.folder / "conversation.jsonl").exists()

    def test_the_notice_of_a_chat_agents_verb_names_the_approval_wait(self):  # S122
        self.start("ask")
        self.an_approval()
        done = self.verb("pending", ".show/deck")
        self.assertIn("this page's agent is waiting for your approval", done.stderr + done.stdout)


class StopStartTest(Flow):
    def test_stop_denies_the_open_approval_ends_the_harness_and_holds_comments_until_start(self):  # S19, S20, S43
        self.start("ask")
        self.an_approval()
        first = self.state()["child_pid"]
        self.assertTrue(alive(first))
        self.assertTrue(self.call("agent_stop")["result"])
        self.assertTrue(self.state_is("stopped"), self.agent())
        self.assertTrue(self.stopped_process(first, 5), "the harness is still running 5 s after Stop")
        self.assertEqual(self.agent()["approvals"], [])
        self.assertEqual([a.get("reason") for a in self.records("approval")], ["stopped by the user"])
        # a comment while stopped starts nothing
        self.assertEqual(self.call("note", note("m-stopped", "while stopped"))["result"], "saved")
        time.sleep(3)
        self.assertEqual(len(self.prompts()), 1)
        self.assertEqual(self.agent()["state"], "stopped")
        self.assertEqual(len(self.launches()), 1, "no harness starts while the agent is stopped")
        # Start: the same tab, the same secret, a turn with the comment
        self.assertTrue(self.call("agent_start")["result"])
        self.assertTrue(self.turns(2, 30))
        self.assertIn("m-stopped", self.prompts()[-1])
        self.assertEqual(len(self.launches()), 2)
        self.assertEqual(
            self.launches()[1][1], self.launches()[0][1], "the page agent keeps its tag across Stop and Start"
        )
        self.assertEqual(self.request("GET", "/agent", secret=self.secret)[0], 200)

    def test_stop_with_nothing_running_and_start_again_gives_a_turn_for_a_waiting_comment(self):  # S20, S128
        self.start()
        self.assertTrue(self.turns(1))
        self.assertTrue(self.state_is("idle"))
        self.call("agent_stop")
        self.assertTrue(self.state_is("stopped"))
        self.call("note", note("m-wait", "waiting"))
        time.sleep(2)
        self.assertEqual(len(self.prompts()), 1)
        self.call("agent_start")
        self.assertTrue(self.turns(2, 30))
        self.assertIn("m-wait", self.prompts()[-1])


class RestartTest(Flow):
    def test_a_server_ended_with_an_approval_open_resumes_the_session_and_delivers_the_waiting_comment(self):
        # S17, S43, S47, S150
        self.start("ask")
        self.an_approval()
        self.call("note", note("m-restart", "sent before the server ends"))
        state = self.state()
        server, child = state["server_pid"], state["child_pid"]
        session = state["session"]
        os.kill(server, signal.SIGTERM)
        self.assertTrue(wait_for(lambda: not alive(server), 10))
        self.assertTrue(self.stopped_process(child, 5), "the harness's process group must be gone within 5 s (S47)")
        approvals = self.records("approval")
        self.assertTrue(approvals, "the approval is logged")
        for record in approvals:
            self.assertIn(record.get("answer"), ("denied", "expired"), "the open approval is closed (S43)")
            self.assertTrue(record.get("reason"), "with its reason (S43)")
        ended = self.state()["ended"]
        self.assertTrue(ended["reason"])
        done = self.served(env=self.env())
        self.assertRegex(done.stdout, rf"^driver: on claude {session}\n", "the same session resumes (S48)")
        self.pair(done)  # no turn starts before a tab pairs (S77)
        self.assertTrue(self.turns(2, 30))
        self.assertIn("m-restart", self.prompts()[-1], "an undelivered comment starts a turn on start (S17)")
        launches = self.launches()
        self.assertEqual(len(launches), 2)
        self.assertIn(f"--resume={session}", launches[1][2])
        state = self.state()
        self.assertEqual(set(state), FIELDS)
        self.assertEqual(state["version"], 1)
        self.assertEqual(set(state["ended"]), {"at", "reason", "kind", "build", "repeats"})
        self.assertEqual(state["session"], session)
        self.assertEqual(state["ended"]["repeats"], 0)

    def test_the_harness_killed_with_an_approval_open_closes_it_and_a_new_turn_goes_on(self):  # S43
        self.start("ask")
        self.an_approval()
        child = self.state()["child_pid"]
        os.kill(child, signal.SIGKILL)
        self.assertTrue(wait_for(lambda: not self.agent()["approvals"], 20), "an approval of a dead harness stays open")

    def test_sigterm_mid_turn_ends_the_harness_group_and_removes_the_server_files(self):  # S47
        self.start("ask")
        self.an_approval()
        state = self.state()
        os.kill(state["server_pid"], signal.SIGTERM)
        self.assertTrue(wait_for(lambda: not alive(state["server_pid"]), 10))
        self.assertTrue(self.stopped_process(state["child_pid"], 5))
        self.assertFalse((self.folder / ".server").exists())
        self.assertFalse((self.folder / ".page-link").exists())


class DriverErrorTest(Flow):
    def test_a_driver_that_cannot_open_ends_the_serve_and_the_third_is_refused(self):  # S106
        boot = "from better_ai.page import driver\n\ndef boom(self, *a):\n    raise RuntimeError('boom')\n\ndriver.Driver._open = boom\n"
        outputs = [self.serve(env=self.env(), boot=boot) for _ in range(3)]
        self.assertTrue(all(done.returncode == 1 for done in outputs))
        self.assertRegex(outputs[0].stdout, r"^driver: off driver: boom; see \S+\.driver\.log\n$")
        self.assertRegex(
            outputs[2].stdout,
            r"^driver: off driver: the same error came back: .*boom; see \S+; this is a better-ai problem\n$",
        )
        self.assertEqual(self.state()["ended"]["repeats"], 1)
        self.assertEqual(self.launches(), [], "no harness ran")

    def test_a_driver_error_while_served_keeps_its_reason_in_ended_and_on_the_page(self):  # S62, B2
        flag = self.root / "boom.flag"
        boot = (
            "import os\nfrom better_ai.page import driver\n\n_check = driver.Driver._check_unit\n\n"
            f"def check(self):\n    if os.path.exists({str(flag)!r}):\n        raise RuntimeError('boom')\n    _check(self)\n\n"
            "driver.Driver._check_unit = check\n"
        )
        done = self.served(env=self.env(), boot=boot)
        self.secret = self.pair(done)
        server = self.state()["server_pid"]
        flag.write_text("")
        self.assertTrue(wait_for(lambda: self.agent()["state"] == "failed", 20))
        body = self.agent()
        self.assertEqual(body["kind"], "driver")
        self.assertIn("boom", body["text"])
        self.assertTrue(wait_for(lambda: not alive(server), 20), "the server ends after a driver error")
        self.assertEqual((self.state()["ended"]["kind"], self.state()["ended"]["reason"]), ("driver", "boom"))


class VerbFormTest(Unit):
    """The page agent's own calls, as the header's form approves them, in a unit whose path holds a space."""

    def setUp(self):
        super().setUp()
        if not PYZ.exists():
            self.skipTest("the built better.pyz of show-better is missing")
        self.workdir = self.root / "a b"
        self.workdir.mkdir()
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
        subprocess.run([*git, "init", "-q", "-b", "main"], cwd=self.workdir, check=True)
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "x"], cwd=self.workdir, check=True)
        self.dump, self.result = self.root / "stub.dump", self.root / "stub.result"
        self.commands = [
            "{python} {pyz} reply {unit} --by page-agent <<'EOF'\nit's a page agent reply\nEOF",
            "{python} {pyz} reply {unit} --by worker-1 <<'EOF'\na worker's line\nEOF",
            "{python} {pyz} reply .show/deck --by page-agent <<'EOF'\nrelative\nEOF",
            "{python} {pyz} reply {unit} --by user <<'EOF'\nas the user\nEOF",
            "{python} {pyz} reply {unit} --by page-agent; echo no",
        ]
        env = stub_env(STUB_DUMP=str(self.dump), STUB_RESULT=str(self.result))
        env["STUB_MODE"] = "verb"
        env["STUB_COMMANDS"] = json.dumps(self.commands)
        made = subprocess.run(
            [sys.executable, str(PYZ), "create", ".show/deck", "--by", "t"],
            input=json.dumps(SHOW),
            cwd=self.workdir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
        self.folder = self.workdir / ".show" / "deck"
        done = subprocess.run(
            [sys.executable, str(PYZ), "serve", ".show/deck", "--no-browser"],
            cwd=self.workdir,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.addCleanup(self.end_everything)
        self.secret = self.pair(done)
        self.assertTrue(wait_for(lambda: self.result.exists() and len(self.answers()) == len(self.commands), 30))

    def answers(self):
        return [json.loads(line) for line in self.result.read_text().splitlines()] if self.result.exists() else []

    def first_prompt(self):
        for line in self.dump.read_text().splitlines():
            if line.startswith("{") and json.loads(line).get("type") == "user":
                content = json.loads(line)["message"]["content"]
                return content if isinstance(content, str) else "".join(p.get("text", "") for p in content)
        return ""

    def test_the_header_names_the_unit_quoted_and_the_approved_form(self):  # S95, S9, D29
        prompt = self.first_prompt()
        unit = str(self.folder)
        self.assertIn(f"Unit: {unit}\n", prompt)
        header = [line for line in prompt.splitlines() if line.startswith("Approved without asking: ")][0]
        self.assertIn(f"{sys.executable} {PYZ} <verb> ", header)
        self.assertIn(shlex.quote(os.path.realpath(unit)), header, "a path with a space is printed quoted (D29)")
        self.assertIn(HEADER_RULES, prompt)

    def test_the_page_agents_and_workers_calls_in_the_header_form_are_approved_and_run(self):  # S9, D24, D29
        answers = self.answers()
        for number in (0, 1):
            with self.subTest(command=number):
                self.assertEqual(answers[number]["behavior"], "allow", answers[number])
                self.assertEqual(answers[number]["exit"], 0)
        text = (self.folder / "conversation.jsonl").read_text()
        self.assertIn("it's a page agent reply", text)
        self.assertIn("a worker's line", text)

    def test_each_allowed_call_is_logged_with_its_exit_in_the_turn_record(self):  # D11, D29, S9
        def turn():
            lines = (self.folder / ".driver.log").read_text().splitlines()
            return [r for r in map(json.loads, lines) if r["type"] == "turn" and r.get("verbs")]

        self.assertTrue(wait_for(turn, 10))
        (record,) = turn()
        self.assertEqual([(v["verb"], v["exit"]) for v in record["verbs"]], [("reply", 0), ("reply", 0)])
        self.assertEqual(len(record["denied"]), 3)
        approvals = [r for r in self.driver_records("approval")]
        self.assertEqual([a["answer"] for a in approvals], ["allow_once", "allow_once", "deny", "deny", "deny"])
        self.assertEqual([a["reason"] for a in approvals[:2]], ["Approved page command"] * 2)

    def driver_records(self, kind):
        lines = (self.folder / ".driver.log").read_text().splitlines()
        return [r for r in map(json.loads, lines) if r["type"] == kind]

    def test_a_call_outside_the_form_is_denied_without_asking_the_user(self):  # S78
        answers = self.answers()
        for number in (2, 3, 4):
            with self.subTest(command=number):
                self.assertEqual(answers[number]["behavior"], "deny", answers[number])
                self.assertTrue(answers[number]["message"].startswith("not-the-approved-form:"), answers[number])
                self.assertIsNone(answers[number]["exit"])
        status, text = self.request("GET", "/agent", secret=self.secret)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(text)["approvals"], [], "no approval was raised on the page")
        self.assertNotIn("as the user", (self.folder / "conversation.jsonl").read_text())

    def test_the_page_agent_text_hands_the_header_form_to_workers_word_for_word(self):  # D29
        text = (ROOT / "src" / "better_ai" / "page" / "page-agent.md").read_text()
        self.assertIn("Approved without asking:", text)
        self.assertIn("word for word", text)


class LinkTest(Browser):
    def test_link_opens_a_newer_tab_and_the_old_one_is_refused_everywhere(self):  # S84, S85
        env = self.env(STUB_MODE="ask")
        old = self.pair(self.served(env=env))
        self.assertTrue(wait_for(lambda: json.loads(self.request("GET", "/agent", secret=old)[1])["approvals"], 20))
        approval = json.loads(self.request("GET", "/agent", secret=old)[1])["approvals"][0]
        done = self.link(env)
        self.assertEqual((done.returncode, done.stdout), (0, "link: on\n"), done.stdout + done.stderr)
        (new,) = self.browser_lines("secret")
        for method, path in (("GET", "/agent"), ("GET", "/data")):
            self.assertEqual(self.request(method, path, secret=old)[0], 403, path)
        answer = self.request("POST", "/rpc", rpc("permission_answer", {"id": approval["id"], "choice": "deny"}), old)
        self.assertEqual(answer[0], 403)
        self.assertEqual(json.loads(self.request("GET", "/agent", secret=new)[1])["approvals"][0]["id"], approval["id"])
        self.assertEqual(
            self.call(new, "permission_answer", {"id": approval["id"], "choice": "allow_once"})["result"], True
        )

    def test_a_link_that_cannot_open_a_tab_leaves_the_old_tab_working(self):  # S85
        old = self.pair(self.served(env=self.env("fail")))  # the server's launcher fails
        done = self.link(self.env("fail"))
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertEqual(self.request("GET", "/agent", secret=old)[0], 200)
        self.assertEqual(self.call(old, "agent_stop")["result"], True)

    def test_the_old_tab_shows_the_fixed_sentence(self):  # S84, D26
        source = (ROOT / "src" / "better_ai" / "page" / "page.js").read_text()
        self.assertIn(
            "This tab is no longer connected. Use the newer tab, or ask the agent in your chat to reopen the page.",
            source,
        )

    def test_serve_with_a_pairing_browser_prints_driver_on_and_pairs_once(self):
        # S76 itself (driver: on only after pairing) is checked in test_page_pairing_v2, with a browser that never loads.
        done = self.serve_in_browser(self.env())
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertRegex(done.stdout.splitlines()[0], rf"^driver: on claude {UUID}$")
        self.assertEqual(len(self.browser_lines("secret")), 1)


class ResendTest(Flow):
    def test_a_send_whose_reply_is_lost_and_is_sent_again_is_one_line_in_the_log(self):  # S127
        self.start()
        body = json.dumps(rpc("note", note("m-lost", "sent twice")))
        host = self.address().split("//")[1].rstrip("/")
        import http.client

        headers = {
            "Host": host,
            "Origin": f"http://{host}",
            "Sec-Fetch-Site": "same-origin",
            "X-Page-Token": self.secret,
            "Content-Type": "application/json",
        }
        lost = http.client.HTTPConnection(host, timeout=10)
        lost.request("POST", "/rpc", body, headers)
        lost.close()  # the tab never reads the answer
        time.sleep(0.5)
        status, text = self.request("POST", "/rpc", rpc("note", note("m-lost", "sent twice")), self.secret)
        self.assertEqual((status, json.loads(text)["result"]), (200, "saved"))
        lines = [json.loads(x) for x in (self.folder / "conversation.jsonl").read_text().splitlines()]
        self.assertEqual([x.get("id") for x in lines].count("m-lost"), 1)


if __name__ == "__main__":
    unittest.main()
