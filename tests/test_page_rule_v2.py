"""The shared page rule in the six page skills, their Missing capabilities, and the page-agent prompt."""

import re
import unittest
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
START = "IF you are in a session opened by the page"
WORDING = {
    "architect-better/modes/design.md": "## 2.",
    "code-better/modes/coordinate.md": "## 2. Start the builders",
    "design-better/SKILL.md": "### Show versions on one page",
    "discover-better/SKILL.md": "## General rules",
    "research-better/SKILL.md": "## General rules",
    "show-better/SKILL.md": "## 6. Work with the user in the page",
}
CLAUSES = (
    # the chat agent
    "RUN `python3 <skill dir>/scripts/better.pyz serve <unit>` in the background",
    "with the hand-off note on stdin",
    "the step you reached and what was agreed in the chat",
    "IF the unit already has a `.driver` file, PASS no hand-off note",
    "`driver: on`, SAY the page opened in the browser with its own agent, and END the turn",
    "`driver: on` and the word `already`, SEND the user to the open page",
    "RUN `python3 <skill dir>/scripts/better.pyz link <unit>` IF they ask for a new tab",
    "`driver: off`, or no `driver:` line comes within 40 seconds, SHOW the problem in one line",
    "FOLLOW the skill's Missing capabilities for a page that cannot be served",
    "AFTER the hand-off, DO NOT edit the unit, and WORK in a worktree",
    'ANSWER "ask it in the page"',
    # the session opened by the page
    "NEVER serve",
    "WRITE what a step says to say or ask in the chat as a `reply` in the page",
    "GIVE the skill's hand-back as one `reply` without `--to`",
    "LET the user accept only with Accept",
    "ASK them to press it WHEN they accept in words",
    "WHEN a step leads into a skill that serves its own page",
    "REPLY that the step starts from the user's chat, with what to ask there",
    "MARK the item `done`, and END the step",
)
# Named by the verb, the flag or the fallback text; not the English word.
GONE = (
    "--drive",
    "--open",
    "--timeout",
    "wait <",
    "`wait`",
    "better.pyz wait",
    "wait again",
    "wait fallback",
    "STREAM",
    '"sent"',
    "driver line",
    "enrollment",
    "start the live view themselves",
    "start the dashboard themselves",
)
MISSING = {
    "architect-better/SKILL.md": ("IF the page cannot be served, HOLD the conversation in the chat",),
    "discover-better/SKILL.md": ("IF the page cannot be served, HOLD the conversation in the chat",),
    "design-better/SKILL.md": (
        "IF the page cannot be served, PUBLISH the versions and GIVE the link",
        "RENDER them and GIVE the path",
        "MARK the work **not finished**",
    ),
    "code-better/SKILL.md": ("IF the page cannot be served, MARK the change **not finished**",),
    "show-better/SKILL.md": ("IF the page cannot be served, RENDER the slides as text",),
    "research-better/SKILL.md": (
        "IF the page cannot be served, REPORT progress in the chat",
        "without the live view",
    ),
}
# Every WAIT sentence of the skills outside the shared rule, as it was before the page protocol was revised.
WAIT_STEPS = Counter(
    """architect-better/modes/audit.md | WAIT for every report and HOLD the hand-back while reviewers run.
architect-better/modes/design.md | WAIT for the user's confirmation or correction and APPLY any corrections.
architect-better/modes/design.md | WAIT for every report.
architect-better/modes/design.md | WAIT for its report.
code-better/SKILL.md | WAIT until the verifier hands back its report.
code-better/modes/audit.md | WAIT until each reviewer hands back its report.
design-better/SKILL.md | WAIT for the user's decision.
design-better/modes/audit.md | WAIT until the reviewer hands back its report.
design-better/modes/design.md | WAIT for the answer, unless the request already gives it or says the user has none.
design-better/modes/design.md | WAIT for the user's decision.
design-better/modes/design.md | WAIT for the reviewer of step 1.
design-better/modes/design.md | WAIT for their answer before step 5, even when the request said to build, and DO NOT apply a fix they have not accepted.
design-better/modes/design.md | WAIT until the build is finished and its checks pass.
design-better/modes/design.md | WAIT until the reviewer hands back its report.
discover-better/SKILL.md | WAIT for the behaviour verifier's hand-back.
discover-better/SKILL.md | WAIT for the analysts' and the quote verifiers' hand-backs.
discover-better/SKILL.md | WAIT for the analysts' and the quote verifiers' hand-backs.
discover-better/SKILL.md | WAIT for the result: the analysts', the quote verifiers' and `/code-better`'s hand-backs, or the user's.
discover-better/SKILL.md | WAIT for checks at most 30 minutes, then go on, treating evidence still `checking` as not counting, and TELL the user.
research-better/SKILL.md | WAIT for them, then START the next group.
research-better/SKILL.md | WAIT for them, THEN SET the brief's `status` to `stopped`, before you present the findings.""".splitlines()
)


def read(name):
    return (SKILLS / name).read_text(encoding="utf-8")


def rule_blocks(name):
    return [block for block in read(name).split("\n\n") if block.startswith(START)]


def section(text, heading):
    level = heading.split(" ")[0]
    start = text.index(heading)
    rest = text[start + len(heading) :]
    end = re.search(rf"^#{{1,{len(level)}}} ", rest, re.M)
    return rest[: end.start()] if end else rest


class SharedRuleTest(unittest.TestCase):
    def rules(self):
        found = {}
        for name in WORDING:
            blocks = rule_blocks(name)
            self.assertEqual(len(blocks), 1, name)
            found[name] = blocks[0]
        return found

    def test_the_six_copies_are_identical_and_in_their_sections(self):
        rules = self.rules()
        self.assertEqual(len(set(rules.values())), 1)
        for name, heading in WORDING.items():
            with self.subTest(skill=name):
                text = read(name)
                self.assertLess(text.index(heading), text.index(rules[name]))

    def test_the_rule_holds_each_clause(self):
        rule = next(iter(self.rules().values()))
        for clause in CLAUSES:
            with self.subTest(clause=clause):
                self.assertIn(clause, rule)

    def test_the_rule_and_the_skills_hold_no_listening_text(self):
        for path in sorted(SKILLS.glob("**/*.md")):
            text = path.read_text(encoding="utf-8")
            for word in GONE:
                with self.subTest(file=str(path.relative_to(SKILLS)), word=word):
                    self.assertNotIn(word, text)

    def test_serve_appears_only_in_the_rule(self):
        for name in WORDING:
            with self.subTest(skill=name):
                text = read(name).replace(rule_blocks(name)[0], "")
                self.assertNotIn("better.pyz serve", text)
                self.assertNotIn("better.pyz link", text)
                self.assertNotIn("`driver: ", text)

    def test_the_rule_names_the_turn_header_words(self):
        rule = next(iter(self.rules().values()))
        prompt = (ROOT / "src/better_ai/page/page-agent.md").read_text(encoding="utf-8").lower().replace("`", "")
        for words in (
            "every word for the user through reply",
            "end the turn when the items are handled",
            "never serve",
        ):
            with self.subTest(words=words):
                self.assertIn(words, prompt)
        self.assertIn("NEVER serve", rule)

    def test_each_skill_says_what_to_do_for_a_page_that_cannot_be_served(self):
        for name, phrases in MISSING.items():
            with self.subTest(skill=name):
                text = (
                    section(read(name), "### Missing capabilities")
                    if "### Missing capabilities" in read(name)
                    else (section(read(name), "## 8. Missing capabilities"))
                )
                for phrase in phrases:
                    self.assertIn(phrase, text)

    def test_design_better_keeps_no_fallback_in_its_step(self):
        text = read("design-better/SKILL.md")
        step = section(text, "### Show versions on one page")
        self.assertNotIn("PUBLISH", step)
        self.assertNotIn("RENDER the page", step)

    def test_no_wait_step_changed(self):
        found = Counter()
        for path in sorted(SKILLS.glob("**/*.md")):
            for match in re.finditer(r"\bWAIT\b[^.\n]*\.", path.read_text(encoding="utf-8")):
                found[f"{path.relative_to(SKILLS).as_posix()} | {match.group(0)}"] += 1
        self.assertEqual(found, WAIT_STEPS)


class PageAgentPromptTest(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / "src/better_ai/page/page-agent.md").read_text(encoding="utf-8")
        self.sections = re.findall(r"^## (.+)$", self.text, re.M)

    def test_sections_and_frontmatter(self):
        self.assertEqual(self.sections, ["Input", "Messages", "Output"])
        head = re.match(r"---\n(.*?)\n---\n", self.text, re.S).group(1)
        self.assertEqual([line.partition(":")[0] for line in head.splitlines()][:2], ["name", "description"])
        self.assertEqual(
            [line.partition(":")[0] for line in head.splitlines()],
            ["name", "description", "capabilities", "edits", "model"],
        )

    def test_it_states_each_rule(self):
        text = " ".join(self.text.split())
        for rule in (
            "every word for the user through `reply`",
            "`--state asked`",
            "NEVER `serve`",
            "END the turn when the items are handled",
            "Once you start workers, END the turn",
            "LEAVE each item `done`, `asked` or `working` before the turn ends",
            "After a denial, DO NOT repeat the call",
            "ASK with `reply --state asked`",
            "After `not-the-approved-form`, RETRY once in the approved form",
            "RECORD the agreements of the hand-off note in the unit's records",
            "MARK item states as the skill's page rule says",
            "GIVE one line for each item, with its id and its state",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, text)

    def test_limits_on_replies_are_in_messages(self):
        messages = section(self.text, "## Messages")
        self.assertIn("ASK with `reply --state asked`", " ".join(messages.split()))
        self.assertIn("one or two short sentences", messages)
        self.assertNotIn("wait", self.text.lower().replace("awaiting", ""))

    def test_it_is_shipped_in_every_zipapp(self):
        prompt = (ROOT / "src/better_ai/page/page-agent.md").read_bytes()
        archives = sorted(SKILLS.glob("*/scripts/better.pyz"))
        self.assertTrue(archives)
        for archive in archives:
            with self.subTest(skill=archive.parent.parent.name), zipfile.ZipFile(archive) as contents:
                self.assertEqual(contents.read("better_ai/page/page-agent.md"), prompt)


if __name__ == "__main__":
    unittest.main()
