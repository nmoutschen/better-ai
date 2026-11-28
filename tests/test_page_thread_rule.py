"""The six page skills tell the agent the same four rules for the page's threads (PRINCIPLES 6.7), in the same words."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_FILES = [
    "skills/design-better/SKILL.md",
    "skills/show-better/SKILL.md",
    "skills/discover-better/SKILL.md",
    "skills/research-better/SKILL.md",
    "skills/architect-better/modes/design.md",
    "skills/code-better/modes/coordinate.md",
]
PREFIX = "python3 <skill dir>/scripts/better.pyz "
UNITS = [".design/<slug>", ".show/<slug>", "<board-path>", "<change folder>"]
RULES = [
    "TRACK each thread with `status <unit> seen|working <id> --read <n>`: `seen` when you read it, `working` only while you change something for it. PASS `--read <n>` to every `status` and `reply --to`: n is the read index of the last output you read, the `_i` of the last line `wait` or `serve` printed, or the number on the last line of `pending`. IF the command refuses because the user wrote in the thread since, READ what they wrote, THEN send it again.",
    "REPLY in the user's thread, under the item you answer, with `reply <unit> --to <id> --read <n>`, your words on stdin, in one or two short sentences. The reply sets the thread's state: `done` by default, `--state asked` when you ask the user something about it, `--state working` when you reply before you have made the change. ONCE an answer leads to a change, REPLY done, THEN ASK any next question about it in the same thread, with `reply <unit> --to <id> --read <n> --state asked`.",
    "ASK one question per message. POST a message without `--to` only to start a new subject: with `--state asked` when it is a question, without `--state` when it is a report, which needs no answer.",
    "The user closes a thread with ✓. A thread you replied done stays in the user's Open list until they close it. Any message from the user in a thread gives it back to you: READ it as part of that thread.",
]
FORBIDDEN = ["in a new message", "no `--to`"]


def normal(text: str) -> str:
    text = text.replace(PREFIX, "")
    for unit in UNITS:
        text = text.replace(unit, "<unit>")
    return re.sub(r"\s+", " ", text)


class PageThreadRule(unittest.TestCase):
    def test_each_skill_has_the_four_rules(self):
        for name in SKILL_FILES + ["PRINCIPLES.md"]:
            text = normal((ROOT / name).read_text())
            for rule in RULES:
                self.assertIn(rule, text, name)

    def test_no_text_sends_a_question_outside_the_thread(self):
        for name in SKILL_FILES + ["PRINCIPLES.md"]:
            text = (ROOT / name).read_text()
            for bad in FORBIDDEN:
                self.assertNotIn(bad, text, name)

    def test_every_ask_names_the_thread(self):
        # An ASK about a note under an item goes back in that thread, never in a message of its own.
        for name in SKILL_FILES:
            for line in (ROOT / name).read_text().splitlines():
                if "ASK in one sentence" in line:
                    self.assertIn("--to <id> --state asked", normal(line), name)

    def test_acceptance_in_words_gives_the_command(self):
        for name in SKILL_FILES:
            for line in (ROOT / name).read_text().splitlines():
                if "accept a thread in words" in line:
                    self.assertIn("accepted <id>... --text", normal(line), name)

    def test_every_status_and_reply_to_command_passes_read(self):
        # Without --read the CLI refuses them (D12): every command the agent is told to run carries it.
        for name in SKILL_FILES + ["PRINCIPLES.md"]:
            for command in re.findall(r"`((?:status|reply) <unit> [^`]*)`", normal((ROOT / name).read_text())):
                if command.startswith("reply") and "--to" not in command or " accepted " in command:
                    continue  # a new subject, or the user's acceptance in words
                self.assertIn("--read <n>", command, name)

    def test_status_lists_do_not_include_asked(self):
        for name in SKILL_FILES:
            self.assertNotRegex((ROOT / name).read_text(), r"seen\|asked|asked\|working")


if __name__ == "__main__":
    unittest.main()
