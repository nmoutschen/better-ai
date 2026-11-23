"""discover-better: the package, its unit kind, and the shape of every record it writes (T6).

Run with `python3 tests/run.py test_discover_schemas`. Each test names the requirement it checks. Shape checks
run on one record at a time with `schema.check_record`; where a pointer or a file matters they run `check` on a unit.
"""

import ast
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))
import better  # noqa: E402
import discover_records as R  # noqa: E402
import pyz  # noqa: E402

from better_ai import resources, schema, skill  # noqa: E402
from better_ai.discover import SKILL  # noqa: E402

PACKAGE = ROOT / "src" / "better_ai" / "discover"
EVENTS = ["conversation.schema.json", "discover-events.schema.json"]
HEX = "b" * 64


DOCS = schema.docs_for("discover")


def problems(record, name):
    """The shape problems of one record: (field, message). Pointers need the files around it: `Pointers` checks those."""
    return list(dict.fromkeys((p.field, p.message) for p in schema.validate_instance(record, DOCS[name], DOCS)))


class Shape(unittest.TestCase):
    """What every shape test uses: a record is valid, or it is refused with the field named."""

    def valid(self, record, name):
        self.assertEqual(problems(record, name), [], record)

    def refused(self, record, name, field=None):
        found = problems(record, name)
        self.assertTrue(found, f"accepted: {record}")
        if field is not None:
            self.assertTrue(any(field in f for f, _ in found), f"{field} not named in {found}")


class Package(unittest.TestCase):
    def test_the_skill_has_one_unit_kind_in_dot_discover(self):
        self.assertEqual(SKILL.name, "discover-better")
        self.assertEqual(SKILL.package, "discover")
        (kind,) = SKILL.kinds
        self.assertEqual((kind.folder, kind.head, kind.head_type), (".discover", "discover.json", "discover"))
        self.assertEqual(set(kind.folders), {"evidence", "sources"})
        self.assertEqual(SKILL.exclude, ".discover/")

    def test_S96_skills_json_lists_discover_better_and_the_owner_maps_name_it(self):
        listed = json.loads(resources.read_text("skills.json"))["skills"]
        self.assertEqual(listed["discover-better"], {"package": "discover"})
        self.assertEqual(skill.OWNER_BY_ROOT[".discover"], "discover-better")
        self.assertEqual(skill.OWNER_BY_HEAD["discover.json"], "discover-better")

    def test_S96_the_build_accepts_the_package_and_the_pyz_it_makes_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            built = pyz.build_into(tmp)
            done = subprocess.run(
                [sys.executable, "-I", str(built["discover-better"]), "--help"], capture_output=True, text=True
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertTrue(done.stdout.startswith("better.pyz discover-better "), done.stdout[:80])

    def test_a_unit_of_another_skill_is_refused_with_the_owner_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            R.make_repo(Path(tmp))
            done = R.run(Path(tmp), "create", ".code/x", "--by", "a", stdin="{}")
            self.assertEqual(done.returncode, 1)
            self.assertIn("code-better", done.stderr)

    def test_the_rule_and_page_modules_exist_as_stubs_registered_from_the_package(self):
        import better_ai.discover as package

        owners = {
            "rules_moves": "T9",
            "summary": "T9",
            "brief": "T10",
            "pagespec": "T11",
        }
        for name, task in owners.items():
            with self.subTest(module=name):
                module = getattr(package, name)
                self.assertIn(task, module.__doc__)

    def test_S120_the_package_makes_no_network_call(self):
        network = {
            "socket",
            "ssl",
            "http",
            "ftplib",
            "smtplib",
            "poplib",
            "imaplib",
            "telnetlib",
            "xmlrpc",
            "socketserver",
            "asyncio",
            "requests",
            "urllib.request",
            "urllib.error",
            "webbrowser",
        }
        files = sorted(PACKAGE.glob("*.py"))
        self.assertTrue(files)
        for path in files:
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module or ""] + [f"{node.module}.{a.name}" for a in node.names]
                for name in names:
                    parts = name.split(".")
                    reached = {".".join(parts[: i + 1]) for i in range(len(parts))}
                    self.assertFalse(reached & network, f"{path.name} imports {name}")

    def test_S71_the_fixture_unit_covers_what_smoke_py_asks_for(self):
        spec = importlib.util.spec_from_file_location("smoke", ROOT / "tools" / "smoke.py")
        smoke = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(smoke)
        fixture = json.loads((ROOT / "tests" / "fixtures" / "units" / "discover-better" / "smoke.json").read_text())
        self.assertEqual(smoke.coverage_problems(fixture), [])
        self.assertEqual(fixture["steps"][0]["args"][:2], ["create", ".discover/demo"])


class Create(unittest.TestCase):
    def test_S59_create_adds_the_folder_to_info_exclude_and_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = R.make_repo(Path(tmp))
            done = R.run(repo, "create", ".discover/d", "--by", R.COORD, stdin=R.head_fields())
            self.assertEqual(done.returncode, 0, done.stderr)
            exclude = (repo / ".git" / "info" / "exclude").read_text().splitlines()
            self.assertEqual(exclude.count(".discover/"), 1)
            self.assertIn(".discover/", done.stdout)
            self.assertIn("exclu", done.stdout)
            again = R.run(repo, "create", ".discover/e", "--by", R.COORD, stdin=R.head_fields())
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertEqual((repo / ".git" / "info" / "exclude").read_text().splitlines().count(".discover/"), 1)
            self.assertNotIn("exclu", again.stdout)

    def test_create_makes_the_head_and_the_two_folders_and_check_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            unit = R.made_unit(Path(tmp))
            self.assertTrue((unit / "discover.json").is_file())
            self.assertTrue((unit / "evidence").is_dir() and (unit / "sources").is_dir())
            done = R.run(Path(tmp), "check", ".discover/d")
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_S101_each_record_goes_in_its_own_file_or_jsonl_and_ids_carry_the_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            unit = R.made_unit(repo)
            fields = {
                "item": {**R.without(R.ITEM, "type", "at", "by", "id"), "checker": "a1", "since": R.AT},
                "option": R.without(R.OPTION, "type", "at", "by", "id"),
                "test": R.without(R.TEST, "type", "at", "by", "id"),
                "decision": R.without(R.DECISION, "type", "at", "by", "id"),
            }
            for kind, body in fields.items():
                done = R.run(repo, "add", ".discover/d", kind, "--by", R.COORD, stdin=json.dumps(body))
                self.assertEqual(done.returncode, 0, f"{kind}: {done.stderr}")
            self.assertEqual(
                {"items.jsonl", "options.jsonl", "tests.jsonl", "decisions.jsonl"},
                {p.name for p in unit.glob("*.jsonl")},
            )
            source = R.without(R.SOURCE, "type", "at", "by", "id")
            done = R.run(repo, "add", ".discover/d", "source", "--by", "a1", stdin=json.dumps(source))
            self.assertEqual((done.returncode, done.stdout.strip()), (0, "S-a1-1"), done.stderr)
            self.assertTrue((unit / "sources" / "S-a1-1.json").is_file())
            body = R.without(R.EVIDENCE, "type", "at", "by", "id")
            done = R.run(repo, "add", ".discover/d", "evidence", "--by", "a1", stdin=json.dumps(body))
            self.assertEqual((done.returncode, done.stdout.strip()), (0, "E-a1-1"), done.stderr)
            self.assertTrue((unit / "evidence" / "E-a1-1.json").is_file())
            self.assertEqual(R.run(repo, "check", ".discover/d").returncode, 0)

    def test_S101_two_analysts_adding_evidence_at_once_lose_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            unit = R.made_unit(repo)
            for checker in ("a1", "a2"):
                item = {**R.without(R.ITEM, "type", "at", "by", "id"), "text": checker, "checker": checker}
                done = R.run(
                    repo, "add", ".discover/d", "item", "--by", R.COORD, stdin=json.dumps({**item, "since": R.AT})
                )
                self.assertEqual(done.returncode, 0, done.stderr)
            for agent in ("a1", "a2"):
                body = json.dumps(R.without(R.SOURCE, "type", "at", "by", "id"))
                self.assertEqual(R.run(repo, "add", ".discover/d", "source", "--by", agent, stdin=body).returncode, 0)
            body = json.dumps(R.without(R.EVIDENCE, "type", "at", "by", "id", "source"))

            def add(agent):
                bears = [{"item": "P1" if agent == "a1" else "P2", "direction": "for"}]
                text = json.dumps({**json.loads(body), "source": f"S-{agent}-1", "bears_on": bears})
                return better.run(
                    R.SKILL, "add", ".discover/d", "evidence", "--by", agent, stdin=text, cwd=repo
                ).returncode

            with ThreadPoolExecutor(2) as pool:
                codes = list(pool.map(add, ("a1", "a2")))
            self.assertEqual(codes, [0, 0])
            self.assertEqual({p.name for p in (unit / "evidence").iterdir()}, {"E-a1-1.json", "E-a2-1.json"})

    def test_an_item_id_comes_from_its_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            R.made_unit(repo)
            ids = []
            for kind in ("problem", "opportunity", "behaviour", "problem"):
                body = R.without(R.ITEM if kind != "behaviour" else R.BEHAVIOUR, "type", "at", "by", "id")
                body["kind"] = kind
                if kind == "behaviour":
                    body["rests_on"] = []
                done = R.run(repo, "add", ".discover/d", "item", "--by", R.COORD, stdin=json.dumps(body))
                self.assertEqual(done.returncode, 0, done.stderr)
                ids.append(done.stdout.strip())
            self.assertEqual(ids, ["P1", "O1", "B1", "P2"])


class Head(Shape):
    def test_S123_the_head_requires_its_fields_and_allows_handed(self):
        self.valid(R.HEAD, "discover.schema.json")
        for key in ("idea", "appetite", "setting", "coordinator", "step", "status"):
            with self.subTest(missing=key):
                self.refused(R.without(R.HEAD, key), "discover.schema.json", key)
        handed = {"brief": "brief/v1.md", "to": "design-better", "at": R.AT}
        self.valid(R.record(R.HEAD, handed=handed), "discover.schema.json")
        self.refused(R.record(R.HEAD, handed={"brief": "brief/v1.md"}), "discover.schema.json", "handed")
        self.refused(R.record(R.HEAD, setting="both"), "discover.schema.json", "setting")
        self.refused(R.record(R.HEAD, status="closed"), "discover.schema.json", "status")
        for step in [str(n) for n in range(1, 11)]:
            self.valid(R.record(R.HEAD, step=step), "discover.schema.json")
        for step in ("0", "11", 3, "1a"):
            with self.subTest(step=step):
                self.refused(R.record(R.HEAD, step=step), "discover.schema.json", "step")
        self.valid(R.record(R.HEAD, setting="internal", status="finished"), "discover.schema.json")


class Items(Shape):
    NAME = "item.schema.json"

    def test_S73_an_item_has_kind_text_rests_on_and_risks(self):
        self.valid(R.ITEM, self.NAME)
        for key in ("kind", "text", "rests_on", "risks"):
            with self.subTest(missing=key):
                self.refused(R.without(R.ITEM, key), self.NAME, key)
        for kind in ("problem", "opportunity"):
            self.valid(R.record(R.ITEM, kind=kind), self.NAME)
        self.refused(R.record(R.ITEM, kind="idea"), self.NAME, "kind")
        self.refused(R.record(R.ITEM, rests_on=[3]), self.NAME, "rests_on")

    def test_S73_a_risk_has_an_id_a_kind_and_text(self):
        for kind in ("value", "usability", "feasibility", "viability"):
            risk = {"id": "R2", "kind": kind, "text": "It may fail."}
            self.valid(R.record(R.ITEM, risks=[risk]), self.NAME)
        bad = {
            "id": {"id": "risk1", "kind": "value", "text": "x"},
            "kind": {"id": "R1", "kind": "money", "text": "x"},
            "text": {"id": "R1", "kind": "value"},
        }
        for field, risk in bad.items():
            with self.subTest(field=field):
                self.refused(R.record(R.ITEM, risks=[risk]), self.NAME, field)

    def test_S62_alternative_is_null_a_move_or_a_reality_check(self):
        self.valid(R.record(R.ITEM, alternative=None), self.NAME)
        self.valid(R.record(R.ITEM, alternative={"type": "move", "move": "M1"}), self.NAME)
        self.valid(R.record(R.ITEM, alternative={"type": "reality_check", "evidence": ["E-a1-1"]}), self.NAME)
        self.refused(R.record(R.ITEM, alternative={"type": "move"}), self.NAME, "alternative")
        self.refused(R.record(R.ITEM, alternative={"type": "reality_check", "move": "M1"}), self.NAME, "alternative")
        self.refused(R.record(R.ITEM, alternative={"type": "guess", "move": "M1"}), self.NAME, "alternative")

    def test_S62_testable_form_is_ears_or_given_when_then(self):
        for form in ("ears", "given when then"):
            body = R.record(R.BEHAVIOUR, testable={"form": form, "text": "x"})
            self.valid(body, self.NAME)
        self.refused(R.record(R.BEHAVIOUR, testable={"form": "gherkin", "text": "x"}), self.NAME, "form")

    def test_S107_a_behaviour_needs_testable(self):
        self.valid(R.BEHAVIOUR, self.NAME)
        self.refused(R.without(R.BEHAVIOUR, "testable"), self.NAME, "testable")
        self.valid(R.record(R.BEHAVIOUR, ambiguity="'its new state' is not defined"), self.NAME)

    def test_the_work_fields_hold_a_name_and_a_time_or_nothing(self):
        work = {"checker": "a1", "since": R.AT, "tries": ["a1"], "updated_at": R.AT}
        self.valid(R.record(R.ITEM, **work), self.NAME)
        self.valid(R.record(R.ITEM, checker=None, since=None), self.NAME)
        self.refused(R.record(R.ITEM, since="yesterday"), self.NAME, "since")


class Changes(Shape):
    NAME = "change.schema.json"

    def test_S111_about_field_and_risk(self):
        self.valid(R.CHANGE, self.NAME)
        self.valid(R.RISK_CHANGE, self.NAME)
        for key in ("about", "field", "to", "cause"):
            with self.subTest(missing=key):
                self.refused(R.without(R.CHANGE, key), self.NAME, key)
        self.valid(R.record(R.CHANGE, about={"type": "discovery"}, field="appetite", to="a month"), self.NAME)
        self.valid(R.record(R.CHANGE, about={"type": "discovery"}, field="setting", to="internal"), self.NAME)
        self.refused(R.record(R.CHANGE, field="mood"), self.NAME, "field")
        self.refused(R.record(R.CHANGE, about={"type": "test", "test": "X1"}), self.NAME, "about")
        self.refused(R.record(R.CHANGE, about={"type": "item"}), self.NAME, "about")

    def test_S111_a_risk_change_names_its_risk_and_only_a_risk_change_does(self):
        self.refused(R.without(R.RISK_CHANGE, "risk"), self.NAME, "risk")
        self.refused(R.record(R.RISK_CHANGE, risk="risk 1"), self.NAME, "risk")
        self.refused(R.record(R.CHANGE, risk="R1"), self.NAME, "risk")

    def test_S111_accepted_is_allowed_only_for_a_risk(self):
        self.refused(R.record(R.CHANGE, to="accepted"), self.NAME, "to")
        self.refused(R.record(R.CHANGE, field="importance", to="accepted"), self.NAME, "to")
        self.refused(R.record(R.RISK_CHANGE, to="supported"), self.NAME, "to")

    def test_S111_accepted_is_refused_for_appetite_and_setting_too(self):
        about = {"type": "discovery"}
        for field in ("appetite", "setting"):
            with self.subTest(field=field):
                self.refused(R.record(R.CHANGE, about=about, field=field, to="accepted"), self.NAME, "to")

    def test_S74_a_state_is_one_of_six_and_an_importance_one_of_two(self):
        for state in ("unverified", "checking", "supported", "contradicted", "needs a test", "waiting for you"):
            self.valid(R.record(R.CHANGE, to=state), self.NAME)
        for state in ("risk accepted", "Supported", "done"):
            with self.subTest(state=state):
                self.refused(R.record(R.CHANGE, to=state), self.NAME, "to")
        for importance in ("high", "lower"):
            self.valid(R.record(R.CHANGE, field="importance", to=importance), self.NAME)
        self.refused(R.record(R.CHANGE, field="importance", to="medium"), self.NAME, "to")

    def test_S27_a_change_needs_at_least_one_cause(self):
        cites = {
            "evidence": ["E-a1-1"],
            "test": "X1",
            "answer": {"type": "decision", "id": "D1"},
            "reasoning": "Two quotes agree.",
        }
        for key, value in cites.items():
            with self.subTest(cause=key):
                self.valid(R.record(R.CHANGE, cause={key: value}), self.NAME)
        self.valid(R.record(R.CHANGE, cause=cites), self.NAME)
        self.refused(R.record(R.CHANGE, cause={}), self.NAME, "cause")
        self.refused(R.record(R.CHANGE, cause={"evidence": []}), self.NAME, "cause")

    def test_S27_an_answer_is_a_decision_a_page_event_or_chat_words(self):
        for answer in (
            {"type": "decision", "id": "D1"},
            {"type": "page", "event": "e1"},
            {"type": "chat", "text": "Yes, accept it."},
        ):
            self.valid(R.record(R.CHANGE, cause={"answer": answer}), self.NAME)
        for answer in ({"type": "decision"}, {"type": "page", "id": "e1"}, {"type": "chat"}, {"type": "mail"}):
            with self.subTest(answer=answer):
                self.refused(R.record(R.CHANGE, cause={"answer": answer}), self.NAME, "answer")


class Sources(Shape):
    NAME = "source.schema.json"

    def test_S110_a_web_source_has_a_url_and_how_it_was_read(self):
        self.valid(R.SOURCE, self.NAME)
        for read in ("raw", "extracted", "snippet", "blocked"):
            self.valid(R.record(R.SOURCE, origin={"type": "web", "url": "https://x.org/a", "read": read}), self.NAME)
        for origin in (
            {"type": "web", "url": "https://x.org/a", "read": "abstract"},
            {"type": "web", "url": "https://x.org/a"},
            {"type": "web", "read": "raw"},
            {"type": "web", "url": "ftp://x.org/a", "read": "raw"},
            {"type": "web", "url": "javascript:alert(1)", "read": "raw"},
        ):
            with self.subTest(origin=origin):
                self.refused(R.record(R.SOURCE, origin=origin), self.NAME, "origin")

    def test_S110_a_source_from_you_holds_a_page_event_or_chat_words(self):
        self.valid(R.YOU_SOURCE, self.NAME)
        page = {"type": "you", "given": {"type": "page", "event": "a1"}}
        self.valid(R.record(R.YOU_SOURCE, origin=page, said_by_role="a teammate on payments"), self.NAME)
        for given in ({"type": "page"}, {"type": "chat"}, {"type": "file", "text": "x"}):
            with self.subTest(given=given):
                self.refused(R.record(R.YOU_SOURCE, origin={"type": "you", "given": given}), self.NAME, "given")
        self.refused(R.record(R.YOU_SOURCE, origin={"type": "you"}), self.NAME, "origin")
        self.refused(R.record(R.YOU_SOURCE, origin={"type": "other"}), self.NAME, "origin")

    def test_S95_a_source_id_names_its_agent(self):
        for good in ("S-a1-1", "S-analyst-2-14", "S-coord-1"):
            self.valid(R.record(R.SOURCE, id=good), self.NAME)
        for bad in ("S1", "S-a1", "E-a1-1", "S-a1-x"):
            with self.subTest(id=bad):
                self.refused(R.record(R.SOURCE, id=bad), self.NAME, "id")


class Evidence(Shape):
    NAME = "evidence.schema.json"

    def test_S75_kind_about_and_bears_on(self):
        self.valid(R.EVIDENCE, self.NAME)
        for kind in ("say", "did", "commit", "data", "desk"):
            self.valid(R.record(R.EVIDENCE, kind=kind), self.NAME)
        self.refused(R.record(R.EVIDENCE, kind="hear"), self.NAME, "kind")
        for about in ("your users", "elsewhere"):
            self.valid(R.record(R.EVIDENCE, about=about), self.NAME)
        self.refused(R.record(R.EVIDENCE, about="everyone"), self.NAME, "about")
        self.valid(R.record(R.EVIDENCE, bears_on=[{"item": "P1", "direction": "against"}]), self.NAME)
        for bad in ({"item": "P1"}, {"direction": "for"}, {"item": "P1", "direction": "sideways"}):
            with self.subTest(bears_on=bad):
                self.refused(R.record(R.EVIDENCE, bears_on=[bad]), self.NAME, "bears_on")
        for key in ("source", "words", "kind", "about", "bears_on", "status"):
            with self.subTest(missing=key):
                self.refused(R.without(R.EVIDENCE, key), self.NAME, key)

    def test_S121_words_are_a_quote_or_the_event_that_holds_them(self):
        self.valid(R.record(R.EVIDENCE, words={"type": "event", "event": "a1"}), self.NAME)
        for words in (
            {"type": "event"},
            {"type": "event", "text": "x"},
            {"type": "quote"},
            {"type": "quote", "event": "a1"},
            {"type": "summary", "text": "x"},
        ):
            with self.subTest(words=words):
                self.refused(R.record(R.EVIDENCE, words=words), self.NAME, "words")

    def test_S18_a_quote_holds_no_newline_and_at_most_600_characters(self):
        self.valid(R.record(R.EVIDENCE, words={"type": "quote", "text": "x" * 600}), self.NAME)
        for text in ("x" * 601, "one\ntwo", "one\r\ntwo", "one line\n", ""):
            with self.subTest(text=text[:12]):
                self.refused(R.record(R.EVIDENCE, words={"type": "quote", "text": text}), self.NAME, "words")

    def test_S95_an_evidence_id_names_its_agent(self):
        for good in ("E-a1-1", "E-quote-verifier-1-3"):
            self.valid(R.record(R.EVIDENCE, id=good), self.NAME)
        for bad in ("E1", "E-a1", "S-a1-1", "E-a1-x"):
            with self.subTest(id=bad):
                self.refused(R.record(R.EVIDENCE, id=bad), self.NAME, "id")

    def test_S93_the_statuses_and_what_each_needs(self):
        self.valid(R.COUNTING, self.NAME)
        self.valid(R.record(R.EVIDENCE, verifier="v1", since=R.AT, tries=["v1"]), self.NAME)
        for status in ("unverified", "not reachable", "removed"):
            self.valid(R.record(R.EVIDENCE, status=status, verifier="v1", reason="why"), self.NAME)
            self.refused(R.record(R.EVIDENCE, status=status, verifier="v1"), self.NAME, "reason")
        self.refused(R.record(R.EVIDENCE, status="settled"), self.NAME, "status")

    def test_S93_checked_read_span_and_sha256_only_in_counts_and_together(self):
        for key in ("checked_read", "span", "sha256"):
            with self.subTest(missing=key):
                self.refused(R.without(R.COUNTING, key), self.NAME)
            with self.subTest(outside=key):
                outside = R.record(R.EVIDENCE, **{key: R.COUNTING[key]})
                self.refused(outside, self.NAME)
        self.refused(R.record(R.COUNTING, checked_read="extracted"), self.NAME, "checked_read")
        self.refused(R.record(R.COUNTING, sha256="abc"), self.NAME, "sha256")
        self.refused(R.record(R.COUNTING, reason="x"), self.NAME, "reason")
        self.valid(R.record(R.EVIDENCE, status="counts"), self.NAME)  # what you gave counts at once, with no read

    def test_S93_verifier_stays_after_an_outcome_and_since_goes(self):
        self.valid(R.record(R.COUNTING, verifier="v1"), self.NAME)
        self.valid(R.record(R.EVIDENCE, status="unverified", verifier="v1", reason="reworded"), self.NAME)
        outcomes = (R.COUNTING, R.record(R.EVIDENCE, status="unverified", reason="x"))
        for outcome in (*outcomes, R.record(R.EVIDENCE, status="removed", reason="x")):
            with self.subTest(status=outcome["status"]):
                self.refused(R.record(outcome, since=R.AT), self.NAME, "since")

    def test_a_summary_is_text(self):
        self.valid(R.record(R.EVIDENCE, summary="Reported by you: a teammate lost a week."), self.NAME)
        self.refused(R.record(R.EVIDENCE, summary=""), self.NAME, "summary")


class Tests(Shape):
    NAME = "test.schema.json"

    def test_S76_a_planned_test(self):
        self.valid(R.TEST, self.NAME)
        for key in ("what", "kind", "settles", "cost", "rule", "runner", "status"):
            with self.subTest(missing=key):
                self.refused(R.without(R.TEST, key), self.NAME, key)
        for kind in ("probe", "proof of concept", "pilot"):
            self.valid(R.record(R.TEST, kind=kind), self.NAME)
        for runner in ("you", "analyst", "code-better"):
            self.valid(R.record(R.TEST, runner=runner), self.NAME)
        self.refused(R.record(R.TEST, kind="survey"), self.NAME, "kind")
        self.refused(R.record(R.TEST, runner="me"), self.NAME, "runner")
        self.refused(R.record(R.TEST, status="finished"), self.NAME, "status")
        self.refused(R.record(R.TEST, settles="P1"), self.NAME, "settles")

    def test_S76_a_done_test_has_a_result_and_a_removed_one_a_reason(self):
        done = {"text": "Three of five found it.", "outcome": "holds", "evidence": ["E-a1-1"]}
        self.valid(R.record(R.TEST, status="done", result=done), self.NAME)
        self.valid(R.record(R.TEST, status="done", result={**done, "outcome": "changes"}), self.NAME)
        self.refused(R.record(R.TEST, status="done"), self.NAME, "result")
        self.refused(R.record(R.TEST, status="done", result={**done, "outcome": "maybe"}), self.NAME, "outcome")
        self.refused(R.record(R.TEST, status="done", result=R.without(done, "text")), self.NAME, "result")
        self.refused(R.record(R.TEST, status="done", result=R.without(done, "evidence")), self.NAME, "evidence")
        self.refused(R.record(R.TEST, status="done", result={**done, "evidence": []}), self.NAME, "evidence")
        self.valid(R.record(R.TEST, status="removed", reason="too costly"), self.NAME)
        self.refused(R.record(R.TEST, status="removed"), self.NAME, "reason")

    def test_S76_a_running_test_may_name_its_checker(self):
        self.valid(R.record(R.TEST, status="running", checker="a1", since=R.AT), self.NAME)


class Options(Shape):
    NAME = "option.schema.json"

    def test_S33_the_move_is_one_of_seven(self):
        for move in ("test first", "expand", "shrink", "switch", "adopt", "pause", "stop"):
            self.valid(R.record(R.OPTION, move=move), self.NAME)
        for move in ("scale", "Stop", "test-first", ""):
            with self.subTest(move=move):
                self.refused(R.record(R.OPTION, move=move), self.NAME, "move")

    def test_S118_an_option_has_its_costs_and_a_note_from_three(self):
        self.valid(R.OPTION, self.NAME)
        for key in ("move", "text", "cost", "speed", "upkeep", "undo", "note"):
            with self.subTest(missing=key):
                self.refused(R.without(R.OPTION, key), self.NAME, key)
        for note in ("proposed", "ruled out by your appetite", None):
            self.valid(R.record(R.OPTION, note=note), self.NAME)
        self.refused(R.record(R.OPTION, note="maybe"), self.NAME, "note")
        self.valid(R.record(R.OPTION, updated_at=R.AT), self.NAME)


class Moves(Shape):
    NAME = "move.schema.json"

    def test_S78_a_move_has_an_id_an_option_a_step_why_and_an_answer(self):
        self.valid(R.MOVE, self.NAME)
        for key in ("option", "step", "why", "answer"):
            with self.subTest(missing=key):
                self.refused(R.without(R.MOVE, key), self.NAME, key)
        for bad in ("M", "m1", "1", "K1"):
            with self.subTest(id=bad):
                self.refused(R.record(R.MOVE, id=bad), self.NAME, "id")

    def test_S78_the_answer_is_a_page_event_or_chat_words_with_an_optional_confirm(self):
        self.valid(R.record(R.MOVE, answer={"type": "page", "event": "c1"}), self.NAME)
        self.valid(R.record(R.MOVE, answer={"type": "chat", "text": "Yes", "confirm": "D2"}), self.NAME)
        for answer in (
            {"type": "page"},
            {"type": "chat"},
            {"type": "page", "event": "c1", "confirm": "D2"},
            {"type": "decision", "id": "D1"},
        ):
            with self.subTest(answer=answer):
                self.refused(R.record(R.MOVE, answer=answer), self.NAME, "answer")


class Briefs(Shape):
    NAME = "brief.schema.json"

    def test_S118_a_brief_has_v_n_a_move_and_a_status(self):
        self.valid(R.BRIEF, self.NAME)
        for key in ("move", "status"):
            with self.subTest(missing=key):
                self.refused(R.without(R.BRIEF, key), self.NAME, key)
        for bad in ("1", "V1", "v", "v1a"):
            with self.subTest(id=bad):
                self.refused(R.record(R.BRIEF, id=bad), self.NAME, "id")
        self.refused(R.record(R.BRIEF, status="sent"), self.NAME, "status")

    def test_S118_file_and_sha256_only_in_final(self):
        final = {"status": "final", "file": "brief/v1.md", "sha256": HEX}
        self.valid(R.record(R.BRIEF, **final), self.NAME)
        self.refused(R.record(R.BRIEF, status="final"), self.NAME)
        self.refused(R.record(R.BRIEF, **R.without(final, "file")), self.NAME, "file")
        self.refused(R.record(R.BRIEF, **R.without(final, "sha256")), self.NAME, "sha256")
        self.refused(R.record(R.BRIEF, file="brief/v1.md", sha256=HEX), self.NAME)
        self.valid(R.record(R.BRIEF, **final, redacted=[HEX]), self.NAME)

    def test_a_brief_holds_the_decision_and_the_open_questions(self):
        body = {"decision": "Test first.", "why": "It is cheapest.", "questions": ["Who signs up?"]}
        self.valid(R.record(R.BRIEF, **body), self.NAME)


class Decisions(Shape):
    NAME = "decisions.schema.json"

    def test_S77_about_is_an_item_a_risk_an_option_evidence_or_the_discovery(self):
        for about in (
            {"type": "item", "item": "P1"},
            {"type": "risk", "item": "P1", "risk": "R1"},
            {"type": "option", "option": "K1"},
            {"type": "evidence", "evidence": "E-a1-1"},
            {"type": "discovery"},
        ):
            default = "Accept the risk" if about["type"] == "risk" else "Yes"
            self.valid(R.record(R.DECISION, about=about, default=default), self.NAME)
        for about in (
            {"type": "task", "task": "T1"},
            {"type": "item"},
            {"type": "risk", "item": "P1"},
            {"type": "discovery", "item": "P1"},
            {"type": "board"},
        ):
            with self.subTest(about=about):
                self.refused(R.record(R.DECISION, about=about), self.NAME, "about")

    def test_S5_a_risk_decision_has_the_fixed_default(self):
        risk = {"type": "risk", "item": "P1", "risk": "R1"}
        self.valid(R.record(R.DECISION, about=risk, default="Accept the risk"), self.NAME)
        self.refused(R.record(R.DECISION, about=risk, default="Plan a test"), self.NAME, "default")
        self.refused(R.record(R.DECISION, about=risk, default=None), self.NAME, "default")
        self.refused(R.without(R.record(R.DECISION, about=risk), "default"), self.NAME, "default")

    def test_S7_only_waiting_and_answered_and_no_deadline(self):
        self.valid(R.DECISION, self.NAME)
        for status in ("defaulted", "decided", "pending", "default"):
            with self.subTest(status=status):
                self.refused(R.record(R.DECISION, status=status), self.NAME, "status")
        self.refused(R.record(R.DECISION, deadline="2026-11-23T11:00:00Z"), self.NAME, "deadline")
        self.refused(R.record(R.DECISION, deadline=None), self.NAME, "deadline")

    def test_a_waiting_decision_has_no_answer_and_an_answered_one_has_answer_and_a_time(self):
        self.refused(R.record(R.DECISION, answer={"type": "chat", "text": "Yes"}), self.NAME)
        self.refused(R.record(R.DECISION, answered_at=R.AT), self.NAME)
        answered = {"status": "answered", "answer": {"type": "chat", "text": "Yes"}, "answered_at": R.AT}
        self.valid(R.record(R.DECISION, **answered), self.NAME)
        self.refused(R.record(R.DECISION, **R.without(answered, "answer")), self.NAME, "answer")
        self.refused(R.record(R.DECISION, **R.without(answered, "answered_at")), self.NAME, "answered_at")
        self.refused(R.record(R.DECISION, **answered, decision="Yes"), self.NAME)

    def test_the_default_is_text_or_none_never_missing(self):
        self.valid(R.record(R.DECISION, default=None), self.NAME)
        self.refused(R.without(R.DECISION, "default"), self.NAME, "default")

    def test_the_shared_decision_schema_is_unchanged(self):
        shared = json.loads((ROOT / "src" / "better_ai" / "schemas" / "decisions.schema.json").read_text())
        self.assertIn("defaulted", shared["properties"]["status"]["enum"])
        self.assertNotIn("defaulted", DOCS["decisions.schema.json"]["properties"]["status"]["enum"])


class Events(Shape):
    def test_S60_the_page_events_are_named_and_each_has_an_id(self):
        for kind in R.EVENTS:
            with self.subTest(event=kind):
                self.assertEqual(problems(R.event(kind), EVENTS[0]), [])
                self.assertEqual(problems(R.event(kind), EVENTS[1]), [])
                self.refused(R.without(R.event(kind), "id"), EVENTS[1], "id")
        self.refused(R.event("choose", type="steer"), EVENTS[1], "type")

    def test_S60_the_shared_events_are_still_allowed(self):
        shared = [
            {"type": "note", "at": R.AT, "by": "user", "id": "n1", "text": "hi", "to": None},
            {"type": "reply", "at": R.AT, "by": R.COORD, "id": "r1", "text": "ok", "to": "n1"},
            {"type": "status", "at": R.AT, "by": R.COORD, "to": "n1", "status": "done"},
            {"type": "answer", "at": R.AT, "by": "user", "id": "a9", "decision": "D1", "text": "Yes", "default": True},
            {"type": "accept", "at": R.AT, "by": "user", "to": "D1"},
        ]
        for line in shared:
            with self.subTest(event=line["type"]):
                for name in EVENTS:
                    self.assertEqual(problems(line, name), [], line)

    def test_S98_choose(self):
        self.refused(R.event("choose", confirmed="yes"), EVENTS[1], "confirmed")
        for key in ("option", "revision", "confirmed"):
            self.refused(R.without(R.event("choose"), key), EVENTS[1], key)
        self.assertEqual(problems(R.event("choose", confirmed=True), EVENTS[1]), [])

    def test_S98_add_evidence(self):
        for key in ("text", "source", "kind", "about", "bears_on"):
            with self.subTest(missing=key):
                self.refused(R.without(R.event("add_evidence"), key), EVENTS[1], key)
        self.refused(R.event("add_evidence", kind="hear"), EVENTS[1], "kind")
        self.refused(R.event("add_evidence", about="all"), EVENTS[1], "about")
        self.refused(R.event("add_evidence", bears_on=[{"item": "P1", "direction": "up"}]), EVENTS[1], "bears_on")

    def test_S98_add_result_remove_edit_and_redact(self):
        for kind, key in (
            ("add_result", "test"),
            ("add_result", "text"),
            ("add_result", "outcome"),
            ("remove", "record"),
            ("remove", "reason"),
            ("edit", "record"),
            ("edit", "field"),
            ("edit", "value"),
            ("redact", "evidence"),
        ):
            with self.subTest(event=kind, missing=key):
                self.refused(R.without(R.event(kind), key), EVENTS[1], key)
        self.refused(R.event("add_result", outcome="maybe"), EVENTS[1], "outcome")

    def test_S98_a_page_event_is_the_users(self):
        for kind in R.EVENTS:
            with self.subTest(event=kind):
                self.refused(R.event(kind, by=R.COORD), EVENTS[1], "by")


class Pointers(unittest.TestCase):
    """The pointers the schemas declare are checked by `check` on a real unit."""

    def test_a_change_citing_evidence_that_does_not_exist_is_dangling(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            unit = R.made_unit(repo)
            (unit / "items.jsonl").write_text(json.dumps(R.ITEM) + "\n")
            (unit / "changes.jsonl").write_text(json.dumps(R.CHANGE) + "\n")
            done = R.run(repo, "check", ".discover/d")
            self.assertEqual(done.returncode, 1)
            self.assertIn("E-a1-1", done.stdout)
            self.assertIn("dangling", done.stdout)
            (unit / "sources" / "S-a1-1.json").write_text(json.dumps(R.SOURCE))
            (unit / "evidence" / "E-a1-1.json").write_text(json.dumps(R.COUNTING))
            done = R.run(repo, "check", ".discover/d")
            self.assertEqual(done.returncode, 0, done.stdout)

    def test_a_tests_settles_naming_a_missing_item_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            unit = R.made_unit(repo)
            (unit / "tests.jsonl").write_text(json.dumps(R.TEST) + "\n")
            done = R.run(repo, "check", ".discover/d")
            self.assertEqual(done.returncode, 1)
            self.assertIn("settles", done.stdout)
            self.assertIn("dangling", done.stdout)
            (unit / "items.jsonl").write_text(json.dumps(R.ITEM) + "\n")
            self.assertEqual(R.run(repo, "check", ".discover/d").returncode, 0)

    def test_a_source_from_you_may_point_to_an_add_evidence_or_an_add_result_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            unit = R.made_unit(repo)
            (unit / "items.jsonl").write_text(json.dumps(R.ITEM) + "\n")
            (unit / "tests.jsonl").write_text(json.dumps(R.TEST) + "\n")
            (unit / "options.jsonl").write_text(json.dumps(R.OPTION) + "\n")
            events = [R.event("add_evidence"), R.event("add_result"), R.event("choose", id="c1")]
            (unit / "conversation.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
            for event, ok in (("a1", True), ("r1", True), ("c1", False)):
                with self.subTest(event=event):
                    given = {"type": "you", "given": {"type": "page", "event": event}}
                    (unit / "sources" / "S-coord-1.json").write_text(json.dumps(R.record(R.YOU_SOURCE, origin=given)))
                    done = R.run(repo, "check", ".discover/d")
                    self.assertEqual(done.returncode, 0 if ok else 1, done.stdout)


if __name__ == "__main__":
    unittest.main()
