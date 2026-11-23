"""Every `better.pyz <verb> ...` line in the text of every skill matches the command line the .pyz parses.

The verbs each skill offers, each verb's positional arguments, flags and the values a flag or argument may take come
from the argparse parser of the skill (cli._parser, through pyz.verbs_of). Only the stdin rules are kept here: the
words of `reply` and `status --text` come on stdin, as `add`'s JSON does, never as a quoted argument.
"""

import argparse
import re
import shlex
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pyz  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def grammar(skill: str) -> dict[str, dict]:
    """verb -> its positional actions, its flags (option string -> action) and its required flags, from the parser."""
    out = {}
    for verb, parser in pyz.verbs_of(skill).items():
        actions = [a for a in parser._actions if not isinstance(a, argparse._HelpAction)]
        out[verb] = {
            "positional": [a for a in actions if not a.option_strings],
            "flags": {flag: a for a in actions for flag in a.option_strings},
            "required": {a.option_strings[0] for a in actions if a.option_strings and a.required},
        }
    return out


GRAMMAR = {skill: grammar(skill) for skill in pyz.skill_names()}


def wrong_choice(action, value: str) -> bool:
    """Whether `value`, one word or alternatives as a|b, is outside the action's choices; a <placeholder> is not."""
    return bool(action.choices) and any(part != "<X>" and part not in action.choices for part in value.split("|"))


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
    """What is wrong with one command line, as a list of words; empty when the skill's parser accepts it."""
    if not text or text.startswith("<verb>"):
        return []
    verb = text.split()[0]
    if verb not in GRAMMAR[skill]:
        return [f"verb {verb!r} is not one of {sorted(GRAMMAR[skill])}"]
    text = re.sub(r"\s*<<-?\s*'?\w+'?\s*$", "", text)  # a heredoc's opener is stdin, not an argument
    if verb in ("reply", "status") and re.search(r"[\"']", text):
        return ["the words of reply and status come on stdin, not as a quoted argument"]
    cleaned = re.sub(r"<[^<>]*>", "<X>", text)
    cleaned = cleaned.replace("[", " ").replace("]", " ")
    try:
        tokens = shlex.split(cleaned)[1:]
    except ValueError as error:
        return [str(error)]
    shape = GRAMMAR[skill][verb]
    positional, found, out = [], set(), []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.startswith("--"):
            action = shape["flags"].get(token)
            if action is None:
                out.append(f"flag {token} is not one of {sorted(shape['flags'])}")
            else:
                found.add(token)
                if action.nargs != 0:
                    values = []
                    while i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                        values.append(tokens[i + 1])
                        i += 1
                        if action.nargs != "+":
                            break
                    if not values:
                        out.append(f"flag {token} needs a value")
                    out += [
                        f"{token} value {v!r} is not one of {list(action.choices)}"
                        for v in values
                        if wrong_choice(action, v)
                    ]
        else:
            positional.append(token)
        i += 1
    wanted = shape["positional"]
    low = len(wanted)
    high = 99 if any(a.nargs == "+" for a in wanted) else low
    if not low <= len(positional) <= high:
        out.append(f"{len(positional)} positional arguments, the verb takes {low} to {high}")
    for n, value in enumerate(positional):
        action = wanted[min(n, len(wanted) - 1)]
        if wrong_choice(action, value):
            out.append(f"{action.dest} {value!r} is not one of {list(action.choices)}")
    out += [f"flag {flag} is required" for flag in sorted(shape["required"] - found)]
    if verb == "add" and not found & {"--by", "--for"}:
        out.append("flag --by is required, unless --for names the agent")
    if verb == "status" and "--text" in found and tokens[-1] != "--text":
        out.append("--text takes no value: the user's words come on stdin")
    return out


class CommandLines(unittest.TestCase):
    def test_every_better_pyz_line_in_the_skills_matches_the_contract(self):
        seen = 0
        for path in sorted(SKILLS.rglob("*.md")):
            relative = path.relative_to(SKILLS)
            if "scripts" in relative.parts or relative.parts[0] not in GRAMMAR:
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
        text = (SKILLS / "show-better" / "formats" / "spec.md").read_text()
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
            "set <unit> <ref> --who me": "flag",
            "serve <unit> --port": "value",
        }
        for text, word in bad.items():
            with self.subTest(text):
                found = problems("show-better", text)
                self.assertTrue(found and word in " ".join(found), found)
        self.assertTrue(problems("show-better", "review <unit> --perspectives a b"))
        self.assertTrue(problems("code-better", "render <unit> --format text"))
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
            "set <unit> <ref> --for x",
            "set <unit> <ref> --by me",
            "serve <unit> --linger 5 --once",
        ]
        for text in good:
            with self.subTest(text):
                self.assertEqual(problems("show-better", text), [])
        self.assertEqual(problems("architect-better", "review <unit> --perspectives <id>..."), [])
        self.assertEqual(problems("architect-better", "review <unit> --perspectives a b"), [])


if __name__ == "__main__":
    unittest.main()
