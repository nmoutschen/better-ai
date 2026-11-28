"""The contract every skill's live page shares, tested once over every page in `page.PAGES`.

For each skill one `serve` process runs on a real unit. Every method the page may send (`spec.sendable()`) is saved as
the user's event, a `by` the page supplies is refused, the agent's wait, reply, status and pending work with the skill's
events schema, the conversation is still a valid log, and SIGTERM takes the server's address away. A skill's own event
semantics stay in its own test file; the shell's details are tested in test_page_shell.py.
"""

import json
import os
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
import architect_records  # noqa: E402
import better  # noqa: E402
import code_records  # noqa: E402
import discover_populated  # noqa: E402
import discover_records  # noqa: E402
import pyz  # noqa: E402
import research_records  # noqa: E402

from better_ai import page, resources  # noqa: E402

SHOW = {
    "type": "slides",
    "title": "The answer is yes.",
    "question": "Why?",
    "panels": [{"headline": "The slide states one clear point.", "source": "test", "kind": "text", "body": ["One."]}],
}
DESIGN = {"title": "Pay", "question": "Which?", "widths": ["1280x800"], "versions": [{"label": "A", "file": "a.html"}]}
NOTE = {"id": "m-x", "text": "hi", "to": None}


def repository(root: Path) -> Path:
    (root / ".git").mkdir()
    return root


def made(root: Path, skill: str, unit: str, fields: dict) -> Path:
    done = better.call(skill, "create", unit, "--by", "tester", stdin=json.dumps(fields), cwd=root)
    assert done.returncode == 0, done.stdout + done.stderr
    return root / unit


def show_unit(root: Path) -> Path:
    return made(repository(root), "show-better", ".show/deck", SHOW)


def design_unit(root: Path) -> Path:
    folder = repository(root) / ".design" / "pay"
    folder.mkdir(parents=True)
    (folder / "a.html").write_text("<h1>A</h1>")
    return made(root, "design-better", ".design/pay", DESIGN)


def architect_unit(root: Path) -> Path:
    return architect_records.example_folder(root)


def code_unit(root: Path) -> Path:
    return code_records.change(root)


def research_unit(root: Path) -> Path:
    return research_records.made_board(root)


PINS = {"id": "c1-x", "n": 1, "text": "unclear"}
# The unit of each skill, and a sample of each method its page sends, as page.js sends it (the server adds type, by, at).
PAGES = {
    "show-better": (
        show_unit,
        {
            "note": {**NOTE, "on": {"slide": 1, "part": None}},
            "comment": {**PINS, "on": {"slide": 1, "part": "headline", "headline": "H", "target": {}, "spot": {}}},
            "delete": {"to": "c1-x"},
            "accept": {"to": "c1-x"},
            "reopen": {"to": "c1-x", "text": "still wrong"},
        },
    ),
    "design-better": (
        design_unit,
        {
            "note": NOTE,
            "comment": {
                **PINS,
                "on": {
                    "version": "A",
                    "screen": "1280x800",
                    "target": {"selector": "#a"},
                    "spot": {"fx": 0.5, "fy": 0.5},
                },
            },
            "delete": {"to": "c1-x"},
            "accept": {"to": "c1-x"},
            "reopen": {"to": "c1-x", "text": "still wrong"},
            "approve": {"id": "ap-x", "option": "A", "label": "Build A", "carries": ["c1-x"], "text": None},
            "verdict": {"version": "A", "verdict": "up"},
        },
    ),
    "architect-better": (
        architect_unit,
        {
            "note": NOTE,
            "comment": {**PINS, "on": {"id": "req-F1", "title": "F1", "key": "k"}},
            "delete": {"to": "c1-x"},
            "accept": {"to": "c1-x"},
            "reopen": {"to": "c1-x", "text": "still wrong"},
            "confirm": {"id": "confirm-x", "requirement": "F1", "wording": "abc", "text": "Confirmed requirement F1."},
            "approve": {"id": "approval-x", "again": False, "perspectives": ["security"], "changes": [], "text": "ok"},
        },
    ),
    "code-better": (
        code_unit,
        {
            "note": NOTE,
            "answer": {"id": "a-x", "decision": "D1", "text": "Business days only.", "default": False},
            "comment": {"id": "c-x", "text": "why?", "on": {"kind": "agent", "id": "b1", "title": "b1"}},
            "accept": {"to": "a-x"},
            "reopen": {"to": "a-x", "text": "still wrong"},
        },
    ),
    "research-better": (
        research_unit,
        {
            "note": NOTE,
            "answer": {"id": "a-x", "decision": "D1", "text": "go on", "default": False},
            "comment": {"id": "c-x", "text": "why?", "on": {"kind": "question", "id": "Q-w2-4", "title": "t"}},
            "accept": {"to": "a-x"},
            "reopen": {"to": "a-x", "text": "still wrong"},
        },
    ),
    "discover-better": (
        discover_populated.populated,
        {
            "note": NOTE,
            "answer": {"id": "a-x", "decision": "D1", "text": "Run the probe", "default": False},
            **discover_records.EVENTS,
            "accept": {"to": "a-x"},
            "reopen": {"to": "a-x", "text": "still wrong"},
        },
    ),
}


# A method the page declares but its events schema does not list yet: the test expects the refusal until it is fixed.
# None now: the architect's schema lists `reopen` (T4).
UNSAVED: dict[str, set[str]] = {}


def rpc(url: str, method: str, params: dict, token: str) -> dict:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    headers = {"Content-Type": "application/json", **better.page_headers(token, url.rstrip("/"))}
    with urllib.request.urlopen(urllib.request.Request(url + "rpc", body, headers), timeout=10) as response:
        return json.loads(response.read())


class PageContract(unittest.TestCase):
    def test_every_shipped_skill_has_live_page_contract_samples(self):
        self.assertEqual(set(PAGES), set(pyz.skill_names()))

    def test_every_page_saves_what_it_sends_as_the_users_and_refuses_a_by(self):
        for skill in pyz.skill_names():
            resources.skill_package(skill.removesuffix("-better"))
        self.assertEqual(set(page.PAGES), set(PAGES), "a page without a unit and samples, or samples without a page")
        for skill, spec in page.PAGES.items():
            make_unit, samples = PAGES[skill]
            with self.subTest(skill), tempfile.TemporaryDirectory() as tmp:
                root = Path(os.path.realpath(tmp))
                folder = make_unit(root)
                self.assertEqual(set(spec.sendable()) - set(samples), set(), "a method without a sample")
                self.assertEqual(set(samples) - set(spec.sendable()), set(), "a sample the page cannot send")
                url, token = better.serve_page(skill, folder, "--linger", "0.2", cwd=root)
                self.addCleanup(better.stop_page, folder)
                kept = [m for m in samples if m not in UNSAVED.get(skill, ())]
                for method, params in samples.items():
                    answer = rpc(url, method, params, token)
                    if method in kept:
                        self.assertEqual(answer.get("result"), "saved", f"{method}: {answer}")
                    else:
                        self.assertEqual(answer["error"]["code"], -32602, method)
                log = folder / "conversation.jsonl"
                events = [json.loads(line) for line in log.read_text().splitlines()][
                    -len(kept) :
                ]  # after the unit's own
                self.assertEqual([e["type"] for e in events], kept)
                self.assertEqual({e["by"] for e in events}, {"user"})
                saved = log.read_text()
                refused = rpc(url, "note", {**NOTE, "by": "agent"}, token)
                self.assertEqual(refused["error"]["code"], -32602)
                self.assertIn("by", refused["error"]["message"])
                self.assertEqual(log.read_text(), saved)
                better.stop_page(folder)  # the unit has its own agent while it is served: it is the agent's now
                self.assertFalse((folder / ".server").exists())
                last = str(len(log.read_text().splitlines()) - 1)  # the agent read the whole log (D12)
                for verb, extra, text in (
                    ("reply", ["--to", "m-x", "--read", last], "seen it"),
                    ("status", ["accepted", "m-x", "--text"], "fine"),
                    ("pending", [], None),
                ):  # the agent's side, with this skill's events schema
                    done = better.call(skill, verb, str(folder), *extra, stdin=text, cwd=root)
                    self.assertEqual(done.returncode, 0, f"{verb}: {done.stdout}{done.stderr}")
                self.assertEqual(better.call(skill, "check", str(folder), cwd=root).returncode, 0)


if __name__ == "__main__":
    unittest.main()
