"""tools/smoke.py: runs each committed better.pyz against a fixture unit, with python -I.

The test builds a fixture source tree whose entry file is a tiny command line (`--help`, `create`, `add`, `serve`),
so it checks the runner itself, not any skill.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pyz  # noqa: E402
import test_build  # noqa: E402

SMOKE = test_build.ROOT / "tools" / "smoke.py"

ENTRY = """import http.server
import json
import sys
import zipfile
from pathlib import Path

info = json.loads(zipfile.ZipFile(sys.argv[0]).read("better_ai/_build.json"))
args = sys.argv[1:]
if args == ["--help"]:
    print("better.pyz", info["skill"], info["hash"])
elif args[0] == "create":
    Path(args[1]).mkdir(parents=True)
    Path(args[1], "head.json").write_text(sys.stdin.read())
elif args[0] == "add":
    Path(args[1], "added.jsonl").open("a").write(sys.stdin.read() + "\\n")
elif args[0] == "serve":
    server = http.server.HTTPServer(("127.0.0.1", 0), http.server.SimpleHTTPRequestHandler)
    print("http://127.0.0.1:%d/" % server.server_port, flush=True)
    server.handle_request()
elif args[0] in ("set", "check", "render"):
    pass
else:
    sys.exit(2)
"""

SPEC = {
    "steps": [
        {"args": ["create", "unit", "--by", "x"], "stdin": "{}"},
        {"args": ["add", "unit", "t"], "stdin": "{}"},
        {"args": ["set", "unit", "T1"]},
        {"args": ["check", "unit"]},
        {"args": ["render", "unit"]},
        {"args": ["nope"], "exit": 2},
        {"args": ["serve", "unit", "--no-browser", "--once"], "serve": True},
    ],
    "worktree_steps": [{"args": ["add", "{repo}/unit", "t"], "stdin": "{}"}],
}


class TestSmoke(unittest.TestCase):
    def setUp(self):
        pyz.build_python()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.repo = test_build.Fixture(self.tmp)
        self.repo.write("src/better_ai/_entry.py", ENTRY)
        self.repo.build()
        self.fixtures = self.tmp / "units"
        for skill in ["alpha-better", "beta-better"]:
            (self.fixtures / skill).mkdir(parents=True)
            (self.fixtures / skill / "smoke.json").write_text(json.dumps(SPEC))

    def smoke(self, *extra):
        cmd = [
            sys.executable,
            "-I",
            str(SMOKE),
            "--src",
            str(self.repo.root / "src"),
            "--skills",
            str(self.repo.root / "skills"),
            "--fixtures",
            str(self.fixtures),
            *extra,
        ]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_every_step_passing_is_ok(self):
        result = self.smoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "alpha-better: ok\nbeta-better: ok\n")

    def test_a_wrong_exit_code_fails_and_names_the_step(self):
        spec = json.loads(json.dumps(SPEC))
        spec["steps"][5]["exit"] = 0
        (self.fixtures / "beta-better" / "smoke.json").write_text(json.dumps(spec))
        result = self.smoke()
        self.assertEqual(result.returncode, 1)
        self.assertIn("smoke: beta-better: nope: exit 2, expected 0", result.stderr)
        self.assertIn("alpha-better: ok", result.stdout)

    def test_a_missing_fixture_or_pyz_fails(self):
        (self.fixtures / "beta-better" / "smoke.json").unlink()
        self.repo.pyz("alpha-better").unlink()
        result = self.smoke()
        self.assertEqual(result.returncode, 1)
        self.assertIn("alpha-better", result.stderr)
        self.assertIn("beta-better: no fixture unit", result.stderr)

    def test_a_fixture_that_misses_a_verb_or_the_worktree_add_fails(self):
        spec = json.loads(json.dumps(SPEC))
        spec["steps"] = [st for st in spec["steps"] if st["args"][0] not in ("render", "set") and not st.get("serve")]
        spec["worktree_steps"] = [{"args": ["check", "unit"]}]
        (self.fixtures / "alpha-better" / "smoke.json").write_text(json.dumps(spec))
        result = self.smoke("alpha-better")
        self.assertEqual(result.returncode, 1)
        self.assertIn("fixture does not cover: set, render, serve", result.stderr)
        self.assertIn("an add in worktree_steps", result.stderr)

    def test_a_failing_step_in_the_second_worktree_fails(self):
        spec = json.loads(json.dumps(SPEC))
        spec["worktree_steps"] = [{"args": ["add", "{repo}/unit", "t"], "stdin": "{}"}, {"args": ["nope"]}]
        (self.fixtures / "alpha-better" / "smoke.json").write_text(json.dumps(spec))
        result = self.smoke("alpha-better")
        self.assertEqual(result.returncode, 1)
        self.assertIn("second worktree: nope", result.stderr)


if __name__ == "__main__":
    unittest.main()
