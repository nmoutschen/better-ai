"""research-better: a claim is set `verified` only with `--raw`, the text of the page the verifier read (issue #138).

The check itself is the shared one in src/better_ai/quotes.py, which discover-better's evidence uses too.
"""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from better import call  # noqa: E402
from research_records import SKILL, example, made_board  # noqa: E402

from better_ai import quotes  # noqa: E402

QUOTE = "we've added an address confirmation step before payment"
PAGE = "Release notes\n\nIn October we've added an address\nconfirmation step before payment. Conversion moved.\n"
SPAN = "In October we've added an address confirmation step before payment."


class ResearchRaw(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.board = made_board(self.root)
        self.page = self.root / "page.txt"
        self.page.write_text(PAGE)
        for kind, label in (("sources", "source, a page with no identifier"), ("questions", "in progress")):
            record = example(f"{kind}/<id>.json", label)
            fields = {k: v for k, v in record.items() if k not in ("type", "at", "by", "id", "raised_in", "lens")}
            if kind == "questions":
                fields["kind"] = "seed"
            done = call(SKILL, "add", self.board, kind[:-1], "--by", "w1", stdin=json.dumps(fields))
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        claim = {"claim": "A step was added.", "question": "Q-w1-1", "source": "S-w1-1", "quote": QUOTE}
        done = call(SKILL, "add", self.board, "claim", "--by", "w1", stdin=json.dumps({**claim, "status": "unchecked"}))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.set({"status": "checking", "checker": "v1"})

    def tearDown(self):
        self.tmp.cleanup()

    def set(self, fields, raw=None):
        args = ["set", self.board, "C-w1-1", "--by", "v1"] + (["--raw", str(raw)] if raw else [])
        return call(SKILL, *args, stdin=json.dumps(fields))

    def claim(self):
        return json.loads((self.board / "claims" / "C-w1-1.json").read_text())

    def verify(self, span=SPAN, raw=None, **more):
        return self.set({"status": "verified", "span": span, "hard": False, **more}, raw or self.page)

    def refused(self, done, *words):
        self.assertEqual(done.returncode, 1, done.stdout)
        for word in words:
            self.assertIn(word, done.stderr)
        self.assertEqual(self.claim()["status"], "checking")

    def test_verified_with_the_page_keeps_its_sha256(self):
        done = self.verify()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        claim = self.claim()
        self.assertEqual(claim["status"], "verified")
        self.assertEqual(claim["sha256"], hashlib.sha256(PAGE.encode()).hexdigest())
        self.assertEqual(call(SKILL, "check", self.board).returncode, 0)

    def test_verified_needs_raw(self):
        done = self.set({"status": "verified", "span": SPAN, "hard": False})
        self.refused(done, "--raw")

    def test_the_span_must_occur_in_the_page(self):
        self.refused(self.verify(span="We added a step before payment."), "does not occur in")

    def test_a_rephrased_quote_is_refused(self):
        page = self.root / "other.txt"
        page.write_text("We put an address check ahead of payment.")
        self.refused(self.verify(span="We put an address check ahead of payment.", raw=page), "quote does not occur")

    def test_passages_joined_by_dots_are_each_checked(self):
        span = "Release notes ... we've added an address confirmation step before payment."
        self.assertEqual(self.verify(span=span).returncode, 0)

    def test_the_quote_must_fall_within_one_passage(self):
        span = "we've added an address ... confirmation step before payment."
        self.refused(self.verify(span=span), "quote does not occur")

    def test_a_verified_claim_that_changes_source_needs_raw_again(self):
        self.assertEqual(self.verify().returncode, 0)
        done = call(SKILL, "set", self.board, "C-w1-1", "--by", "w1", stdin=json.dumps({"source": "S-w1-1"}))
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("--raw", done.stdout + done.stderr)

    def test_raw_on_a_verified_claim_is_checked_again(self):
        self.assertEqual(self.verify().returncode, 0)
        done = self.set({"differs": "date: the page says 2026-10-03"}, self.page)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        other = self.root / "other.txt"
        other.write_text("nothing here")
        self.assertEqual(self.set({"differs": "x"}, other).returncode, 1)

    def test_a_reworded_claim_goes_back_to_unchecked_with_unsets(self):
        self.set({"status": "unverified", "hard": False, "reason": "reworded: x", "span": SPAN})
        unset = [a for f in ("checker", "span", "hard", "reason") for a in ("--unset", f)]
        done = call(SKILL, "set", self.board, "C-w1-1", "--by", "coordinator", *unset, stdin='{"status": "unchecked"}')
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_raw_file_inside_the_board_is_refused(self):
        inside = self.board / "page.txt"
        inside.write_text(PAGE)
        self.refused(self.verify(raw=inside), "inside")

    def test_sha256_is_not_given_by_the_agent(self):
        self.refused(self.verify(sha256="a" * 64), "sha256")

    def test_unverified_needs_no_raw_and_withdrawing_drops_the_sha256(self):
        done = self.set({"status": "unverified", "hard": False, "reason": "not on the page"})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("sha256", self.claim())
        call(
            SKILL,
            "set",
            self.board,
            "C-w1-1",
            "--by",
            "v1",
            "--unset",
            "hard",
            "--unset",
            "reason",
            stdin='{"status": "checking"}',
        )
        self.assertEqual(self.verify().returncode, 0)
        unset = ["--unset", "checker", "--unset", "span", "--unset", "hard"]
        withdraw = json.dumps({"status": "withdrawn", "replaced_by": None})
        done = call(SKILL, "set", self.board, "C-w1-1", "--by", "coordinator", *unset, stdin=withdraw)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("sha256", self.claim())

    def test_a_claim_is_added_unchecked(self):
        claim = {"claim": "x", "question": "Q-w1-1", "source": "S-w1-1", "quote": QUOTE, "status": "verified"}
        claim.update(checker="v1", span=QUOTE, hard=False)
        done = call(SKILL, "add", self.board, "claim", "--by", "w1", stdin=json.dumps(claim))
        self.assertEqual(done.returncode, 1)
        self.assertIn("unchecked", done.stderr)


class Words(unittest.TestCase):
    def test_quote_in_span_ignores_case_punctuation_and_whitespace(self):
        self.assertTrue(quotes.quote_in_span("We've added", "Today, we’ve\n added it".replace("’", "'")))
        self.assertFalse(quotes.quote_in_span("we added", "we have added"))
        self.assertFalse(quotes.quote_in_span("", "anything"))


if __name__ == "__main__":
    unittest.main()
