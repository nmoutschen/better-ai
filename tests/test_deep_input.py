"""Input nested far deeper than Python's recursion limit, in each file a script reads, through each command of the scripts
that read them: none prints a traceback, whatever it answers. Nesting is 950 (just inside the limit, where code that
recurses twice per level fails) and 50,000 (far past it), as a list and as an object."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_board_formats as boards  # noqa: E402
import test_dashboard_formats as dashboards  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def nest(kind: str, depth: int) -> str:
    return ("[" * depth + "]" * depth) if kind == "list" else ('{"a":' * depth + "1" + "}" * depth)


def traceback_of(*args) -> str:
    """The command's last traceback line, or '' when it printed none."""
    done = subprocess.run([sys.executable, "-I", *map(str, args)], capture_output=True, text=True, timeout=120)
    return done.stderr.strip().splitlines()[-1] if "Traceback" in done.stderr else ""


def spec_with(field_in_panel: bool, nested: str) -> str:
    """A slides spec holding `nested` in the free `document` field, or as the body of a text panel."""
    panel = {"headline": "A clear point here.", "kind": "text", "body": ["x"]}
    text = json.dumps({"type": "slides", "title": "T", "document": "@@", "panels": [panel]})
    if field_in_panel:
        panel["body"] = "@@"
        text = json.dumps({"type": "slides", "title": "T", "panels": [panel]})
    return text.replace('"@@"', nested)


class DeepInput(unittest.TestCase):
    def commands(self, root: Path, nested: str) -> dict:
        """The commands to run, by label, each on a file or folder that holds `nested` in one place."""
        show = SKILLS / "show-better" / "scripts"
        code = SKILLS / "code-better" / "scripts"
        research = SKILLS / "research-better" / "scripts"
        commands = {}
        for where, in_panel in (("document", False), ("body", True)):
            path = root / f"{where}.json"
            path.write_text(spec_with(in_panel, nested))
            commands[f"show check {where}"] = [show / "show.py", "check", path]
            commands[f"show render {where}"] = [show / "show.py", "render", path, "--out", root / "o.html"]
            commands[f"schema check {where}"] = [show / "schema.py", "check", path]
        slides = root / "slides"
        slides.mkdir()
        (slides / "conversation.jsonl").write_text('{"type":"note","id":"m-1","text":' + nested + "}\n")
        commands["show pending"] = [show / "show.py", "pending", slides]

        folder = dashboards.change(root / "dash")
        with (folder / "tasks.jsonl").open("a") as f:
            f.write('{"type":"task","id":"T9","x":' + nested + "}\n")
        commands["dashboard check"] = [code / "dashboard.py", "check", folder]
        commands["dashboard pending"] = [code / "dashboard.py", "pending", folder]
        commands["schema check dashboard"] = [code / "schema.py", "check", folder]

        board = root / "board"
        board.mkdir()
        boards.support(board)
        (board / "questions" / "Q-deep.json").write_text('{"type":"question","id":"Q-deep","x":' + nested + "}")
        commands["board check"] = [research / "board.py", "check", board]
        commands["board snapshot"] = [research / "board.py", "snapshot", board, "--out", board / "o.html"]
        commands["schema check board"] = [research / "schema.py", "check", board]
        return commands

    def test_no_command_prints_a_traceback_for_a_deeply_nested_file(self):
        for depth in (950, 50000):
            for kind in ("list", "dict"):
                with self.subTest(depth=depth, kind=kind), tempfile.TemporaryDirectory() as d:
                    commands = self.commands(Path(d), nest(kind, depth))
                    problems = {label: traceback_of(*args) for label, args in commands.items()}
                    self.assertEqual({k: v for k, v in problems.items() if v}, {})


if __name__ == "__main__":
    unittest.main()
