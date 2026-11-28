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

    def test_prompt_uses_full_items_through_twenty_then_ids_only(self):
        self.conv = shell.page.Conversation(self.unit(), self.spec, self.docs)
        self.seed(*(note(f"m{n}") for n in range(20)))
        result = self.conv.delivery()
        self.assertEqual(result.prompt_items(), result.items)
        self.seed(*(note(f"m{n}") for n in range(20, 25)))
        result = self.conv.delivery()
        self.assertEqual(result.prompt_items(), [{"id": f"m{n}"} for n in range(25)])
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
        self.assertEqual((code, out, err), (0, "0 not done. Pass --read 3 to status and reply.\n", ""))

    def test_driver_pending_keeps_exact_turn_after_late_user_input(self):
        from test_page_driver import Peer

        from better_ai.page.driver import Driver

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
        driver.tab_paired()
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
        records = [{k: v for k, v in r.items() if k != "since"} for r in map(json.loads, out.splitlines()[:-1])]
        expected = [{**item, "status": {0: "working", 1: "seen"}.get(n, "new")} for n, item in enumerate(sent[:-1])]
        # The turn keeps its items, and m21, sent since, stays for a later turn. The user's writes since in the turn's
        # own threads are shown, with a --read that covers them, as a --read before them is refused (D12): the agent
        # sent here by that refusal reads them, then sends again. A note sent again keeps its first text (page
        # `threads`: only a comment is edited).
        answer = self.log()[len(sent) + 2]
        thread = [{"from": "user", "at": answer["at"], "text": "later-answer", "id": "later-answer"}]
        expected[0] = {**expected[0], "thread": thread}
        self.assertEqual(records, [*expected, sent[-1]])
        self.assertEqual(out.splitlines()[-1], f"21 not done. Pass --read {len(sent) + 2} to status and reply.")

    def test_an_rpc_edit_reaches_pending_only_while_the_item_is_not_settled(self):
        _, host = self.serve()
        states = ["working", "asked", "done", "accepted"]
        for number, state in enumerate([*states, "stale"], 1):
            self.assertEqual(
                self.rpc(host, "comment", {"id": f"c{number}", "n": number, "on": {}, "text": state}).get("result"),
                "saved",
            )
        for number, state in enumerate([*states, "working"], 1):
            read = ["--read", str(len(self.log()) - 1)] if state != "accepted" else []  # what the agent read (D12)
            self.assertEqual(
                self.cli("status", self.unit_arg, state, f"c{number}", "--text", *read, stdin="Agreed")[0], 0
            )
        for number, state in enumerate(states, 1):
            self.assertEqual(
                self.rpc(host, "comment", {"id": f"c{number}", "n": number, "on": {}, "text": f"edited {state}"}).get(
                    "result"
                ),
                "saved",
            )
        # An edit of a working item is delivered; one of an asked, done or accepted item is not (S15, S58).
        code, out, err = self.cli("pending", self.unit_arg)
        self.assertEqual((code, err), (0, ""))
        lines = out.splitlines()[:-1]
        self.assertEqual(
            [(item["id"], item["status"], item["text"]) for item in map(json.loads, lines)],
            [("c1", "working", "edited working")],
        )
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
