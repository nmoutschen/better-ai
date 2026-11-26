"""The fixture repository of the build tests: tools/build.py, a small `better_ai` source tree and a git history.

`Fixture(tmp)` is used by test_build.py and test_smoke.py.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pyz  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "tools" / "build.py"

ENTRY = """import json
import sys
import zipfile


def main():
    info = json.loads(zipfile.ZipFile(sys.argv[0]).read("better_ai/_build.json"))
    print("better.pyz", info["skill"], info["hash"])


main()
"""


SNAPSHOTS = ROOT / "tests" / "fixtures" / "build-schemas"


def snapshot(name):
    """A hand-made minimal schema (tests/fixtures/build-schemas), as a dict to change and write."""
    return json.loads((SNAPSHOTS / name).read_text())


def snapshot_text(name):
    return (SNAPSHOTS / name).read_text()


ALPHA_INIT = '''"""alpha, shaped like code-better: a change and an audit."""

from ..skill import Skill, UnitKind

SKILL = Skill(
    name="alpha-better",
    package="alpha",
    kinds=(
        UnitKind(kind="change", folder=".alpha", head="code.json", head_type="code", folders=("logs",)),
        UnitKind(kind="audit", folder=".alpha/audit", head="audit.json", head_type="audit"),
    ),
)
'''

BETA_INIT = '''"""beta, shaped like research-better: one kind of unit."""

from ..skill import Skill, UnitKind

SKILL = Skill(
    name="beta-better",
    package="beta",
    kinds=(UnitKind(kind="board", folder=".beta", head="brief.json", head_type="brief"),),
)
'''


def fixture_files():
    """The fixture source tree: {path under src/: text}. The schemas are hand-made minimal ones, shaped like the real
    decisions, code, tasks, progress, next-steps, audit and claims schemas but not kept equal to them, and the packages
    declare their unit kinds the way the real ones do."""
    files = {
        "skills.json": json.dumps(
            {
                "format_cutoff": "2026-11-22T00:00:00Z",
                "shared": [
                    "better_ai/__init__.py",
                    "better_ai/cli.py",
                    "better_ai/skill.py",
                    "better_ai/_entry.py",
                    "better_ai/schemas/",
                    "better_ai/page/",
                ],
                "skills": {"alpha-better": {"package": "alpha"}, "beta-better": {"package": "beta"}},
            }
        ),
        "__init__.py": "",
        "_entry.py": ENTRY,
        "cli.py": "import json\nimport os.path\nfrom better_ai import page\nfrom . import _entry\nfrom .skill import Skill\n",
        "skill.py": snapshot_text("skill.py.txt"),
        "page/__init__.py": "",
        "page/page.js": "export const a = 1;\n",
        "schemas/base.schema.json": snapshot_text("base.schema.json"),
        "schemas/decisions.schema.json": snapshot_text("decisions.schema.json"),
        "alpha/__init__.py": ALPHA_INIT,
        "beta/__init__.py": BETA_INIT,
    }
    for name in ["code", "tasks", "progress", "next-steps", "audit"]:
        files[f"alpha/schemas/{name}.schema.json"] = snapshot_text(f"{name}.schema.json")
    files["beta/schemas/claims.schema.json"] = snapshot_text("claims.schema.json")
    return {f"better_ai/{k}": v for k, v in files.items()}


def git(repo, *args):
    cmd = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com", *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()


class Fixture:
    """A fixture repository: tools/build.py, src/ and a git history; `tmp` is the folder it lives in."""

    def __init__(self, tmp: Path):
        self.root = tmp / "repo"
        self.root.mkdir()
        (self.root / "tools").mkdir()
        shutil.copy(BUILD, self.root / "tools" / "build.py")
        git(self.root, "init", "-q", "-b", "main")
        for name, text in fixture_files().items():
            self.write(f"src/{name}", text, tracked=False)
        git(self.root, "add", "-f", "src")

    def write(self, rel, text, tracked=True):
        """Write a file; one under src/ is staged, as a maintainer's would be (the build reads tracked files)."""
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        if tracked and rel.startswith("src/"):
            git(self.root, "add", "-f", rel)

    def run(self, *args, env=None, python=None):
        cmd = [python or pyz.build_python(), "-I", str(self.root / "tools" / "build.py"), *args]
        merged = {**os.environ, **(env or {})}
        return subprocess.run(cmd, capture_output=True, text=True, cwd=self.root, env=merged)

    def build(self):
        result = self.run()
        assert result.returncode == 0, result.stderr
        return result

    def commit(self, message="c"):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", message)
        return git(self.root, "rev-parse", "HEAD")

    def pyz(self, skill):
        return self.root / "skills" / skill / "scripts" / "better.pyz"
