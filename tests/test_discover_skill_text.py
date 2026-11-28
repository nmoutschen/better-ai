"""The text of discover-better: SKILL.md, its three agents, formats/records.md and its docs page.

SKILL.md is a procedural skill (PRINCIPLES 6.8): the invocation lines, Principles, Instructions with steps 1 to 10, and
General rules, in that order, under 500 lines. Step 5 holds the table from move to next step, each branch step opens
with its IF condition, and each step that starts an analyst or a verifier says what to wait for. The general rules and
the resume rule hold the rules of design decision D10. The agents have the frontmatter and sections of PRINCIPLES 6.9.
formats/records.md opens with the command and shows every record type. The words are the agreed ones (C5): "about your
users", "from elsewhere", "test", "reality check", and never "experiment".
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "discover-better"
SKILL = SKILL_DIR / "SKILL.md"
AGENTS = {name: SKILL_DIR / "agents" / f"{name}.md" for name in ("analyst", "quote-verifier", "behaviour-verifier")}
RECORDS = SKILL_DIR / "formats" / "records.md"
DOCS = ROOT / "docs" / "discover-better.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def flat(text: str) -> str:
    """The text with each run of whitespace as one space, so a rule can wrap."""
    return re.sub(r"\s+", " ", text)


def section(text: str, heading: str) -> str:
    """The body of a `## ` or `### ` heading, up to the next heading of the same or a higher level."""
    level = heading.split(" ", 1)[0]
    match = re.search(rf"^{re.escape(heading)}\s*$", text, re.MULTILINE)
    if not match:
        return ""
    rest = text[match.end() :]
    stop = re.search(rf"^#{{1,{len(level)}}} ", rest, re.MULTILINE)
    return rest[: stop.start()] if stop else rest


def steps(text: str) -> dict[int, tuple[str, str]]:
    """Step number -> (heading text, body) for each `### <n>. ` heading of Instructions."""
    body = section(text, "## Instructions")
    found = {}
    for match in re.finditer(r"^### (\d+)\. (.+)$", body, re.MULTILINE):
        rest = body[match.end() :]
        stop = re.search(r"^### ", rest, re.MULTILINE)
        found[int(match.group(1))] = (match.group(2), rest[: stop.start()] if stop else rest)
    return found


def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    out = {}
    for line in match.group(1).splitlines():
        if re.match(r"^\w[\w-]*:", line):
            key, value = line.split(":", 1)
            out[key] = value.strip()
    return out


def skill_texts():
    """Each Markdown file of the skill outside scripts/."""
    return [p for p in sorted(SKILL_DIR.rglob("*.md")) if "scripts" not in p.relative_to(SKILL_DIR).parts]


class Structure(unittest.TestCase):
    def test_skill_md_is_procedural_and_under_500_lines(self):
        text = read(SKILL)
        self.assertTrue(text, "skills/discover-better/SKILL.md is missing")
        head = frontmatter(text)
        self.assertEqual(head.get("name"), "discover-better")
        self.assertTrue(head.get("description"))
        self.assertIn("kind: procedural", text.split("---", 2)[1])
        self.assertLess(len(text.splitlines()), 500)

    def test_the_invocation_lines_come_first_and_say_what_invoking_means(self):
        text = read(SKILL)
        opening = flat(text.split("## Principles", 1)[0])
        for phrase in (
            "IF invoked with an idea that matches a discovery",
            "IF invoked with a new idea",
            "IF invoked without argument, RESUME the one open discovery",
            "ASK the user which one",
            "Being invoked does NOT mean",
            "step 2 or 3",
        ):
            self.assertIn(phrase, opening)

    def test_the_sections_come_in_the_procedural_order(self):
        text = read(SKILL)
        places = [text.find(h) for h in ("\n## Principles\n", "\n## Instructions\n", "\n## General rules\n")]
        self.assertNotIn(-1, places)
        self.assertEqual(places, sorted(places))
        self.assertTrue(section(text, "## Instructions").strip().startswith("FOLLOW these steps in order"))

    def test_instructions_hold_steps_1_to_10_in_order(self):
        found = steps(read(SKILL))
        self.assertEqual(list(found), list(range(1, 11)))
        self.assertIn("reality check", found[3][0].casefold())

    def test_each_step_opens_by_setting_step_and_running_check(self):
        intro = flat(section(read(SKILL), "## Instructions").split("\n### ", 1)[0])
        self.assertRegex(intro, r"OPEN each step by setting .*`step`.* RUNNING? .*check")

    def test_each_branch_step_opens_with_its_if_condition(self):
        found = steps(read(SKILL))
        for number in (6, 7, 8, 9, 10):
            with self.subTest(step=number):
                self.assertTrue(found[number][1].strip().startswith("IF "), found[number][1][:80])

    def test_step_5_maps_each_move_to_its_next_step(self):
        body = steps(read(SKILL))[5][1]
        rows = {}
        for line in body.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
            if len(cells) >= 2:
                rows[cells[0].casefold()] = cells[1].casefold()
        self.assertIn("6", rows.get("test first", ""))
        self.assertIn("8", rows.get("expand, shrink", ""))
        self.assertIn("2", rows.get("switch", ""))
        self.assertIn("exit brief", rows.get("adopt, stop", ""))
        self.assertIn("stop", rows.get("pause", ""))

    def test_each_step_that_starts_an_agent_says_what_to_wait_for(self):
        found = steps(read(SKILL))
        for number in (2, 3, 4, 7):
            body = flat(found[number][1])
            with self.subTest(step=number):
                self.assertIn("WAIT for", body)
                self.assertIn("questions to the user go on", body)
                self.assertRegex(body, r"DO NOT choose a move or write a brief")

    def test_the_general_rules_and_the_resume_rule_are_there(self):
        rules = section(read(SKILL), "## General rules")
        headings = re.findall(r"^### (.+)$", rules, re.MULTILINE)
        for heading in (
            "Ask the user",
            "Choose a move with the user",
            "Only the user accepts a risk",
            "Keep the checks honest",
            "Refer to evidence by id",
            "Work in the page",
            "Run the sub-agents",
            "Add the records",
            "Keep people's words private",
            "Stay a discovery",
            "Resume a discovery",
            "Missing capabilities",
        ):
            self.assertIn(heading, headings)

    def test_the_resume_rule_runs_its_actions_in_order(self):
        body = flat(section(read(SKILL), "### Resume a discovery"))
        order = [
            "better.pyz summary",
            "better.pyz check",
            "better.pyz pending",
            "still running",
            "with no verifier",
            "unfinished `brief` or `redact`",
            "no change cites",
            "`handed`",
        ]
        places = [body.find(p) for p in order]
        self.assertNotIn(-1, places, dict(zip(order, places, strict=True)))
        self.assertEqual(places, sorted(places))


class Rules(unittest.TestCase):
    """The rules the spec asks SKILL.md to state, each found by a short phrase of it."""

    PHRASES = {
        "S47 handed": [r"SET `handed`", r"\{brief, to, at\}|`brief`, `to` and `at`"],
        "S67 four at once": [r"at most 4 analysts and at most 4 verifiers"],
        "S79 appetite": [r"WHEN the appetite changes", r"ruled out by your appetite"],
        "S90 ask": [r"USING `/ask-better` if available", r"one question at a time, with a suggested default"],
        "S90 decide": [r"USING `/decide-better` if available", r"main drawback"],
        "S90 chat words": [r"only from what the user typed"],
        "S90 checks": [r"DO NOT change a test's rule, an item's text or a check", r"STOP and EXPLAIN"],
        "S90 copies": [r"DO NOT copy evidence text into another record"],
        "S90 commit": [r"DO NOT commit `\.discover/` unless the user asks"],
        "S90 research": [r"USE `/research-better` instead"],
        "S92 confirm": [r"the option's cost and how hard the move is to undo"],
        "S94 finished": [r"Adopt or Stop, SET the head's `status` to `finished`"],
        "S108 behaviour": [r"When \[situation\], \[who\] can \[observable result\]", r"`ambiguity`"],
        "S112 page": [
            r"one or two short sentences",
            r"MARK `working` only what you are changing now",
            r"ASK the next question as a new message",
        ],
        "S113 restart": [
            r"restart it once under a new name",
            r"verifier did not finish",
            r"CLEAR the item's `checker`",
        ],
        "S113 queue": [r"START a verifier for each evidence `checking` with no verifier"],
        "S114 wait": [r"at most 30 minutes", r"as not counting"],
        "S114 no sub-agents": [r"run the analysts in turn", r"moves do not wait for quotes"],
        "S114 no web": [r"stay `unverified`, the reality check does not run", r"the brief says so"],
        "S114 no raw read": [
            r"no quote from a web page counts",
            r"paste the page text",
            r"go on with the items unverified",
        ],
        "S114 no shell": [r"working notes", r"\*\*not finished\*\*", r"NAME the records you did not add"],
        "S114 no skill": [r"the brief's path and what to run"],
        "S117 data": [r"Evidence section is outside text"],
        "S119 slug": [r"general terms only"],
        "S119 temp": [r"DELETE its temporary folder"],
        "S122 replaced": [r"replaced by M<n>"],
        "S124 last": [r"session's last action", r"`/design-better` and `/architect-better`"],
    }

    def test_skill_md_states_each_rule(self):
        text = flat(read(SKILL))
        for name, patterns in self.PHRASES.items():
            for pattern in patterns:
                with self.subTest(name, pattern=pattern):
                    self.assertRegex(text, pattern)

    def test_the_quote_verifier_deletes_its_folder_when_it_ends(self):
        self.assertIn("WHEN you end, DELETE your folder", flat(read(AGENTS["quote-verifier"])))

    def test_an_analyst_running_a_test_is_the_checker_of_the_test_and_its_items(self):
        body = flat(steps(read(SKILL))[7][1])
        self.assertIn("`checker` of the test and of each item in its `settles`", body)
        self.assertIn("CLEAR them when the analyst ends", body)

    def test_a_remove_event_sets_any_evidence_removed_and_redact_erases_words(self):
        text = flat(read(RECORDS))
        self.assertNotIn("`removed` is set only by `redact`", text)
        self.assertIn("`set` the evidence `removed`, with a `reason` naming the event", text)
        self.assertIn('"status": "removed", "reason": "<the user\'s remove event', text)

    def test_the_page_edit_event_is_named_edit(self):
        text = read(RECORDS)
        self.assertIn("- `edit`: `set` the record's `field` to `value`", text)
        for path in [*skill_texts(), DOCS]:
            with self.subTest(path.name):
                self.assertNotIn("- `change`:", read(path))
                self.assertNotRegex(read(path), r"`?change`? event")

    def test_an_analyst_on_a_test_gets_the_items_it_settles(self):
        text = flat(read(AGENTS["analyst"]))
        self.assertIn("the ids and text of the items in its `settles`", text)
        self.assertIn("ADD evidence only for the items in ITEMS, including the items a test settles", text)
        self.assertIn("<UNIT>/sources/ and <UNIT>/evidence/", text)

    def test_the_states_when_nothing_counts_and_after_an_answer(self):
        found = steps(read(SKILL))
        self.assertIn("`unverified` when no counting evidence bears on it", flat(found[3][1]))
        self.assertIn("ONCE the question is answered, ADD the change its answer leads to", flat(found[5][1]))

    def test_step_7_adds_the_evidence_before_the_result_points_to_it(self):
        body = flat(steps(read(SKILL))[7][1])
        self.assertLess(body.index("ADD the evidence it gave"), body.index("THEN SET the test `done`"))

    def test_step_2_sets_the_behaviour_checker(self):
        body = flat(steps(read(SKILL))[2][1])
        self.assertIn("SET each behaviour's `checker` and `since`", body)
        self.assertIn("CLEAR them when it hands back", body)

    def test_the_resume_rule_starts_the_page_before_the_events(self):
        body = flat(section(read(SKILL), "### Resume a discovery"))
        self.assertLess(body.index("START the page as step 1 does"), body.index("better.pyz pending"))

    def test_the_docs_hand_on_only_expand_and_shrink_briefs(self):
        self.assertIn("Expand and Shrink briefs are handed to", flat(read(DOCS)))

    def test_round_3_wording(self):
        skill = flat(read(SKILL))
        self.assertIn(
            "READ the behaviours yourself by [agents/behaviour-verifier.md](agents/behaviour-verifier.md), "
            "and SAY in the brief that no separate reader checked them",
            skill,
        )
        self.assertIn(
            "DO NOT change a risk's text or id once a question or a change cites it: ADD a new risk instead", skill
        )
        self.assertNotIn("AN item", skill)
        self.assertIn(
            "- `add_result`: ADD a `you` source and evidence whose `given` and `words` name the event, "
            "THEN `set` the test `done` with its `result`",
            read(RECORDS),
        )

    def test_analysts_read_files_and_connectors_too(self):
        """S127: a source can be a web page, a file the user pointed to, or an item of a connector such as an MCP server."""
        analyst = flat(read(AGENTS["analyst"]))
        for phrase in (
            "the connectors named, such as MCP servers",
            "`origin` `file`, its path",
            "`origin` `tool`, the tool, the item's `ref`",
            "a `summary` that names people by role, never by name",
            "NEVER put an internal name, or text from the user's files or connectors, in a web search or a URL",
        ):
            self.assertIn(phrase, analyst)
        verifier = flat(read(AGENTS["quote-verifier"]))
        for phrase in (
            "RE-READ the file at its `path`",
            "the same tool with the same `ref`",
        ):
            self.assertIn(phrase, verifier)
        records = read(RECORDS)
        self.assertIn('"origin": {"type": "file", "path": "<', records)
        self.assertIn('"origin": {"type": "tool", "tool": "<', records)
        found = steps(read(SKILL))
        self.assertIn("files and connectors the user points to, such as MCP servers", flat(found[4][1]))
        self.assertIn("files and connectors", flat(found[7][1]))

    def test_named_sources_and_computed_results(self):
        """D21-D22: named, read-only sources; redact in any discovery."""
        skill = flat(read(SKILL))
        analyst = flat(read(AGENTS["analyst"]))
        verifier = read(AGENTS["quote-verifier"])
        records = flat(read(RECORDS))
        self.assertIn("evidence from the user's files or connectors, in any discovery", skill)
        self.assertIn(
            "READ only the files and the connectors in WHERE, and only with tools that read. "
            "NEVER call a connector tool that sends, creates, changes or deletes anything.",
            analyst,
        )
        self.assertIn("- NAMED SOURCES:", section(verifier, "## Input"))
        self.assertIn('"not a named source"', verifier)
        self.assertIn("NAMED SOURCES", flat(steps(read(SKILL))[3][1]))
        self.assertIn("A connector the user named is not available to sub-agents", skill)
        self.assertIn("export the items to a file the analysts can read", skill)
        self.assertIn("the command or query and its result", analyst)
        self.assertIn("the command or query and its result", records)

    def test_round_4_wording(self):
        skill = read(SKILL)
        verifier = flat(read(AGENTS["quote-verifier"]))
        self.assertIn("no quote from a web page counts", flat(skill))
        self.assertIn("the items no file or connector evidence bears on stay `unverified`", flat(skill))
        outside = flat(section(read(RECORDS), "## Outside text"))
        self.assertIn("`summary`", outside)
        self.assertIn("`ref`", outside)
        self.assertTrue(
            any(
                '"type": "evidence"' in line and '"summary"' in line and '"words": {"type": "quote"' in line
                for line in read(RECORDS).splitlines()
            )
        )
        self.assertIn(
            'IF the file is not text, EXTRACT its text with a command, or SET the evidence `not reachable` with the reason "no text tool"',
            verifier,
        )
        self.assertIn("Analysts read the web, and the files and connectors you name", flat(read(DOCS)))

    def test_principles_state_findings_without_describing_the_research(self):
        """PRINCIPLES 1: no effect sizes or statements of where evidence comes from or how strong it is."""
        skill = read(SKILL)
        for word in (
            r"\d+ ?%",
            r"\ba fifth\b",
            r"\btrials?\b",
            r"randomi[sz]ed",
            r"\bstud(?:y|ies)\b",
            r"\bmeasured\b",
            r"common practice",
            r"trial runs",
        ):
            with self.subTest(word):
                self.assertNotRegex(skill, word)
        self.assertGreaterEqual(skill.count("TREAT this as a guide, not a rule"), 2)

    def test_a_computed_result_counts_once_the_user_confirms_it(self):
        """D24: nothing runs a computed result again; the user confirms it."""
        skill = flat(read(SKILL))
        verifier = read(AGENTS["quote-verifier"])
        analyst = flat(read(AGENTS["analyst"]))
        records = flat(read(RECORDS))
        self.assertIn('with the suggested default "Confirm this result"', skill)
        self.assertIn("ONCE the user takes it, SET the evidence `counts`", skill)
        self.assertNotRegex(verifier, r"(?i)re-?run")
        self.assertIn("SKIP evidence whose words hold a command or query and its result", flat(verifier))
        self.assertIn("one read-only command or query on a named source", analyst)
        self.assertNotIn("runs it again", analyst + records)
        self.assertIn("counts only once the user confirms it", records)
        self.assertIn('"default": "Confirm this result"', records)

    def test_named_sources_live_in_the_head(self):
        skill = flat(read(SKILL))
        self.assertIn('"named_sources": [', read(RECORDS))
        self.assertIn("ADD them to the head's `named_sources`", skill)
        self.assertIn("from the head's `named_sources`", flat(steps(read(SKILL))[3][1]))
        self.assertIn("`named_sources`", flat(section(read(SKILL), "### Resume a discovery")))
        self.assertIn("re-reads each quote's web page, file or connector item", flat(read(DOCS)))

    def test_round_6_records(self):
        records = flat(read(RECORDS))
        self.assertIn('"to": "<the skills you handed it to, such as /design-better and /architect-better>"', records)
        self.assertIn("not confirmed by you", records)
        self.assertIn("inside a named folder", records)
        body = flat(steps(read(SKILL))[3][1])
        self.assertIn(
            "ONCE the user takes it, SET the evidence `counts` and ADD the change of state for each item it bears on",
            body,
        )
        self.assertIn('SET it `unverified` with the reason "not confirmed by you"', body)

    def test_the_confirm_question_names_the_computed_result_by_its_id(self):
        """S90, redact: the question holds no evidence text; the page or the chat shows the command and result."""
        body = flat(steps(read(SKILL))[3][1])
        self.assertIn('"Is the result of <E-...> right?"', body)
        self.assertIn("never copied into the question's text", body)
        self.assertNotIn("showing its command or query and its result", body)
        records = read(RECORDS)
        self.assertIn(
            '"about": {"type": "evidence", "evidence": "<E-... a computed result>"}, '
            '"asked": "Is the result of <E-...> right?", "default": "Confirm this result"',
            records,
        )
        self.assertNotIn("<the command or query, and its result: is it right?>", records)

    def test_records_name_the_one_exception_to_the_verifier_setting_the_outcome(self):
        records = flat(read(RECORDS))
        self.assertIn(
            "the coordinator sets a computed result `counts` once the user confirms it, or `unverified`", records
        )

    def test_no_text_pipes_echo_into_a_command(self):
        for path in [*skill_texts(), DOCS]:
            for sentence in re.split(r"(?<=[.:])\s+", flat(read(path))):
                if re.search(r"\becho\b", sentence):
                    with self.subTest(path.name, sentence=sentence[:80]):
                        self.assertIn("NEVER", sentence)

    def test_no_text_starts_research_better_or_writes_to_its_boards(self):
        self.assertEqual(len(skill_texts()), 5)
        for path in [*skill_texts(), DOCS]:
            text = read(path)
            with self.subTest(path.name):
                self.assertTrue(text, f"{path} is missing")
                self.assertNotIn(".research", text)
                for sentence in re.split(r"(?<=[.:])\s+", flat(text)):
                    if "research-better" in sentence:
                        self.assertIn("instead", sentence, sentence)


class Terms(unittest.TestCase):
    def test_a_quote_not_on_the_page_is_not_found_and_a_reworded_one_is_corrected(self):
        verifier, skill, recs = (flat(read(x)) for x in (AGENTS["quote-verifier"], SKILL, RECORDS))
        self.assertIn('SET `status` `not found` with the reason "not on the page"', verifier)
        self.assertIn('SET `status` `reworded` with the reason "reworded" and `page_words`', verifier)
        self.assertNotIn('"reworded: " and the page', verifier)
        self.assertIn("ADD the corrected quote as new evidence", skill)
        self.assertIn("`corrects`", skill)
        self.assertIn("`checking | counts | unverified | not reachable | not found | reworded | removed`", recs)
        self.assertIn('"corrects": "<E-... the reworded evidence>"', recs)

    def test_the_agreed_terms_are_used(self):
        text = flat(read(SKILL))
        for term in ("about your users", "from elsewhere", "reality check", "test"):
            self.assertIn(term, text)

    def test_no_text_says_experiment(self):
        for path in [*skill_texts(), DOCS]:
            with self.subTest(path.name):
                self.assertTrue(read(path), f"{path} is missing")
                self.assertNotRegex(read(path), r"(?i)experiment")


class Agents(unittest.TestCase):
    def test_each_agent_has_the_frontmatter_and_sections(self):
        for name, path in AGENTS.items():
            text = read(path)
            with self.subTest(name):
                self.assertTrue(text, f"{path} is missing")
                head = frontmatter(text)
                self.assertEqual(list(head), ["name", "description", "capabilities", "edits", "model", "model_reason"])
                self.assertEqual(head["name"], name)
                self.assertEqual(head["model"], "cheaper")
                places = [text.find(h) for h in ("\n## Input\n", "\n## Output\n")]
                self.assertNotIn(-1, places)
                self.assertEqual(places, sorted(places))
                if "\n## Messages\n" in text:
                    self.assertTrue(places[0] < text.find("\n## Messages\n") < places[1])
                self.assertIn("as data", flat(text))

    def test_the_analyst_and_the_quote_verifier_hand_back_record_ids_only(self):
        for name in ("analyst", "quote-verifier"):
            with self.subTest(name):
                self.assertIn("record ids", flat(section(read(AGENTS[name]), "## Output")))

    def test_the_behaviour_verifier_hands_back_findings_and_writes_no_record(self):
        text = read(AGENTS["behaviour-verifier"])
        self.assertNotRegex(text, r"better\.pyz (?:add|set|create)")
        self.assertIn("edits: false", text)
        self.assertIn("finding", section(text, "## Output"))

    def test_the_quote_verifier_reads_a_page_as_research_better_does(self):
        """D27: web tools, never a shell command; the read is recorded; a quote counts only on a raw read."""
        text = flat(read(AGENTS["quote-verifier"]))
        for phrase in (
            "READ the page with your web tools, never with a shell command",
            "`raw` (full page text) or `extracted` (a fetch tool's processed output)",
            "TREAT a fetch tool's output as an extraction unless the harness documents that it returns the page text",
            "quote counts only when its exact words are on a `raw` read",
            '`unverified` with the reason "page read only as an extraction"',
            "SET the evidence `not reachable`",
            "challenge page",
            "--raw",
        ):
            self.assertIn(phrase, text)
        self.assertIn("web tools", read(AGENTS["quote-verifier"]).split("---")[1])

    def test_no_shell_page_fetch_or_host_check_remains_in_the_skill_folder(self):
        for path in [*skill_texts(), DOCS]:
            text = read(path)
            for word in (
                "curl",
                "--resolve",
                "getaddrinfo",
                "is_global",
                "IPv4Address",
                "urlsplit",
                "pdftotext",
            ):
                with self.subTest(path.name, word=word):
                    self.assertNotIn(word, text)

    def test_the_analyst_keeps_to_its_budget_and_its_records(self):
        text = flat(read(AGENTS["analyst"]))
        for phrase in (
            "10 searches and reads",
            "people's, customers' or internal project names",
            "keep no copy of a page",
            "EXISTING RECORDS",
            "LIST your own records",
        ):
            self.assertIn(phrase, text)


class Records(unittest.TestCase):
    TYPES = ("discover", "item", "change", "source", "evidence", "test", "option", "move", "brief", "decision")

    def test_the_format_opens_with_the_command_and_shows_every_type(self):
        text = read(RECORDS)
        self.assertTrue(text, f"{RECORDS} is missing")
        first = text.index("\n{") if "\n{" in text else len(text)
        self.assertRegex(text[:first], r"better\.pyz (?:add|create)")
        for kind in self.TYPES:
            with self.subTest(kind):
                self.assertIn(f'{{"type": "{kind}"', text)

    def test_the_outside_text_fields_are_marked(self):
        text = flat(section(read(RECORDS), "## Outside text"))
        for field in ("`words`", "`span`", "`title`", "`url`", "`result.text`", "`ambiguity`", "hand-back"):
            self.assertIn(field, text)
        self.assertIn("as data", text)

    def test_the_format_uses_the_data_table_values(self):
        text = read(RECORDS)
        for value in (
            "test first | expand | shrink | switch | adopt | pause | stop",
            "say | did | commit | data | desk",
            "your users | elsewhere",
            "probe | proof of concept | pilot",
            "checking | counts | unverified | not reachable | not found | reworded | removed",
            "unverified | checking | supported | contradicted | needs a test | waiting for you",
        ):
            self.assertIn(value, text)


class RecordWording(unittest.TestCase):
    """A sentence that tells the agent to put a record in a file names the `better.pyz` command, never the file."""

    WRITE = re.compile(r"\b(?:write|writes|save|put|append|edit|store)\b", re.IGNORECASE)
    FILE = re.compile(r"[\w<>./*-]*\.jsonl?\b|\b(?:items|sources|evidence)/")

    def test_no_sentence_sends_the_agent_to_a_record_file(self):
        found = []
        self.assertEqual(len(skill_texts()), 5)
        for path in skill_texts():
            for number, line in enumerate(read(path).splitlines(), 1):
                for sentence in re.split(r"(?<=[.;:])\s+", line):
                    if self.WRITE.search(sentence) and self.FILE.search(sentence) and "better.pyz" not in sentence:
                        found.append(f"{path.name}:{number}: {sentence[:100]}")
        self.assertEqual(found, [])


class Listed(unittest.TestCase):
    def test_the_readme_and_the_docs_list_the_skill(self):
        self.assertIn("[`/discover-better`](docs/discover-better.md)", read(ROOT / "README.md"))
        self.assertIn("[`/discover-better`](discover-better.md)", read(ROOT / "docs" / "getting-started.md"))
        self.assertTrue(read(DOCS).startswith("# `/discover-better`"))


if __name__ == "__main__":
    unittest.main()
