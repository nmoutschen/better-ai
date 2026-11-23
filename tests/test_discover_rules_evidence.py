"""discover-better: the rules for evidence and sources: the quote flow, the URL rule and the user's evidence.

Run with `python3 tests/run.py test_discover_rules_evidence`. Each test names the requirement it checks. A test starts
from a copy of one prepared repository: a discovery by `coord` with two items (P1 checked by `a1`, P2 by `a2`), a web
source S-a1-1 and a quote E-a1-1 that is `checking`, and a conversation with some of the user's events in it.
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
import discover_records as R  # noqa: E402

from better_ai import schema  # noqa: E402
from better_ai.discover import rules_evidence  # noqa: E402

COORD = R.COORD
QUOTE = "We lost a week to this."
PAGE = f"A post.\nIn the end, {QUOTE} Never again.\n"
SPAN = f"In the end, {QUOTE}"
OLD = "2026-11-23T08:00:00Z"
TEMPLATES: dict[str, Path] = {}
_KEEP: list[tempfile.TemporaryDirectory] = []


def ago(minutes):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def build(setting):
    tmp = tempfile.TemporaryDirectory()
    _KEEP.append(tmp)
    root = Path(os.path.realpath(tmp.name)) / "repo"
    root.mkdir()
    R.make_repo(root)
    done = R.run(root, "create", ".discover/d", "--by", COORD, stdin=R.head_fields(setting=setting))
    assert done.returncode == 0, done.stderr
    unit = ".discover/d"
    for text, checker in (("People lose track.", "a1"), ("People pay for it.", "a2")):
        fields = {"kind": "problem", "text": text, "rests_on": [], "risks": [], "checker": checker, "since": OLD}
        done = R.run(root, "add", unit, "item", "--by", COORD, stdin=json.dumps(fields))
        assert done.returncode == 0, done.stderr
    web = {"origin": {"type": "web", "url": "https://example.com/post", "read": "raw"}, "title": "A post"}
    assert R.run(root, "add", unit, "source", "--by", "a1", stdin=json.dumps(web)).returncode == 0
    fields = {
        "source": "S-a1-1",
        "words": {"type": "quote", "text": QUOTE},
        "kind": "say",
        "about": "your users",
        "bears_on": [{"item": "P1", "direction": "for"}],
        "status": "checking",
    }
    done = R.run(root, "add", unit, "evidence", "--by", "a1", stdin=json.dumps(fields))
    assert done.returncode == 0, done.stderr
    lines = [R.event("add_evidence", id=f"e{n}") for n in (1, 2, 3)]
    lines.append(R.event("remove", id="m1", record="E-a1-1"))
    lines.append(R.event("redact", id="d1", evidence="E-a1-1"))
    (root / unit / "conversation.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
    return root


def setUpModule():
    for setting in ("external", "internal"):
        TEMPLATES[setting] = build(setting)


class Rules(unittest.TestCase):
    setting = "external"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(os.path.realpath(tmp.name)) / "repo"
        shutil.copytree(TEMPLATES[self.setting], self.repo, symlinks=True)
        self.unit = ".discover/d"
        self.folder = self.repo / self.unit
        self.page = self.repo.parent / "page.txt"
        self.page.write_text(PAGE)

    # helpers
    def run_(self, *args, stdin=None):
        text = json.dumps(stdin) if isinstance(stdin, (dict, list)) else stdin
        return R.run(self.repo, *args, stdin=text)

    def add(self, kind, fields, by):
        return self.run_("add", self.unit, kind, "--by", by, stdin=fields)

    def set(self, ident, fields, by=None, raw=None, unset=()):
        args = ["set", self.unit, ident]
        for name in unset:
            args += ["--unset", name]
        if by:
            args += ["--by", by]
        if raw:
            args += ["--raw", str(raw)]
        return self.run_(*args, stdin=fields)

    def evidence(self, ident="E-a1-1"):
        return json.loads((self.folder / "evidence" / f"{ident}.json").read_text())

    def put(self, ident="E-a1-1", **over):
        """Write the evidence as a test needs it, in any state, without going through the command."""
        record = R.record(R.EVIDENCE, id=ident, by=ident.split("-")[1], **over)
        for key in [k for k, v in over.items() if v is None]:
            record.pop(key)
        (self.folder / "evidence" / f"{ident}.json").write_text(json.dumps(record, indent=2) + "\n")

    def refused(self, done, *words):
        self.assertEqual(done.returncode, 1, (done.stdout, done.stderr))
        for word in words:
            self.assertIn(word, done.stdout + done.stderr)

    def ok(self, done):
        self.assertEqual(done.returncode, 0, (done.stdout, done.stderr))

    def counts(self, by="v1", **over):
        fields = {"status": "counts", "checked_read": "raw", "span": SPAN, **over}
        return self.set("E-a1-1", fields, by, self.page)

    def started(self, verifier="v1", since=None):
        self.put(verifier=verifier, tries=[verifier], since=since or ago(1))


class Counts(Rules):
    def test_s12_counts_with_a_verifier_who_read_the_page(self):
        self.started()
        self.ok(self.counts())
        record = self.evidence()
        self.assertEqual((record["status"], record["checked_read"], record["span"]), ("counts", "raw", SPAN))
        self.assertNotIn("since", record)
        self.assertEqual(record["verifier"], "v1")

    def test_s13_better_pyz_computes_the_sha256_of_the_raw_file(self):
        self.started()
        self.ok(self.counts())
        self.assertEqual(self.evidence()["sha256"], hashlib.sha256(PAGE.encode()).hexdigest())

    def test_s13_a_typed_sha256_is_refused(self):
        self.started()
        self.refused(self.counts(sha256="a" * 64), "sha256", "computed by better.pyz")

    def test_s12_counts_needs_a_raw_file(self):
        self.started()
        done = self.set("E-a1-1", {"status": "counts", "checked_read": "raw", "span": SPAN}, "v1")
        self.refused(done, "--raw")
        self.assertEqual(self.evidence()["status"], "checking")

    def test_s12_counts_needs_checked_read_raw(self):
        self.started()
        self.refused(self.set("E-a1-1", {"status": "counts", "span": SPAN}, "v1", self.page), "checked_read")
        done = self.counts(checked_read="extracted")
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual(self.evidence()["status"], "checking")

    def test_s12_the_span_must_occur_in_the_raw_file(self):
        self.started()
        self.refused(self.counts(span="a sentence the page never had"), "span", "does not occur")

    def test_s12_a_missing_or_unreadable_raw_file_is_refused(self):
        self.started()
        fields = {"status": "counts", "checked_read": "raw", "span": SPAN}
        self.refused(self.set("E-a1-1", fields, "v1", self.repo / "nope.txt"), "--raw", "cannot read")
        self.refused(self.set("E-a1-1", fields, "v1", self.repo), "--raw", "cannot read")

    def test_s12_the_quote_must_occur_in_the_span(self):
        self.started()
        self.refused(self.counts(span="A post."), "quote", "span")

    def test_s12_the_quote_matches_the_span_after_whitespace_and_punctuation_are_normalised(self):
        self.page.write_text("He said:  “we LOST a week -- to this”\nand left.")
        self.started()
        self.ok(self.counts(span="we LOST a week -- to this"))

    def test_s12_a_quote_of_only_punctuation_never_counts(self):
        self.put(words={"type": "quote", "text": "..."}, verifier="v1", tries=["v1"], since=ago(1))
        self.page.write_text("...")
        self.refused(self.counts(span="..."), "quote")

    def test_s12_the_verifier_must_differ_from_the_evidences_by(self):
        self.put(verifier="a1", tries=["a1"], since=ago(1))
        self.refused(self.counts(by="a1"), "a1", "added")
        self.assertEqual(self.evidence()["status"], "checking")

    def test_s12_a_raw_file_is_only_for_counts(self):
        self.started()
        done = self.set("E-a1-1", {"status": "unverified", "reason": "reworded"}, "v1", self.page)
        self.refused(done, "--raw")


class Transitions(Rules):
    """S14, S15: every change of status as every writer."""

    STATES = {
        "checking, recent": dict(status="checking", verifier="v1", tries=["v1"], since=ago(5)),
        "checking, stale": dict(status="checking", verifier="v1", tries=["v1"], since=ago(40)),
        "checking, no verifier": dict(status="checking"),
        "not reachable, one try": dict(status="not reachable", verifier="v1", tries=["v1"], reason="HTTP 503"),
        "not reachable, two tries": dict(status="not reachable", verifier="v2", tries=["v1", "v2"], reason="HTTP 503"),
        "counts": dict(status="counts", verifier="v1", tries=["v1"], checked_read="raw", span=SPAN, sha256="a" * 64),
        "unverified": dict(status="unverified", verifier="v1", tries=["v1"], reason="reworded"),
        "removed": dict(status="removed", verifier="v1", tries=["v1"], reason="the user asked: remove m1"),
    }
    WRITERS = (None, "v1", "v2", "v3", "a1", COORD)

    @staticmethod
    def target(name, state):
        """The fields a writer gives to move to `name`, and whether the file goes with it."""
        if name == "counts":
            return {"status": "counts", "checked_read": "raw", "span": SPAN}, True
        if name == "unverified":
            return {"status": "unverified", "reason": "reworded"}, False
        if name == "timeout":
            return {"status": "unverified", "reason": "verifier did not finish"}, False
        if name == "not reachable":
            return {"status": "not reachable", "reason": "HTTP 404"}, False
        if name == "checking":
            return {"status": "checking", "verifier": "v3"}, False
        return {"status": "removed", "reason": "the user asked: remove m1"}, False

    @staticmethod
    def allowed(state, writer, name):
        """The table, written out apart from the code: who may make each change of status. None: not a change."""
        fields = Transitions.STATES[state]
        was = fields["status"]
        same = {"counts": "counts", "unverified": "unverified", "not reachable": "not reachable", "removed": "removed"}
        if same.get("unverified" if name == "timeout" else name) == was and was != "counts":
            return None
        if was == "counts" and name == "counts":
            return False  # what counting wrote is never rewritten
        if name == "removed":
            return was != "removed" and writer == COORD
        if was == "checking":
            if name == "checking":
                return writer == COORD  # starting or replacing a verifier
            if writer is not None and writer == fields.get("verifier"):
                return True
            return name == "timeout" and writer == COORD and state == "checking, stale"
        if was == "not reachable" and name == "checking":
            return writer == COORD and len(fields["tries"]) < 2
        return False

    def test_s14_every_transition_as_every_writer(self):
        names = ("counts", "unverified", "timeout", "not reachable", "checking", "removed")
        ran = 0
        for state, fields in self.STATES.items():
            for name in names:
                for writer in self.WRITERS:
                    wanted = self.allowed(state, writer, name)
                    if wanted is None:
                        continue
                    with self.subTest(state=state, to=name, by=writer):
                        self.put(**fields)
                        patch, raw = self.target(name, state)
                        done = self.set("E-a1-1", patch, writer, self.page if raw else None)
                        ran += 1
                        self.assertEqual(done.returncode == 0, wanted, (done.stdout, done.stderr))
                        if not wanted:
                            self.assertEqual(self.evidence()["status"], fields["status"])
                            self.assertTrue((done.stdout + done.stderr).strip(), "a refusal says what to do next")
        self.assertGreater(ran, 200)

    def test_s14_a_refusal_names_the_next_action(self):
        self.put(**self.STATES["counts"])
        done = self.set("E-a1-1", {"status": "unverified", "reason": "x"}, COORD)
        self.refused(done, "counts", "unverified")
        self.assertRegex(done.stderr, r"\. \S")

    def test_s14_a_missing_by_on_an_evidence_set_is_refused_with_the_next_action(self):
        self.started()
        self.refused(self.set("E-a1-1", {"status": "unverified", "reason": "x"}), "--by")

    def test_s14_the_timeout_says_how_long_to_wait(self):
        self.put(**self.STATES["checking, recent"])
        self.refused(self.set("E-a1-1", {"status": "unverified", "reason": "verifier did not finish"}, COORD), "30")

    def test_s14_the_timeout_leaves_the_verifier_and_drops_since(self):
        self.put(**self.STATES["checking, stale"])
        self.ok(self.set("E-a1-1", {"status": "unverified", "reason": "verifier did not finish"}, COORD))
        record = self.evidence()
        self.assertEqual((record["status"], record["verifier"], record["tries"]), ("unverified", "v1", ["v1"]))
        self.assertNotIn("since", record)

    def test_s14_a_retry_sets_a_new_verifier_since_and_clears_the_reason(self):
        self.put(**self.STATES["not reachable, one try"])
        self.ok(self.set("E-a1-1", {"status": "checking", "verifier": "v2"}, COORD))
        record = self.evidence()
        self.assertEqual((record["status"], record["verifier"], record["tries"]), ("checking", "v2", ["v1", "v2"]))
        self.assertIn("since", record)
        self.assertNotIn("reason", record)

    def test_s14_a_third_try_is_refused(self):
        self.put(**self.STATES["not reachable, two tries"])
        self.refused(self.set("E-a1-1", {"status": "checking", "verifier": "v3"}, COORD), "two", "unverified")

    def test_s14_a_retry_needs_a_new_verifier(self):
        self.put(**self.STATES["not reachable, one try"])
        self.refused(self.set("E-a1-1", {"status": "checking"}, COORD), "verifier")
        self.refused(self.set("E-a1-1", {"status": "checking", "verifier": "v1"}, COORD), "v1", "tries")

    def test_s14_removing_needs_a_reason_that_names_the_users_event(self):
        self.started()
        self.refused(self.set("E-a1-1", {"status": "removed", "reason": "I did not like it"}, COORD), "remove")
        self.refused(self.set("E-a1-1", {"status": "removed", "reason": "the user asked: remove zz9"}, COORD), "remove")
        self.ok(self.set("E-a1-1", {"status": "removed", "reason": "the user asked (m1)"}, COORD))
        record = self.evidence()
        self.assertEqual(record["status"], "removed")
        self.assertEqual(record["words"], R.EVIDENCE["words"])
        self.assertNotIn("since", record)

    def test_s14_removing_counting_evidence_drops_what_only_counting_holds(self):
        self.put(**self.STATES["counts"])
        self.ok(self.set("E-a1-1", {"status": "removed", "reason": "the user asked (m1)"}, COORD))
        record = self.evidence()
        for field in ("checked_read", "span", "sha256"):
            self.assertNotIn(field, record)

    def test_s14_a_redact_request_names_the_evidence_too(self):
        self.started()
        self.ok(self.set("E-a1-1", {"status": "removed", "reason": "the user asked: redact d1"}, COORD))

    def test_s14_a_remove_event_for_other_evidence_does_not_count(self):
        with open(self.folder / "conversation.jsonl", "a") as out:
            out.write(json.dumps(R.event("remove", id="m2", record="E-a1-9")) + "\n")
        self.started()
        self.refused(self.set("E-a1-1", {"status": "removed", "reason": "the user asked (m2)"}, COORD), "remove")

    def test_s14_removed_is_final(self):
        self.put(**self.STATES["removed"])
        self.refused(self.set("E-a1-1", {"status": "checking", "verifier": "v3"}, COORD), "removed")

    def test_s15_a_replaced_verifier_is_told_to_stop(self):
        self.put(status="checking", verifier="v2", tries=["v1", "v2"], since=ago(1))
        done = self.counts(by="v1")
        self.refused(done, "you were replaced by v2: stop")
        self.assertEqual(self.evidence()["status"], "checking")

    def test_s15_the_replaced_verifier_is_told_even_after_the_outcome(self):
        self.put(status="unverified", verifier="v2", tries=["v1", "v2"], reason="reworded")
        self.refused(self.counts(by="v1"), "you were replaced by v2: stop")

    def test_s15_a_name_that_was_never_started_is_not_a_replaced_verifier(self):
        self.started()
        done = self.counts(by="stranger")
        self.refused(done, "v1")
        self.assertNotIn("replaced", done.stdout + done.stderr)


class VerifierFields(Rules):
    def test_s16_the_verifier_cannot_change_once_the_status_is_not_checking(self):
        for status, extra in (
            ("counts", dict(checked_read="raw", span=SPAN, sha256="a" * 64)),
            ("unverified", dict(reason="reworded")),
            ("not reachable", dict(reason="HTTP 503")),
        ):
            with self.subTest(status):
                self.put(status=status, verifier="v1", tries=["v1"], **extra)
                self.refused(self.set("E-a1-1", {"verifier": "v2"}, COORD), "checking")
                self.assertEqual(self.evidence()["verifier"], "v1")

    def test_s100_the_coordinator_starts_a_verifier_and_since_is_stamped(self):
        self.ok(self.set("E-a1-1", {"verifier": "v1"}, COORD))
        record = self.evidence()
        self.assertEqual((record["verifier"], record["tries"]), ("v1", ["v1"]))
        self.assertRegex(record["since"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertNotEqual(record["since"], R.AT)

    def test_s100_a_later_verifier_is_appended_to_tries(self):
        self.started("v1")
        self.ok(self.set("E-a1-1", {"verifier": "v2"}, COORD))
        self.assertEqual(self.evidence()["tries"], ["v1", "v2"])

    def test_s100_a_verifier_already_in_tries_is_refused(self):
        self.put(status="checking", verifier="v2", tries=["v1", "v2"], since=ago(1))
        self.refused(self.set("E-a1-1", {"verifier": "v1"}, COORD), "v1", "tries")
        self.refused(self.set("E-a1-1", {"verifier": "v2"}, COORD), "v2", "tries")

    def test_s100_only_the_coordinator_sets_verifier_or_since(self):
        self.started()
        for writer in ("v1", "a1", "v9"):
            for fields in ({"verifier": "v9"}, {"since": ago(0)}):
                with self.subTest(writer=writer, fields=fields):
                    self.refused(self.set("E-a1-1", fields, writer), "coordinator")

    def test_s100_the_coordinator_may_set_since(self):
        self.started()
        self.ok(self.set("E-a1-1", {"since": ago(3)}, COORD))

    def test_s100_tries_is_kept_by_better_pyz(self):
        self.started()
        self.refused(self.set("E-a1-1", {"tries": ["v1", "v7"]}, COORD), "tries")

    def test_s100_since_goes_when_the_status_leaves_checking_whoever_writes(self):
        self.started()
        self.ok(self.set("E-a1-1", {"status": "not reachable", "reason": "HTTP 500"}, "v1"))
        self.assertNotIn("since", self.evidence())
        self.ok(self.set("E-a1-1", {"status": "checking", "verifier": "v2"}, COORD))
        self.assertIn("since", self.evidence())
        self.ok(self.counts(by="v2"))
        self.assertNotIn("since", self.evidence())

    def test_other_fields_of_evidence_need_a_by_too(self):
        self.refused(self.set("E-a1-1", {"kind": "did"}), "--by")


class Urls(Rules):
    def source(self, url, by="a1"):
        origin = {"type": "web", "url": url, "read": "raw"}
        return self.add("source", {"origin": origin, "title": "A page"}, by)

    def test_s17_public_addresses_are_accepted(self):
        for url in (
            "https://example.com/a?b=c#d",
            "http://example.org",
            "https://8.8.8.8/x",
            "http://[2001:4860:4860::8888]/",
            "https://user@example.com:8443/p",
            "https://localhost.example.com/",
            "https://100.0.0.1/",
        ):
            with self.subTest(url):
                self.ok(self.source(url))

    def test_s17_other_schemes_are_refused(self):
        for url in ("ftp://example.com/x", "file:///etc/passwd", "javascript:alert(1)", "example.com", "//example.com"):
            with self.subTest(url):
                self.assertEqual(self.source(url).returncode, 1)

    def test_s17_localhost_loopback_private_and_link_local_are_refused(self):
        for url in (
            "http://localhost/",
            "http://LOCALHOST:8080/x",
            "http://localhost./x",
            "http://app.localhost/",
            "http://127.0.0.1/",
            "http://127.1/",
            "http://127.255.255.254/",
            "http://10.0.0.1/",
            "http://172.16.5.4/",
            "http://192.168.1.1/",
            "http://169.254.169.254/latest/meta-data/",
            "http://0.0.0.0/",
            "http://100.64.0.1/",
            "http://[::1]/",
            "http://[::]/",
            "http://[fe80::1]/",
            "http://[fc00::1]/",
            "http://[::ffff:127.0.0.1]/",
            "http://[::ffff:10.0.0.1]/",
            "http://2130706433/",
            "http://0x7f.0.0.1/",
            "http://0177.0.0.1/",
            "http://user@127.0.0.1/",
            "https://example.com@localhost/",
            "http:///nohost",
            "http://127.0.0.1\\@example.com/",
            "https://example.com/\n",
        ):
            with self.subTest(url):
                done = self.source(url)
                self.assertEqual(done.returncode, 1, url)
                self.assertTrue((done.stdout + done.stderr).strip(), url)
        self.assertEqual(sorted(p.name for p in (self.folder / "sources").iterdir()), ["S-a1-1.json"])

    HOST_FORMS = (
        # (address, refused?) the forms a client such as curl reads as another host than the one the text shows
        ("http://%31%32%37.0.0.1/", True),
        ("http://%31%32%37%2e%30%2e%30%2e%31/", True),
        ("http://%6c%6f%63%61%6c%68%6f%73%74/", True),
        ("http://%2531%2532%2537.0.0.1/", True),  # still a percent sign after one reading
        ("http://example.com%2f@127.0.0.1/", True),
        ("http://exa%mple.com/", True),
        ("http://LocalHost/", True),
        ("http://localhost./", True),
        ("http://\uff11\uff12\uff17.0.0.1/", True),
        ("http://0x7f000001/", True),
        ("http://0X7F.0.0.1/", True),
        ("http://0177.0.0.1/", True),
        ("http://017700000001/", True),
        ("http://2130706433/", True),
        ("http://127.1/", True),
        ("http://127.0.1/", True),
        ("http://127.0.0.1./", True),
        ("http://[::1]/", True),
        ("http://[0:0:0:0:0:0:0:1]/", True),
        ("http://[::ffff:7f00:1]/", True),
        ("http://[::ffff:127.0.0.1]/", True),
        ("http://[::127.0.0.1]/", True),
        ("http://[::7f00:1]/", True),
        ("http://[64:ff9b::7f00:1]/", True),
        ("http://[64:ff9b::127.0.0.1]/", True),
        ("http://[64:ff9b::a00:1]/", True),
        ("http://[64:ff9b::c0a8:101]/", True),
        ("http://[64:ff9b::a9fe:a9fe]/", True),
        ("http://[fe80::1]/", True),
        ("https://example.com/\n", True),
        ("http://6425673729/", True),
        ("http://0x17f000001/", True),
        ("http://4294967296/", True),
        ("http://0x/", True),
        ("http://127.0.0.256/", True),
        ("http://1.2.3.4.5/", True),
        ("https://a1.example.com/", False),
        ("https://1password.com/", False),
        ("https://example.com", False),
        ("https://EXAMPLE.com./x", False),
        ("https://%65xample.com/", False),
        ("https://exa\u3002mple.com/", False),
        ("https://8.8.8.8/", False),
        ("http://[64:ff9b::808:808]/", False),
        ("http://[::ffff:808:808]/", False),
        ("http://[2001:4860:4860::8888]/", False),
        ("https://b\u00fccher.example/", False),
        ("https://xn--bcher-kva.example/", False),
    )

    def test_s17_every_host_form_is_judged_as_a_client_reads_it(self):
        for url, refused in self.HOST_FORMS:
            with self.subTest(url=url):
                self.assertEqual(schema.url_problem(url) is not None, refused, url)

    def test_s17_the_same_forms_through_add(self):
        for url, refused in self.HOST_FORMS[::3]:
            with self.subTest(url=url):
                done = self.source(url)
                self.assertEqual(done.returncode, 1 if refused else 0, (url, done.stdout, done.stderr))

    def test_s17_the_refusal_says_what_to_do(self):
        done = self.source("http://localhost/")
        self.refused(done, "localhost", "public")

    def test_s17_check_reports_a_source_written_by_hand(self):
        record = R.record(R.SOURCE, id="S-a1-2", origin={"type": "web", "url": "http://10.0.0.5/x", "read": "raw"})
        (self.folder / "sources" / "S-a1-2.json").write_text(json.dumps(record))
        done = self.run_("check", self.unit)
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("S-a1-2.json", done.stdout + done.stderr)

    def test_s17_the_rule_is_the_shared_one(self):
        schema_text = (HERE.parent / "src" / "better_ai" / "discover" / "schemas" / "source.schema.json").read_text(
            encoding="utf-8"
        )
        self.assertIn('"x-public-url": true', schema_text)
        self.assertFalse(hasattr(rules_evidence, "url_problem"))


class UserEvidence(Rules):
    def you(self, given=None, by=COORD, **over):
        given = given or {"type": "page", "event": "e1"}
        fields = {"origin": {"type": "you", "given": given}, "title": "You, on the page", **over}
        return self.add("source", fields, by)

    def user_evidence(self, source="S-coord-1", by=COORD, **over):
        fields = {
            "source": source,
            "words": {"type": "event", "event": "e1"},
            "kind": "say",
            "about": "your users",
            "bears_on": [{"item": "P1", "direction": "for"}],
            "status": "counts",
            **over,
        }
        return self.add("evidence", fields, by)

    def test_s19_the_coordinator_adds_a_source_from_you_and_its_evidence_counts_at_once(self):
        self.ok(self.you())
        done = self.user_evidence()
        self.ok(done)
        record = self.evidence(done.stdout.strip())
        self.assertEqual((record["status"], record.get("verifier")), ("counts", None))

    def test_s19_chat_words_work_the_same(self):
        self.ok(self.you(given={"type": "chat", "text": "I lost a week."}))
        self.ok(self.user_evidence(words={"type": "quote", "text": "I lost a week."}))

    def test_s19_only_the_coordinator_adds_a_source_from_you(self):
        for by in ("a1", "v1", "stranger"):
            with self.subTest(by):
                self.refused(self.you(by=by), "coordinator")
        self.assertEqual(len(list((self.folder / "sources").iterdir())), 1)

    def test_s19_only_the_coordinator_adds_evidence_from_you(self):
        self.ok(self.you())
        for by in ("a1", "v1"):
            with self.subTest(by):
                self.refused(self.user_evidence(by=by), "coordinator")

    def test_s19_given_must_point_to_the_users_add_evidence_event_or_hold_chat_text(self):
        self.assertNotEqual(self.you(given={"type": "page", "event": "zz9"}).returncode, 0)
        self.assertNotEqual(self.you(given={"type": "page", "event": "m1"}).returncode, 0)  # a remove event
        self.assertNotEqual(self.you(given={"type": "chat"}).returncode, 0)
        self.assertNotEqual(self.add("source", {"origin": {"type": "you"}, "title": "t"}, COORD).returncode, 0)

    def test_s19_user_evidence_is_added_with_status_counts_and_no_verifier(self):
        self.ok(self.you())
        self.refused(self.user_evidence(status="checking"), "counts")
        for extra in (
            {"verifier": "v1"},
            {"tries": ["v1"]},
            {"checked_read": "raw", "span": "x", "sha256": "a" * 64},
        ):
            with self.subTest(extra):
                self.assertEqual(self.user_evidence(**extra).returncode, 1)

    def test_s19_check_reports_user_evidence_written_by_an_analyst(self):
        self.ok(self.you())
        self.put("E-a1-2", source="S-coord-1", words={"type": "event", "event": "e1"}, status="counts")
        done = self.run_("check", self.unit)
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("E-a1-2.json", done.stdout + done.stderr)

    def test_s19_words_of_an_event_need_a_source_that_points_to_that_event(self):
        self.ok(self.you())
        self.assertEqual(self.user_evidence(words={"type": "event", "event": "e2"}).returncode, 1)
        self.assertEqual(self.user_evidence(source="S-a1-1").returncode, 1)

    def test_s14_the_coordinator_may_remove_user_evidence_with_the_users_request(self):
        self.ok(self.you())
        made = self.user_evidence().stdout.strip()
        with open(self.folder / "conversation.jsonl", "a") as out:
            out.write(json.dumps(R.event("remove", id="m5", record=made)) + "\n")
        self.ok(self.set(made, {"status": "removed", "reason": "the user asked: remove m5"}, COORD))
        self.assertEqual(self.evidence(made)["status"], "removed")

    def test_s14_user_evidence_cannot_move_to_checking_or_back(self):
        self.ok(self.you())
        made = self.user_evidence().stdout.strip()
        self.refused(self.set(made, {"status": "checking"}, COORD), "counts")
        self.refused(self.set(made, {"status": "unverified", "reason": "x"}, COORD), "counts")


class InternalSetting(Rules):
    setting = "internal"

    def you(self, **over):
        fields = {"origin": {"type": "you", "given": {"type": "page", "event": "e1"}}, "title": "You", **over}
        return self.add("source", fields, COORD)

    def test_s20_a_source_from_you_needs_said_by_role(self):
        self.refused(self.you(), "said_by_role")
        self.ok(self.you(said_by_role="the support lead"))

    def test_s20_the_evidence_from_such_a_source_needs_a_summary(self):
        self.ok(self.you(said_by_role="the support lead"))
        fields = {
            "source": "S-coord-1",
            "words": {"type": "event", "event": "e1"},
            "kind": "say",
            "about": "your users",
            "bears_on": [{"item": "P1", "direction": "for"}],
            "status": "counts",
        }
        self.refused(self.add("evidence", fields, COORD), "summary")
        self.ok(self.add("evidence", {**fields, "summary": "The support lead lost a week."}, COORD))

    def test_s20_check_reports_the_missing_role_and_summary(self):
        record = R.record(R.YOU_SOURCE, origin={"type": "you", "given": {"type": "chat", "text": "x"}})
        (self.folder / "sources" / "S-coord-1.json").write_text(json.dumps(record))
        done = self.run_("check", self.unit)
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("said_by_role", done.stdout + done.stderr)

    def test_s20_a_web_source_needs_neither(self):
        origin = {"type": "web", "url": "https://example.com/z", "read": "raw"}
        self.ok(self.add("source", {"origin": origin, "title": "z"}, "a1"))

    def test_s20_an_external_discovery_needs_neither(self):
        shutil.rmtree(self.repo)
        shutil.copytree(TEMPLATES["external"], self.repo, symlinks=True)
        self.ok(self.you())


class Writers(Rules):
    def evidence_fields(self, **over):
        return {
            "source": "S-a1-1",
            "words": {"type": "quote", "text": "A different sentence."},
            "kind": "say",
            "about": "your users",
            "bears_on": [{"item": "P1", "direction": "for"}],
            "status": "checking",
            **over,
        }

    def test_s21_the_current_checker_adds_evidence(self):
        self.ok(self.add("evidence", self.evidence_fields(), "a1"))

    def test_s21_the_coordinator_adds_evidence(self):
        self.ok(self.add("evidence", self.evidence_fields(), COORD))

    def test_s21_a_replaced_analyst_is_refused(self):
        done = self.add("evidence", self.evidence_fields(), "a2")
        self.refused(done, "a2", "P1", "a1")
        self.assertEqual(len(list((self.folder / "evidence").iterdir())), 1)

    def test_s21_the_analyst_must_check_every_item_the_evidence_bears_on(self):
        both = [{"item": "P1", "direction": "for"}, {"item": "P2", "direction": "against"}]
        self.refused(self.add("evidence", self.evidence_fields(bears_on=both), "a1"), "P2")
        self.refused(self.add("evidence", self.evidence_fields(bears_on=both), "a2"), "P1")
        self.ok(self.add("evidence", self.evidence_fields(bears_on=both), COORD))

    def test_s21_an_item_with_no_checker_has_no_analyst(self):
        fields = {"kind": "problem", "text": "Another.", "rests_on": [], "risks": []}
        self.ok(self.add("item", fields, COORD))
        bears = [{"item": "P3", "direction": "for"}]
        self.refused(self.add("evidence", self.evidence_fields(bears_on=bears), "a1"), "P3")

    def test_s21_a_released_checker_cannot_add(self):
        self.ok(self.set("P1", {"checker": None, "since": None}, COORD))
        self.refused(self.add("evidence", self.evidence_fields(), "a1"), "P1")

    def test_s21_a_source_by_a_stranger_is_not_the_writer_rule_s21(self):
        origin = {"type": "web", "url": "https://example.com/q", "read": "raw"}
        self.ok(self.add("source", {"origin": origin, "title": "q"}, "a9"))


class Duplicates(Rules):
    def fields(self, text, **over):
        return {
            "source": "S-a1-1",
            "words": {"type": "quote", "text": text},
            "kind": "say",
            "about": "your users",
            "bears_on": [{"item": "P1", "direction": "for"}],
            "status": "checking",
            **over,
        }

    def test_s22_the_same_words_from_the_same_source_are_refused_with_the_existing_id(self):
        self.refused(self.add("evidence", self.fields(QUOTE), "a1"), "already recorded as E-a1-1")

    def test_s22_normalised_words_are_the_same_words(self):
        for text in (
            "we lost a week to this",
            "  We   lost a week to  this!! ",
            "“We lost a week to this”",
            "We lost a week, to this.",
        ):
            with self.subTest(text):
                self.refused(self.add("evidence", self.fields(text), "a1"), "E-a1-1")

    def test_s22_other_words_or_another_source_are_accepted(self):
        self.ok(self.add("evidence", self.fields("We lost two weeks to this."), "a1"))
        origin = {"type": "web", "url": "https://example.com/other", "read": "raw"}
        self.ok(self.add("source", {"origin": origin, "title": "other"}, "a1"))
        self.ok(self.add("evidence", self.fields(QUOTE, source="S-a1-2"), "a1"))

    def test_s22_removed_evidence_still_counts_as_recorded(self):
        self.put(status="removed", reason="the user asked (m1)")
        self.refused(self.add("evidence", self.fields(QUOTE), "a1"), "E-a1-1")

    def test_s22_the_same_event_words_from_the_same_source_are_refused(self):
        origin = {"type": "you", "given": {"type": "page", "event": "e1"}}
        self.ok(self.add("source", {"origin": origin, "title": "you"}, COORD))
        fields = self.fields("x", source="S-coord-1", words={"type": "event", "event": "e1"}, status="counts")
        self.ok(self.add("evidence", fields, COORD))
        self.refused(self.add("evidence", fields, COORD), "already recorded as E-coord-1")


class PageEvents(Rules):
    def you(self, event, by=COORD):
        origin = {"type": "you", "given": {"type": "page", "event": event}}
        return self.add("source", {"origin": origin, "title": "you"}, by)

    def test_s85_an_event_another_record_points_to_is_refused_and_that_record_is_named(self):
        self.ok(self.you("e1"))
        done = self.you("e1")
        self.refused(done, "e1", "S-coord-1")
        self.ok(self.you("e2"))

    def test_s85_the_evidence_of_a_source_may_point_to_its_sources_event(self):
        self.ok(self.you("e1"))
        fields = {
            "source": "S-coord-1",
            "words": {"type": "event", "event": "e1"},
            "kind": "say",
            "about": "your users",
            "bears_on": [{"item": "P1", "direction": "for"}],
            "status": "counts",
        }
        self.ok(self.add("evidence", fields, COORD))

    def test_s85_evidence_may_not_point_to_an_event_of_another_source(self):
        self.ok(self.you("e1"))
        self.ok(self.you("e2"))
        fields = {
            "source": "S-coord-2",
            "words": {"type": "event", "event": "e1"},
            "kind": "say",
            "about": "your users",
            "bears_on": [{"item": "P1", "direction": "for"}],
            "status": "counts",
        }
        self.refused(self.add("evidence", fields, COORD), "e1", "S-coord-1")

    def test_s85_any_record_type_counts(self):
        self.ok(self.you("e1"))
        line = R.record(
            R.DECISION,
            id="D1",
            status="answered",
            answer={"type": "page", "event": "e1"},
            answered_at=R.AT,
        )
        with open(self.folder / "decisions.jsonl", "a") as out:
            out.write(json.dumps(line) + "\n")
        self.refused(self.you("e1"), "e1", "D1")


class Web(Rules):
    def fields(self, **over):
        return {
            "source": "S-a1-1",
            "words": {"type": "quote", "text": "A new sentence."},
            "kind": "say",
            "about": "your users",
            "bears_on": [{"item": "P1", "direction": "for"}],
            "status": "checking",
            **over,
        }

    def test_s99_new_web_evidence_starts_checking_without_verifier_fields(self):
        self.ok(self.add("evidence", self.fields(), "a1"))
        for who in ("a1", COORD):
            for extra in (
                {"status": "counts"},
                {"status": "unverified", "reason": "x"},
                {"status": "removed", "reason": "x"},
                {"verifier": "v1"},
                {"tries": ["v1"]},
                {"since": ago(1)},
                {"checked_read": "raw"},
                {"span": "x"},
                {"sha256": "a" * 64},
                {"status": "counts", "verifier": "v1", "checked_read": "raw", "span": "x", "sha256": "a" * 64},
            ):
                with self.subTest(who=who, extra=extra):
                    done = self.add(
                        "evidence", self.fields(words={"type": "quote", "text": f"x {extra}"}, **extra), who
                    )
                    self.assertEqual(done.returncode, 1, extra)
        self.assertEqual(len(list((self.folder / "evidence").iterdir())), 2)

    def test_s99_check_reports_web_evidence_that_counts_without_a_verifier_who_read_the_page(self):
        cases = {
            "E-a1-2": dict(status="counts"),
            "E-a1-3": dict(
                status="counts", verifier="a1", tries=["a1"], checked_read="raw", span=SPAN, sha256="a" * 64
            ),
            "E-a1-4": dict(
                status="counts", verifier="v1", tries=["v1"], checked_read="raw", span="elsewhere", sha256="a" * 64
            ),
        }
        for ident, fields in cases.items():
            self.put(ident, words={"type": "quote", "text": f"{QUOTE} {ident}"}, **fields)
        done = self.run_("check", self.unit)
        self.assertEqual(done.returncode, 1, done.stdout)
        text = done.stdout + done.stderr
        for ident in cases:
            self.assertIn(f"{ident}.json", text)

    def test_check_accepts_what_the_flow_makes(self):
        self.started()
        self.ok(self.counts())
        done = self.run_("check", self.unit)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


class FieldTable(Rules):
    """One table of who may write each field of evidence and of a source, in which status, and that nothing else may:
    every field, as a patch and as an unset, as every writer, in every status."""

    STATES = {
        k: Transitions.STATES[k]
        for k in (
            "checking, recent",
            "checking, no verifier",
            "not reachable, one try",
            "counts",
            "unverified",
            "removed",
        )
    }
    WRITERS = (None, "v1", "a1", "a2", COORD)
    VALUES = {
        "source": "S-a1-2",
        "words": {"type": "quote", "text": "A wholly other sentence."},
        "bears_on": [{"item": "P1", "direction": "against"}],
        "kind": "did",
        "about": "elsewhere",
        "summary": "A summary.",
        "verifier": "v9",
        "since": ago(2),
        "tries": ["x"],
        "reason": "because",
        "checked_read": "extracted",
        "span": "another span",
        "sha256": "b" * 64,
    }

    def setUp(self):
        super().setUp()
        origin = {"type": "web", "url": "https://example.com/two", "read": "raw"}
        self.ok(self.add("source", {"origin": origin, "title": "two"}, "a1"))

    @staticmethod
    def allowed(field, mode, state, writer, present):
        """The table, written out apart from the code. For evidence whose own analyst is a1."""
        if writer is None:
            return False
        was = Transitions.STATES[state]["status"]
        if mode == "unset":
            return field not in present  # nothing to remove is not a change; anything present stays
        if field in ("source", "words", "bears_on", "kind", "about"):
            return was == "checking" and writer in (COORD, "a1")
        if field == "summary":
            return writer == COORD and was in ("checking", "counts")
        if field == "verifier":
            return writer == COORD and was == "checking"
        if field == "since":  # only while a verifier runs
            return writer == COORD and was == "checking" and "verifier" in present
        return False  # tries, sha256, reason, checked_read, span: set only by a change of status, or by better.pyz

    def test_every_field_as_every_writer_in_every_status(self):
        ran = 0
        for state, fields in self.STATES.items():
            for field, value in self.VALUES.items():
                for mode in ("patch", "unset"):
                    for writer in self.WRITERS:
                        with self.subTest(state=state, field=field, mode=mode, by=writer):
                            self.put(**fields)
                            before = (self.folder / "evidence" / "E-a1-1.json").read_text()
                            present = set(json.loads(before))
                            if mode == "patch":
                                done = self.set("E-a1-1", {field: value}, writer)
                            else:
                                done = self.set("E-a1-1", {}, writer, unset=[field])
                            ran += 1
                            wanted = self.allowed(field, mode, state, writer, present)
                            self.assertEqual(done.returncode == 0, wanted, (done.stdout, done.stderr))
                            after = (self.folder / "evidence" / "E-a1-1.json").read_text()
                            if not wanted:
                                self.assertEqual(after, before)
        self.assertGreater(ran, 700)

    def test_the_verifier_cannot_replace_the_words_in_the_set_that_counts_them(self):
        self.started()
        words = {"type": "quote", "text": "We lost a week to this. And more."}
        self.refused(self.counts(words=words), "words")
        self.assertEqual(self.evidence()["status"], "checking")

    def test_the_coordinator_cannot_change_words_in_the_set_that_leaves_checking(self):
        self.started()
        fields = {"status": "unverified", "reason": "reworded", "words": self.VALUES["words"]}
        self.refused(self.set("E-a1-1", fields, "v1"), "words")
        fields = {"status": "removed", "reason": "the user asked (m1)", "words": self.VALUES["words"]}
        self.refused(self.set("E-a1-1", fields, COORD), "words")

    def test_the_words_that_will_be_stored_must_meet_the_rules(self):
        self.started()
        self.ok(self.set("E-a1-1", {"words": {"type": "quote", "text": "In the end, we lost a week"}}, COORD))
        self.ok(self.counts(span=SPAN))
        self.assertEqual(self.evidence()["status"], "counts")

    def test_new_words_cannot_repeat_other_evidence(self):
        fields = {
            "source": "S-a1-1",
            "words": {"type": "quote", "text": "Other words."},
            "kind": "say",
            "about": "your users",
            "bears_on": [{"item": "P1", "direction": "for"}],
            "status": "checking",
        }
        self.ok(self.add("evidence", fields, "a1"))
        self.refused(self.set("E-a1-2", {"words": {"type": "quote", "text": QUOTE}}, "a1"), "E-a1-1")

    def test_an_analyst_may_not_point_evidence_at_an_item_it_does_not_check(self):
        both = [{"item": "P1", "direction": "for"}, {"item": "P2", "direction": "for"}]
        self.refused(self.set("E-a1-1", {"bears_on": both}, "a1"), "P2")
        self.ok(self.set("E-a1-1", {"bears_on": both}, COORD))

    def test_the_evidence_must_bear_on_something_unless_the_coordinator_adds_it(self):
        fields = {
            "source": "S-a1-1",
            "words": {"type": "quote", "text": "Other words."},
            "kind": "say",
            "about": "your users",
            "bears_on": [],
            "status": "checking",
        }
        self.refused(self.add("evidence", fields, "a1"), "bears")
        self.ok(self.add("evidence", fields, COORD))
        self.refused(self.set("E-a1-1", {"bears_on": []}, "a1"), "bears")

    def test_a_source_has_its_own_table(self):
        origin = {"type": "web", "url": "https://example.com/other", "read": "snippet"}
        values = {"origin": origin, "title": "A new title", "said_by_role": "a role"}
        for field, value in values.items():
            for mode in ("patch", "unset"):
                for writer in (None, "a1", "a2", "v1", COORD):
                    with self.subTest(field=field, mode=mode, by=writer):
                        path = self.folder / "sources" / "S-a1-1.json"
                        before = path.read_text()
                        if mode == "patch":
                            done = self.set("S-a1-1", {field: value}, writer)
                        else:
                            done = self.set("S-a1-1", {}, writer, unset=[field])
                        if mode == "unset":
                            wanted = writer is not None and field == "said_by_role"  # nothing there to remove
                        elif field == "origin":
                            wanted = False
                        elif field == "title":
                            wanted = writer in ("a1", COORD)
                        else:
                            wanted = writer == COORD
                        self.assertEqual(done.returncode == 0, wanted, (done.stdout, done.stderr))
                        if not wanted:
                            self.assertEqual(path.read_text(), before)
                        else:
                            path.write_text(before)


class Hardening(Rules):
    def test_removal_may_name_a_decision_answered_with_exactly_remove_the_id(self):
        self.started()
        line = R.record(
            R.DECISION,
            id="D1",
            about={"type": "evidence", "evidence": "E-a1-1"},
            status="answered",
            answer={"type": "chat", "text": "remove E-a1-1"},
            answered_at=R.AT,
        )
        with open(self.folder / "decisions.jsonl", "a") as out:
            out.write(json.dumps(line) + "\n")
        self.ok(self.set("E-a1-1", {"status": "removed", "reason": "the user answered D1"}, COORD))

    def test_a_decision_answered_with_other_words_is_not_a_removal_request(self):
        self.started()
        line = R.record(
            R.DECISION,
            id="D1",
            about={"type": "evidence", "evidence": "E-a1-1"},
            status="answered",
            answer={"type": "chat", "text": "keep it, but tell me more"},
            answered_at=R.AT,
        )
        with open(self.folder / "decisions.jsonl", "a") as out:
            out.write(json.dumps(line) + "\n")
        self.refused(self.set("E-a1-1", {"status": "removed", "reason": "the user answered D1"}, COORD), "remove")

    def test_the_quote_matches_the_span_on_word_boundaries(self):
        self.page.write_text("Note: We lost a week to thisandthat.")
        self.started()
        self.refused(self.counts(span="We lost a week to thisandthat"), "quote")
        self.page.write_text("Note: Why we lost a week to this, again?")
        self.ok(self.counts(span="Why we lost a week to this, again"))

    def test_the_coordinator_is_never_the_verifier(self):
        self.refused(self.set("E-a1-1", {"verifier": COORD}, COORD), "coordinator")

    def test_check_reports_counting_evidence_whose_verifier_is_the_coordinator(self):
        self.put(status="counts", verifier=COORD, tries=[COORD], checked_read="raw", span=SPAN, sha256="a" * 64)
        done = self.run_("check", self.unit)
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("E-a1-1.json", done.stdout + done.stderr)

    def test_the_check_reports_a_quote_that_is_only_inside_a_word_of_the_span(self):
        span = "We lost a week to thisandthat"
        self.put(status="counts", verifier="v1", tries=["v1"], checked_read="raw", span=span, sha256="a" * 64)
        self.assertEqual(self.run_("check", self.unit).returncode, 1)

    def test_hosts_are_normalised_before_the_rule_reads_them(self):
        for url in (
            "http://\uff11\uff12\uff17.0.0.1/",
            "http://\uff12\uff11\uff13\uff10\uff17\uff10\uff16\uff14\uff13\uff13/",
            "http://a..b/",
            "http://exa\u3002mple.com./x",
            "http://[::127.0.0.1]/",
            "http://[::7f00:1]/",
            "http://[::10.1.2.3]/",
        ):
            with self.subTest(url):
                origin = {"type": "web", "url": url, "read": "raw"}
                done = self.add("source", {"origin": origin, "title": "x"}, "a1")
                if "exa" in url:  # a full-width dot is an ordinary dot: a public name
                    continue
                self.assertEqual(done.returncode, 1, url)

    def test_an_international_name_is_a_public_host(self):
        origin = {"type": "web", "url": "https://b\u00fccher.example/x", "read": "raw"}
        self.ok(self.add("source", {"origin": origin, "title": "x"}, "a1"))


class Last(Rules):
    def test_since_is_set_only_while_a_verifier_runs(self):
        self.refused(self.set("E-a1-1", {"since": ago(2)}, COORD), "verifier")
        self.ok(self.set("E-a1-1", {"verifier": "v1"}, COORD))
        self.ok(self.set("E-a1-1", {"since": ago(2)}, COORD))

    def test_the_timeout_needs_a_verifier(self):
        self.put(status="checking", since=ago(60))
        done = self.set("E-a1-1", {"status": "unverified", "reason": "verifier did not finish"}, COORD)
        self.refused(done, "verifier")

    def test_check_reports_the_coordinator_as_verifier_in_any_status(self):
        for status, extra in (
            ("checking", {}),
            ("unverified", {"reason": "reworded"}),
            ("not reachable", {"reason": "HTTP 503"}),
        ):
            with self.subTest(status):
                self.put(
                    status=status,
                    verifier=COORD,
                    tries=[COORD],
                    **({"since": ago(1)} if status == "checking" else {}),
                    **extra,
                )
                done = self.run_("check", self.unit)
                self.assertEqual(done.returncode, 1, done.stdout)
                self.assertIn("E-a1-1.json", done.stdout + done.stderr)

    def test_check_reports_since_without_a_verifier(self):
        self.put(status="checking", since=ago(1))
        self.assertEqual(self.run_("check", self.unit).returncode, 1)


class FileCase(Rules):
    """What the tests of files and tools share: the named sources and the sources an analyst adds."""

    NAMED = [{"type": "file", "path": "/data/tickets"}, {"type": "tool", "tool": "mcp__desk__get_ticket"}]

    def name(self):
        self.ok(self.set("discover", {"named_sources": self.NAMED}, COORD))

    def file(self, path, by="a1"):
        return self.add("source", {"origin": {"type": "file", "path": path, "read": "raw"}, "title": "Tickets"}, by)

    def tool(self, tool="mcp__desk__get_ticket", by="a1"):
        origin = {"type": "tool", "tool": tool, "ref": "T-1042", "read": "extracted"}
        return self.add("source", {"origin": origin, "title": "A ticket"}, by)


class Named(FileCase):
    """Files and tools the user named (S129) and the sources an analyst may add from them (S125)."""

    def test_s129_only_the_coordinator_sets_named_sources(self):
        self.refused(self.set("discover", {"named_sources": self.NAMED}, "a1"), "named_sources", COORD)
        self.refused(self.set("discover", {"named_sources": self.NAMED}), "named_sources")
        self.name()
        self.assertEqual(json.loads((self.folder / "discover.json").read_text())["named_sources"], self.NAMED)

    def test_s129_no_other_way_to_change_them_gets_past_the_rule(self):
        self.name()
        before = (self.folder / "discover.json").read_bytes()
        for by in ("a1", "v1", None):
            with self.subTest(by=by):
                self.refused(self.set("discover", {"named_sources": None}, by), "named_sources")
                self.refused(self.set("discover", {}, by, unset=["named_sources"]), "named_sources")
                self.refused(self.set("discover", {"named_sources": []}, by), "named_sources")
        self.assertEqual((self.folder / "discover.json").read_bytes(), before)

    def test_s129_the_coordinator_adds_named_sources_and_none_goes_once_named(self):
        self.name()
        more = [*self.NAMED, {"type": "file", "path": "/data/notes"}]
        self.ok(self.set("discover", {"named_sources": more}, COORD))
        self.refused(self.set("discover", {"named_sources": self.NAMED}, COORD), "stays named")
        self.refused(self.set("discover", {"named_sources": None}, COORD), "stays named")
        self.refused(self.set("discover", {}, COORD, unset=["named_sources"]), "stays named")

    def test_s129_an_analyst_adds_a_file_source_only_for_a_named_path_or_inside_a_named_folder(self):
        self.name()
        for path in ("/data/tickets", "/data/tickets/q3.csv", "/data/tickets/2026/q3.csv"):
            with self.subTest(path=path):
                self.ok(self.file(path))
        for path in ("/data/tickets-old/q3.csv", "/data", "/data/other.csv", "/data/tickets/../other.csv"):
            with self.subTest(path=path):
                self.refused(self.file(path), "named")

    def test_s129_a_named_file_matches_by_path_segments(self):
        self.ok(self.set("discover", {"named_sources": [{"type": "file", "path": "/data/q3.csv"}]}, COORD))
        self.ok(self.file("/data/q3.csv"))
        self.refused(self.file("/data/q3.csv.bak"), "named")

    def test_s129_an_analyst_adds_a_tool_source_only_for_a_named_tool(self):
        self.name()
        self.ok(self.tool())
        self.refused(self.tool("mcp__desk__delete_ticket"), "named")

    def test_s129_nothing_is_named_so_nothing_is_added(self):
        self.refused(self.file("/data/tickets/q3.csv"), "named")
        self.refused(self.tool(), "named")

    def test_s129_check_reports_a_file_source_written_by_hand_for_an_unnamed_path(self):
        self.name()
        record = R.record(
            R.SOURCE,
            id="S-a1-2",
            by="a1",
            origin={"type": "file", "path": "/elsewhere/q3.csv", "read": "raw"},
            title="Tickets",
        )
        (self.folder / "sources" / "S-a1-2.json").write_text(json.dumps(record))
        done = self.run_("check", self.unit)
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("S-a1-2.json", done.stdout + done.stderr)

    def test_s125_the_coordinator_may_add_any_file_or_tool_source(self):
        self.ok(self.file("/anywhere/q3.csv", by=COORD))


class Sourced(FileCase):
    """A file source S-a1-2 and a tool source S-a1-3, named, and a raw file to count against."""

    RAW = "Ticket 1: the report took a week to find.\nTicket 2: nothing.\n"
    QUOTE = "the report took a week to find"

    def setUp(self):
        super().setUp()
        self.name()
        self.ok(self.file("/data/tickets/q3.csv"))
        self.ok(self.tool())
        self.raw = self.repo.parent / "raw.txt"
        self.raw.write_text(self.RAW)

    def evidence_from(self, source, words=None, kind="say", **over):
        fields = {
            "source": source,
            "words": {"type": "quote", "text": words or self.QUOTE},
            "kind": kind,
            "about": "your users",
            "bears_on": [{"item": "P1", "direction": "for"}],
            "status": "checking",
            **over,
        }
        return self.add("evidence", fields, "a1")


class FromFiles(Sourced):
    """Evidence from a file or a tool: the quote flow of a web page, without the URL rule (S126)."""

    def test_s126_a_verifier_counts_a_quote_from_a_file_or_a_tool_with_the_raw_file(self):
        for source, ident in (("S-a1-2", "E-a1-2"), ("S-a1-3", "E-a1-3")):
            with self.subTest(source=source):
                self.ok(self.evidence_from(source, words=self.QUOTE + (" " if ident == "E-a1-3" else "")))
                self.ok(self.set(ident, {"verifier": "v1"}, COORD))
                done = self.set(
                    ident, {"status": "counts", "checked_read": "raw", "span": self.RAW.splitlines()[0]}, "v1", self.raw
                )
                self.ok(done)
                record = self.evidence(ident)
                self.assertEqual(record["status"], "counts")
                self.assertEqual(record["sha256"], hashlib.sha256(self.RAW.encode()).hexdigest())
                self.ok(self.run_("check", self.unit))

    def test_s126_the_span_must_occur_in_the_raw_file(self):
        self.ok(self.evidence_from("S-a1-2"))
        self.ok(self.set("E-a1-2", {"verifier": "v1"}, COORD))
        done = self.set(
            "E-a1-2",
            {"status": "counts", "checked_read": "raw", "span": "the report took a week to find!"},
            "v1",
            self.raw,
        )
        self.refused(done, "span")
        self.refused(self.set("E-a1-2", {"status": "counts", "checked_read": "raw", "span": self.QUOTE}, "v1"), "--raw")
        self.assertEqual(self.evidence("E-a1-2")["status"], "checking")

    def test_s126_counts_by_hand_without_the_checks_is_reported_by_check(self):
        self.ok(self.evidence_from("S-a1-2"))
        self.put(
            "E-a1-2",
            source="S-a1-2",
            words={"type": "quote", "text": self.QUOTE},
            status="counts",
            verifier="v1",
            checked_read="raw",
            span="something else",
            sha256="a" * 64,
        )
        self.assertEqual(self.run_("check", self.unit).returncode, 1)

    def test_s126_the_url_rule_is_not_applied_to_a_file_or_tool(self):
        origin = {"type": "tool", "tool": "mcp__desk__get_ticket", "ref": "http://localhost:8080/t/1", "read": "raw"}
        self.ok(self.add("source", {"origin": origin, "title": "A ticket"}, "a1"))
        self.ok(self.file("/data/tickets/localhost/127.0.0.1.csv"))

    def test_s126_new_evidence_from_a_file_starts_checking_with_no_verifier_fields(self):
        self.refused(self.evidence_from("S-a1-2", status="counts"), "checking")
        self.refused(self.evidence_from("S-a1-2", verifier="v1"), "checking")


class Computed(Sourced):
    """A result computed from the user's data counts once the user takes the default of a question about it (S128)."""

    WORDS = "wc -l tickets.csv => 37"
    DEFAULT = "Confirm this result"

    def setUp(self):
        super().setUp()
        self.ok(self.evidence_from("S-a1-2", words=self.WORDS, kind="data"))

    def ask(self, evidence="E-a1-2", default=None, about=None):
        about = about or {"type": "evidence", "evidence": evidence}
        asked = f"Is the result of {evidence} right?"
        fields = R.without(
            R.record(R.DECISION, about=about, asked=asked, default=default or self.DEFAULT), "at", "by", "id"
        )
        return self.ok(self.add("decision", fields, COORD))

    def answer(self, decision="D1", taken=True, event="a9"):
        with (self.folder / "conversation.jsonl").open("a") as out:
            line = {"type": "answer", "at": R.AT, "by": "user", "id": event, "decision": decision}
            line |= {"text": self.DEFAULT if taken else "Not sure", "default": taken}
            out.write(json.dumps(line) + "\n")
        done = self.set(decision, {"status": "answered", "answer": {"type": "page", "event": event}}, COORD)
        self.ok(done)

    def confirm(self, by=COORD, raw=None):
        return self.set("E-a1-2", {"status": "counts"}, by, raw)

    def test_s128_the_coordinator_sets_counts_once_the_user_took_the_default_and_nothing_is_run(self):
        self.ask()
        self.answer()
        self.ok(self.confirm())
        record = self.evidence("E-a1-2")
        self.assertEqual(record["status"], "counts")
        for name in ("verifier", "sha256", "span"):
            self.assertNotIn(name, record)
        self.ok(self.run_("check", self.unit))

    def test_s128_a_typed_default_in_the_chat_counts_too(self):
        self.ask()
        self.ok(self.set("D1", {"status": "answered", "answer": {"type": "chat", "text": self.DEFAULT}}, COORD))
        self.ok(self.confirm())

    def test_s128_no_question_a_waiting_question_or_another_answer_is_refused(self):
        self.refused(self.confirm(), "Confirm this result")
        self.ask()
        self.refused(self.confirm(), "answered")
        self.answer(taken=False)
        self.refused(self.confirm(), "default")
        self.assertEqual(self.evidence("E-a1-2")["status"], "checking")

    def test_s128_a_chat_answer_in_other_words_is_refused(self):
        self.ask()
        self.ok(self.set("D1", {"status": "answered", "answer": {"type": "chat", "text": "yes"}}, COORD))
        self.refused(self.confirm(), "default")

    def test_s128_the_question_must_be_about_this_evidence(self):
        self.ok(self.evidence_from("S-a1-3", words="grep -c late tickets.csv => 12", kind="data"))
        self.ask(evidence="E-a1-3")
        self.answer()
        self.refused(self.confirm(), "E-a1-2")
        self.ask(about={"type": "item", "item": "P1"})
        self.answer("D2", event="a8")
        self.refused(self.confirm(), "E-a1-2")

    def test_s128_a_question_with_another_default_is_refused(self):
        self.ask(default="Yes")
        self.answer()
        self.refused(self.confirm(), "Confirm this result")

    def test_s128_a_verifier_or_an_analyst_never_counts_it_and_no_raw_file_helps(self):
        self.ask()
        self.answer()
        self.refused(self.confirm("a1"), "coordinator")
        self.ok(self.set("E-a1-2", {"verifier": "v1"}, COORD))
        fields = {"status": "counts", "checked_read": "raw", "span": self.WORDS}
        self.refused(self.set("E-a1-2", fields, "v1", self.raw), "coordinator")
        self.refused(self.set("E-a1-2", {"status": "counts"}, COORD, self.raw), "--raw")

    def test_s128_the_coordinator_sets_it_unverified_when_the_user_does_not_confirm(self):
        self.refused(self.set("E-a1-2", {"status": "unverified", "reason": "no"}, COORD), "not confirmed by you")
        self.ok(self.set("E-a1-2", {"status": "unverified", "reason": "not confirmed by you"}, COORD))

    def test_s128_check_reports_computed_evidence_counting_with_no_confirmation(self):
        self.put("E-a1-2", source="S-a1-2", words={"type": "quote", "text": self.WORDS}, kind="data", status="counts")
        done = self.run_("check", self.unit)
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("E-a1-2.json", done.stdout + done.stderr)

    def test_s128_a_quote_of_kind_data_from_a_web_page_still_needs_a_verifier(self):
        self.ask(evidence="E-a1-1")
        self.answer()
        self.refused(self.set("E-a1-1", {"status": "counts"}, COORD), "verifier")


class NotFoundAndCorrected(Rules):
    """#126: a quote that is not on the page is `not found`; a reworded one is `reworded` with the page's words, and the
    coordinator adds the corrected quote as new evidence that `corrects` it and goes through the check again."""

    PAGE_WORDS = "In the end, we lost a whole week."

    def reword(self, by="v1"):
        return self.set("E-a1-1", {"status": "reworded", "reason": "reworded", "page_words": self.PAGE_WORDS}, by)

    def corrected(self, **over):
        return {
            "source": "S-a1-1",
            "words": {"type": "quote", "text": self.PAGE_WORDS},
            "kind": "say",
            "about": "your users",
            "bears_on": [{"item": "P1", "direction": "for"}],
            "status": "checking",
            "corrects": "E-a1-1",
            **over,
        }

    def test_the_verifier_sets_not_found_with_its_reason(self):
        self.started()
        self.ok(self.set("E-a1-1", {"status": "not found", "reason": "not on the page"}, "v1"))
        self.assertEqual(self.evidence()["status"], "not found")
        self.assertNotIn("since", self.evidence())

    def test_not_found_needs_a_reason_and_only_the_verifier_sets_it(self):
        self.started()
        self.refused(self.set("E-a1-1", {"status": "not found"}, "v1"), "reason")
        self.refused(self.set("E-a1-1", {"status": "not found", "reason": "not on the page"}, COORD), "verifier")
        self.refused(self.set("E-a1-1", {"status": "not found", "reason": "not on the page"}, "a1"), "verifier")

    def test_not_found_is_final_but_for_removal(self):
        self.put(status="not found", verifier="v1", tries=["v1"], reason="not on the page")
        self.refused(self.set("E-a1-1", {"status": "checking", "verifier": "v2"}, COORD))
        self.ok(self.set("E-a1-1", {"status": "removed", "reason": "the user asked: remove m1"}, COORD))

    def test_the_verifier_sets_reworded_with_the_pages_words(self):
        self.started()
        self.ok(self.reword())
        record = self.evidence()
        self.assertEqual((record["status"], record["page_words"]), ("reworded", self.PAGE_WORDS))

    def test_reworded_needs_the_pages_words_and_only_with_reworded(self):
        self.started()
        self.refused(self.set("E-a1-1", {"status": "reworded", "reason": "reworded"}, "v1"), "page_words")
        self.refused(
            self.set("E-a1-1", {"status": "not found", "reason": "x", "page_words": self.PAGE_WORDS}, "v1"),
            "page_words",
        )
        self.refused(self.reword(COORD), "verifier")

    def test_the_coordinator_adds_the_corrected_quote_and_it_starts_checking(self):
        self.started()
        self.ok(self.reword())
        done = self.add("evidence", self.corrected(), COORD)
        self.ok(done)
        self.assertEqual(self.evidence("E-coord-1")["corrects"], "E-a1-1")
        self.assertEqual(self.evidence("E-coord-1")["status"], "checking")

    def test_a_correction_must_point_to_reworded_evidence_and_hold_its_page_words(self):
        self.started()
        self.refused(self.add("evidence", self.corrected(), COORD), "reworded")
        self.ok(self.reword())
        wrong = self.corrected(words={"type": "quote", "text": "Something the page never said."})
        self.refused(self.add("evidence", wrong, COORD), "page_words")
        self.refused(self.add("evidence", self.corrected(source="S-a1-2"), COORD), "source")

    def test_only_the_coordinator_corrects_and_only_once(self):
        self.started()
        self.ok(self.reword())
        self.refused(self.add("evidence", self.corrected(), "a1"), "coordinator")
        self.ok(self.add("evidence", self.corrected(), COORD))
        again = self.corrected(words={"type": "quote", "text": "In the end, we lost a whole week!"})
        self.refused(self.add("evidence", again, COORD), "E-coord-1")

    def test_check_accepts_both_new_statuses_at_rest(self):
        self.put(status="not found", verifier="v1", tries=["v1"], reason="not on the page")
        self.put("E-a1-2", status="reworded", verifier="v1", tries=["v1"], reason="reworded", page_words="x y")
        done = self.run_("check", self.unit)
        self.assertNotIn("E-a1-1.json", done.stdout + done.stderr)
        self.assertNotIn("E-a1-2.json", done.stdout + done.stderr)


class Hooks(unittest.TestCase):
    def test_normalise(self):
        n = rules_evidence.normalise
        self.assertEqual(n("  We   LOST, a week -- to this!"), "we lost a week to this")
        self.assertEqual(n("don’t"), n("don't"))
        self.assertEqual(n("..."), "")


if __name__ == "__main__":
    unittest.main()
