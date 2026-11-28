"""The driver's item selection and the fallback commands read the same conversation states."""

import json
import os
import random
from unittest import mock

import test_page_shell as shell


def note(item, *, to=None):
    return {"type": "note", "id": item, "to": to, "by": "user", "text": item}


def status(item, state):
    return {"type": "status", "to": item, "by": "coordinator", "status": state}


def user_writes(log, thread):
    """The lines of the user's writes in THREAD (page `threads`): what the agent must be shown before a read covers it."""
    lines = {id(e): n for n, e in enumerate(log)}
    return [lines[id(m)] for m in thread["messages"] if m.get("by") == "user"]


def read_so_far(log):
    """The highest read the agent has written in a status: what it has read of the log."""
    return max([-1, *(e["read"] for e in log if e.get("type") == "status" and isinstance(e.get("read"), int))])


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


class ReadTest(shell.Fixture):
    """A --read the agent is given never covers a user write it was not shown (thread.tla A2): the turn prompt and
    pending in a page session give the line before the first write in a thread the batch does not show."""

    def setUp(self):
        super().setUp()
        self.conv = shell.page.Conversation(self.unit(), self.spec, self.docs)

    def test_a_batch_that_leaves_a_thread_out_reads_up_to_the_line_before_its_write(self):
        self.seed(note("m1"), note("m2"), note("m3"))
        batch = self.conv.delivery()
        self.assertEqual(batch.read, 2)
        batch.items[:] = [item for item in batch.items if item["id"] != "m2"]  # the driver did not admit m2
        self.assertEqual(batch.read, 0)
        self.assertEqual(batch.lines()[-1], "2 not done. Pass --read 0 to status and reply.")

    def test_pending_in_a_session_does_not_read_past_a_thread_the_turn_did_not_carry(self):
        self.seed(note("m1"))
        (self.unit_dir / ".page-delivery").write_text(
            json.dumps({"session": "live", "position": 1, "item_ids": ["m1"], "actions": []})
        )
        self.seed(note("m2"), note("m1-more", to="m1"))  # a new thread, then a write in the turn's own thread
        with mock.patch.dict(os.environ, {"BETTER_PAGE_SESSION": "live"}):
            code, out, err = self.cli("pending", self.unit_arg)
        self.assertEqual((code, err), (0, ""))
        lines = out.splitlines()
        self.assertEqual([json.loads(line)["id"] for line in lines[:-1]], ["m1"])
        self.assertEqual(lines[-1], "1 not done. Pass --read 0 to status and reply.")
        found = {t["id"]: (t["state"], t["step"]) for t in shell.page.threads(self.log(), self.conv.items)}
        self.assertEqual(found["m2"], ("agent", "new"))

    def test_seeded_interleavings_give_no_read_past_an_unshown_write_and_no_false_seen(self):
        """For random interleavings of user writes and agent turns, each through the turn prompt (with some items not
        admitted) or pending in the turn's session: no read the agent is given covers a user write it was not shown in
        a thread the user has not closed, and no thread shows seen or working for a write the agent was not shown
        (thread.tla NoLostWrite, SeenIsTrue)."""
        path, active = self.unit_dir / "conversation.jsonl", self.unit_dir / ".page-delivery"
        for seed in range(60):
            with self.subTest(seed=seed):
                path.unlink(missing_ok=True)
                active.unlink(missing_ok=True)
                rng, ids, turn, shown = random.Random(seed), [], None, set()
                for step in range(rng.randint(6, 18)):
                    act = rng.choice(("new", "new", "note", "note", "accept", "reopen", "turn", "turn", "session"))
                    if act == "new" or (not ids and act in ("note", "accept", "reopen")):
                        ids.append(f"m{len(ids)}")
                        self.seed(note(ids[-1]))
                    elif act == "note":
                        self.seed(note(f"x{step}", to=rng.choice(ids)))
                    elif act in ("accept", "reopen"):
                        self.seed({"type": act, "to": rng.choice(ids), "by": "user"})
                    elif act == "turn":
                        batch = self.conv.delivery(rng.randint(0, len(self.log())))
                        batch.items[:] = [item for item in batch.items if rng.random() < 0.6]  # some not admitted
                        turn = {"session": "live", "position": batch.position, "actions": []}
                        turn["item_ids"] = sorted(item["id"] for item in batch.items)
                        self.agent_acts(batch, rng, shown)
                    elif turn is not None:
                        active.write_text(json.dumps(turn))
                        with mock.patch.dict(os.environ, {"BETTER_PAGE_SESSION": "live"}):
                            batch = shell.page._active_batch(self.conv, turn)
                        self.agent_acts(batch, rng, shown)
                    for t in shell.page.threads(self.conv.events(), self.conv.items):
                        if t["state"] == "agent" and (t["id"], t["user_at"]) not in shown:
                            self.assertEqual(t["step"], "new", (seed, step, t["id"], self.log()))

    def agent_acts(self, batch, rng, shown):
        """The agent is given BATCH: check its read, note what it was shown, then mark some of its items."""
        log = self.conv.events()
        before, kept = read_so_far(log), {item["id"] for item in batch.items}
        for t in shell.page.threads(log, self.conv.items):
            if t["id"] in kept:
                shown.update((t["id"], line) for line in user_writes(log, t))
            elif not t["closed_by_user"] and not t["deleted"]:
                for line in user_writes(log, t):
                    if line <= batch.read:
                        self.assertTrue(line <= before or (t["id"], line) in shown, (t["id"], line, batch.read, log))
        if batch.read < 0:
            return
        for ident in sorted(kept):
            if rng.random() < 0.7:
                try:
                    read = self.conv.unread(log, [ident], batch.read, "status")
                except shell.paths.Refused:
                    continue
                state = rng.choice(("seen", "working", "done", "asked"))
                self.conv.write({"type": "status", "by": "coordinator", "to": ident, "status": state, "read": read})

    def test_the_turn_prompt_does_not_read_past_a_write_the_driver_did_not_admit(self):
        from test_page_driver import Event, Peer, eventually

        from better_ai.page.driver import Driver

        self.seed(note("m0"))
        peer = Peer()
        driver = Driver(
            self.conv,
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
        self.seed(note("unadmitted"))  # in the log, never enqueued: the driver does not carry it
        later = note("m1")
        self.seed(later)
        driver.enqueue(later)
        peer.events.put(Event("turn_ended", outcome="completed"))
        eventually(lambda: len(peer.prompts) == 2)
        line = next(n for n, e in enumerate(self.log()) if e["id"] == "unadmitted")
        self.assertIn('"id": "m1"', peer.prompts[1])
        self.assertNotIn('"id": "unadmitted"', peer.prompts[1])
        last = peer.prompts[1].split("Pass --read ")[1].split(" ")[0]
        self.assertLess(int(last), line, peer.prompts[1])


class AnsweredTest(shell.Fixture):
    def test_a_note_the_agent_read_and_answered_is_not_delivered_again(self):
        """A user note the agent read through pending and answered (a later status in its thread whose read covers it)
        is not an event of a later turn; one it has not read still is."""
        conv = shell.page.Conversation(self.unit(), self.spec, self.docs)
        self.seed(
            note("m1"),
            note("r1"),
            note("m1-more", to="m1"),
            note("r1-more", to="r1"),
            {"type": "reply", "by": "coordinator", "id": "a1", "to": "m1", "text": "Done."},
            {**status("m1", "done"), "read": 2},
            {**status("r1", "seen"), "read": 2},  # read before r1-more: it has not read it
        )
        batch = conv.delivery(after=2)
        self.assertEqual([e["id"] for e in batch.events], ["r1-more"])
