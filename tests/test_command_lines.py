"""Every `better.pyz <verb> ...` line in the text of every skill matches the command contract.

The contract is design.md's command contract, D4 and D5: the verbs each skill offers, each verb's positional
arguments and flags, and that the words of `reply` and `status --text` come on stdin, as `add`'s JSON does, never as
a quoted argument.
"""

import re
import shlex
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"

COMMON = {"create", "add", "set", "check", "serve", "wait", "reply", "status", "pending", "render"}
VERBS = {
    "architect-better": COMMON | {"review", "specs", "register"},
    "code-better": COMMON,
    "design-better": COMMON,
    "research-better": COMMON,
    "show-better": COMMON,
}
STATES = {"seen", "asked", "working", "done", "accepted"}

# verb: (fewest and most positional arguments, flags and whether each takes a value, flags that are required)
GRAMMAR = {
    "create": (1, 1, {"--by": True}, {"--by"}),
    "add": (2, 2, {"--by": True, "--for": True, "--id": True}, set()),
    "set": (2, 2, {"--unset": True, "--by": True}, set()),
    "check": (1, 1, {}, set()),
    "serve": (1, 1, {"--open": False, "--no-browser": False, "--linger": False, "--once": False}, set()),
    "wait": (1, 1, {"--timeout": True}, set()),
    "reply": (1, 1, {"--to": True, "--state": True}, set()),
    "status": (3, 99, {"--text": False}, set()),
    "pending": (1, 1, {}, set()),
    "render": (
        1,
        1,
        {"--format": True, "--ascii": False, "--width": True, "--screen-reader": False},
        set(),
    ),
    "review": (1, 1, {"--perspectives": True}, {"--perspectives"}),
    "specs": (1, 1, {}, set()),
    "register": (1, 1, {}, set()),
}
FORMATS = {"text", "md", "html"}


def command_texts(path: Path):
    """Each (line number, text after `better.pyz `) in a file; inline code ends at its closing backtick."""
    for number, line in enumerate(path.read_text().splitlines(), 1):
        for match in re.finditer(r"better\.pyz(?= )", line):
            before = line[: match.start()]
            rest = line[match.end() + 1 :]
            if before.count("`") % 2:
                rest = rest.split("`", 1)[0]
            yield number, re.sub(r"\s#.*", "", rest).strip()


def problems(skill: str, text: str):
    """What is wrong with one command line, as a list of words; empty when it matches the contract."""
    if not text or text.startswith("<verb>"):
        return []
    verb = text.split()[0]
    if verb not in VERBS[skill]:
        return [f"verb {verb!r} is not one of {sorted(VERBS[skill])}"]
    text = re.sub(r"\s*<<-?\s*'?\w+'?\s*$", "", text)  # a heredoc's opener is stdin, not an argument
    if verb in ("reply", "status") and re.search(r"[\"']", text):
        return ["the words of reply and status come on stdin, not as a quoted argument"]
    cleaned = re.sub(r"<[^<>]*>", "<X>", text)
    cleaned = cleaned.replace("[", " ").replace("]", " ")
    try:
        tokens = shlex.split(cleaned)[1:]
    except ValueError as error:
        return [str(error)]
    low, high, flags, required = GRAMMAR[verb]
    positional, found, found_values, out = [], set(), {}, []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.startswith("--"):
            if token not in flags:
                out.append(f"flag {token} is not one of {sorted(flags)}")
            else:
                found.add(token)
                if flags[token]:
                    values = []
                    while i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                        values.append(tokens[i + 1])
                        i += 1
                        if token != "--perspectives":
                            break
                    if not values:
                        out.append(f"flag {token} needs a value")
                    found_values[token] = values
        else:
            positional.append(token)
        i += 1
    if not low <= len(positional) <= high:
        out.append(f"{len(positional)} positional arguments, the verb takes {low} to {high}")
    out += [f"flag {flag} is required" for flag in sorted(required - found)]
    if verb == "add" and not found & {"--by", "--for"}:
        out.append("flag --by is required, unless --for names the agent")
    if verb == "status" and "--text" in found and tokens[-1] != "--text":
        out.append("--text takes no value: the user's words come on stdin")
    if verb == "status" and positional[1:2] and not all(s in STATES or s == "<X>" for s in positional[1].split("|")):
        out.append(f"state {positional[1]!r} is not one of {sorted(STATES)}")
    if verb == "render" and "--format" in found_values:
        out += [f"format {v!r}" for v in found_values["--format"] if v != "<X>" and not all(p in FORMATS for p in v.split("|"))]
    if verb == "reply" and "--state" in found_values:
        out += [f"state {v!r}" for v in found_values["--state"] if v not in ("asked", "working", "<X>")]
    return out


class CommandLines(unittest.TestCase):
    def test_every_better_pyz_line_in_the_skills_matches_the_contract(self):
        seen = 0
        for path in sorted(SKILLS.rglob("*.md")):
            relative = path.relative_to(SKILLS)
            if "scripts" in relative.parts or relative.parts[0] not in VERBS:
                continue
            for number, text in command_texts(path):
                seen += bool(text)
                with self.subTest(file=str(relative), line=number, command=text):
                    self.assertEqual(problems(relative.parts[0], text), [])
        self.assertGreater(seen, 20)

    def test_no_line_passes_the_words_of_a_reply_or_a_status_as_a_quoted_argument(self):
        for path in sorted(SKILLS.rglob("*.md")):
            for number, line in enumerate(path.read_text().splitlines(), 1):
                with self.subTest(file=str(path.relative_to(SKILLS)), line=number):
                    self.assertIsNone(re.search(r"--text\s+[\"']", line))

    def test_the_command_table_of_show_better_names_commands_only(self):
        text = (SKILLS / "show-better" / "templates" / "spec.md").read_text()
        block = text.split("```")[1]
        self.assertIn("better.pyz create", block)
        self.assertNotIn("#", block)

    def test_the_checker_refuses_what_the_contract_does_not_allow(self):
        bad = {
            'reply <unit> "<text>" --to <id>': "stdin",
            'status <unit> accepted <id>... --text "the user\'s words"': "stdin",
            "status <unit> seen": "positional",
            "status <unit> nearly <id>": "state",
            "add <unit>": "positional",
            "add <unit> <type> --who x": "flag",
            "create <folder>": "required",
            "card <unit>": "verb",
            "render <unit> --format pdf": "format",
            "wait <unit> --timeout": "value",
            "status <unit> accepted <id>... --text <words>": "stdin",
            "add <unit> <type>": "--by",
            "render <unit> --format text|pdf": "format",
        }
        for text, word in bad.items():
            with self.subTest(text):
                found = problems("show-better", text)
                self.assertTrue(found and word in " ".join(found), found)
        self.assertTrue(problems("show-better", "review <unit> --perspectives a b"))
        good = [
            "add <unit> <type> --by <your name>",
            "reply <unit> --to <id>",
            "status <unit> seen|asked|working|done <id>...",
            "status <unit> accepted <id>... --text",
            "render <unit> --format text --screen-reader",
            "serve <unit> --open",
            "add <unit> log --for <agent>",
            "reply <unit> --to <id> <<'EOF'",
            "add <unit> spec --by me <<'EOF'",
            "render <unit> --format text|md",
        ]
        for text in good:
            with self.subTest(text):
                self.assertEqual(problems("show-better", text), [])
        self.assertEqual(problems("architect-better", "review <unit> --perspectives <id>..."), [])
        self.assertEqual(problems("architect-better", "review <unit> --perspectives a b"), [])


if __name__ == "__main__":
    unittest.main()
