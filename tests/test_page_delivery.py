"""The driver's item selection and the fallback commands read the same conversation states."""

import json
import os
from unittest import mock

import test_page_shell as shell


def note(item, *, to=None):
    return {"type": "note", "id": item, "to": to, "by": "user", "text": item}


def status(item, state):
    return {"type": "status", "to": item, "by": "coordinator", "status": state}


class DeliveryTest(shell.Fixture):
    def test_normal_and_abnormal_carry_only_items_from_the_named_turn(self):
        self.conv = shell.page.Conversation(self.unit(), self.spec, self.docs)
        self.seed(
            note("fresh"),
            note("seen-normal"),
            status("seen-normal", "seen"),
            note("seen-abnormal"),
            status("seen-abnormal", "seen"),
            note("working-normal"),
            status("working-normal", "working"),
            note("working-abnormal"),
            status("working-abnormal", "working"),
            note("asked"),
            status("asked", "asked"),
            note("done"),
            status("done", "done"),
            note("accepted"),
            {"type": "accept", "to": "accepted", "by": "user"},
            note("unrelated"),
            status("unrelated", "seen"),
        )
        result = self.conv.delivery(
            after=13,
            carry_ids={"seen-normal", "working-normal"},
            recover_ids={"seen-abnormal", "working-abnormal", "asked", "done", "accepted"},
        )
        self.assertEqual(
            [(item["id"], item["status"]) for item in result.items],
            [("fresh", "new"), ("seen-normal", "seen"), ("seen-abnormal", "seen"), ("working-abnormal", "working")],
        )
        self.assertEqual([(event["type"], event["to"]) for event in result.events], [("accept", "accepted")])
        self.assertEqual(result.position, 17)

    def test_prompt_uses_full_items_through_twenty_then_ids_and_states(self):
        self.conv = shell.page.Conversation(self.unit(), self.spec, self.docs)
        self.seed(*(note(f"m{n}") for n in range(20)))
        result = self.conv.delivery()
        self.assertEqual(result.prompt_items(), result.items)
        self.seed(*(note(f"m{n}") for n in range(20, 25)))
        result = self.conv.delivery()
        self.assertEqual(result.prompt_items(), [{"id": f"m{n}", "status": "new"} for n in range(25)])
        self.assertEqual(len(result.items), 25)

    def test_pending_for_driven_turn_uses_matching_active_batch(self):
        self.seed(note("m1"), status("m1", "working"), note("m2"), status("m2", "seen"))
        (self.unit_dir / ".page-delivery").write_text(
            json.dumps({"session": "live", "after": 0, "carry_ids": ["m2"], "recover_ids": ["m1"]})
        )
        with mock.patch.dict(os.environ, {"BETTER_PAGE_SESSION": "live"}):
            code, out, err = self.cli("pending", self.unit_arg)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(
            [(item["id"], item["status"]) for item in map(json.loads, out.splitlines()[:-1])],
            [("m1", "working"), ("m2", "seen")],
        )
        with mock.patch.dict(os.environ, {"BETTER_PAGE_SESSION": "unrelated"}):
            code, out, err = self.cli("pending", self.unit_arg)
        self.assertEqual((code, out, err), (0, "0 not done.\n", ""))

    def test_driver_pending_keeps_exact_turn_after_late_user_input(self):
        from better_ai.page.driver import Driver
        from test_page_driver import Peer

        initial_action = {"type": "accept", "to": "earlier", "by": "user"}
        self.seed(*(note(f"m{n}") for n in range(21)), initial_action)
        sent = self.log()
        peer = Peer()
        driver = Driver(
            shell.page.Conversation(self.unit(), self.spec, self.docs),
            "stub",
            lambda *_: peer,
            skill_path="SKILL.md",
            command="better.pyz",
            cwd=self.unit_dir,
            valid_session=lambda key: key == "session-1",
        )
        self.addCleanup(driver.close)
        driver.start()
        self.assertTrue(peer.prompt_arrived.wait(2))
        self.seed(
            note("m21"),
            {**note("m0"), "text": "later edit"},
            note("later-answer", to="m0"),
            {"type": "reopen", "to": "earlier", "by": "user"},
            status("m0", "working"),
            status("m1", "seen"),
        )
        with mock.patch.dict(os.environ, {"BETTER_PAGE_SESSION": driver.tag}):
            code, out, err = self.cli("pending", self.unit_arg)
        self.assertEqual((code, err), (0, ""))
        records = list(map(json.loads, out.splitlines()[:-1]))
        expected = [{**item, "status": {0: "working", 1: "seen"}.get(n, "new")} for n, item in enumerate(sent[:-1])]
        self.assertEqual(records, [*expected, sent[-1]])

    def test_wait_ignores_legacy_cursor_and_keeps_an_action_for_resume(self):
        self.serve()
        self.seed(note("m1"), status("m1", "done"), {"type": "reopen", "to": "m1", "by": "user", "text": "again"})
        legacy = self.unit_dir / ".conversation-seen"
        legacy.write_text("9000")
        code, out, err = self.cli("wait", self.unit_arg, "--timeout", "1")
        self.assertEqual((code, err), (0, ""))
        item, event = map(json.loads, out.splitlines())
        self.assertEqual((item["id"], item["status"]), ("m1", "reopened"))
        self.assertEqual((event["type"], event["to"]), ("reopen", "m1"))
        self.assertEqual(legacy.read_text(), "9000")
        self.seed(status("m1", "seen"))
        code, _, _ = self.cli("wait", self.unit_arg, "--timeout", "1")
        self.assertEqual(code, 3)
        code, out, err = self.cli("pending", self.unit_arg)
        self.assertEqual((code, err), (0, ""))
        item, event = map(json.loads, out.splitlines()[:-1])
        self.assertEqual((item["id"], item["status"]), ("m1", "seen"))
        self.assertEqual((event["type"], event["to"]), ("reopen", "m1"))

    def test_rpc_edits_to_excluded_states_reach_pending_and_wait_with_their_state(self):
        _, host = self.serve()
        states = ["working", "asked", "done", "accepted"]
        for number, state in enumerate([*states, "stale"], 1):
            self.assertEqual(
                self.rpc(host, "comment", {"id": f"c{number}", "n": number, "on": {}, "text": state}).get("result"),
                "saved",
            )
        self.assertEqual(self.cli("wait", self.unit_arg, "--timeout", "1")[0], 0)
        for number, state in enumerate([*states, "working"], 1):
            self.assertEqual(self.cli("status", self.unit_arg, state, f"c{number}", "--text", stdin="Agreed")[0], 0)
        for number, state in enumerate(states, 1):
            self.assertEqual(
                self.rpc(host, "comment", {"id": f"c{number}", "n": number, "on": {}, "text": f"edited {state}"}).get(
                    "result"
                ),
                "saved",
            )
        expected = [(f"c{number}", state, f"edited {state}") for number, state in enumerate(states, 1)]
        for verb, args in (("pending", ()), ("wait", ("--timeout", "1"))):
            with self.subTest(verb=verb):
                code, out, err = self.cli(verb, self.unit_arg, *args)
                self.assertEqual((code, err), (0, ""))
                lines = out.splitlines()
                if verb == "pending":
                    lines = lines[:-1]
                self.assertEqual(
                    [(item["id"], item["status"], item["text"]) for item in map(json.loads, lines)], expected
                )
        self.assertEqual(self.cli("wait", self.unit_arg, "--timeout", "1")[0], 3)
        self.assertEqual(self.conv.delivery(after=len(self.log())).items, [])

    def test_pending_reads_all_sent_ids_once_active_prompt_items_are_seen(self):
        self.conv = shell.page.Conversation(self.unit(), self.spec, self.docs)
        self.seed(note("unrelated"), status("unrelated", "seen"), *(note(f"m{n}") for n in range(25)))
        batch = self.conv.delivery()
        (self.unit_dir / ".page-delivery").write_text(
            json.dumps({"session": "live", "after": 0, "item_ids": [item["id"] for item in batch.prompt_items()]})
        )
        self.seed(*(status(f"m{n}", "seen") for n in range(25)))
        with mock.patch.dict(os.environ, {"BETTER_PAGE_SESSION": "live"}):
            code, out, err = self.cli("pending", self.unit_arg)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(
            [(item["id"], item["status"], item["text"]) for item in map(json.loads, out.splitlines()[:-1])],
            [(f"m{n}", "seen", f"m{n}") for n in range(25)],
        )
        self.assertEqual(self.conv.delivery(after=batch.position).items, [])
