"""tools/build.py: the deterministic build, every kind of failure `--check` reports, and `--which`.

Each test builds a small fixture repository in a temporary folder (a `better_ai` package with a skills.json, an
entry file, schemas and two fake skill packages) and runs tools/build.py on it. The real src/ is not needed.
"""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pyz  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "tools" / "build.py"
PY310 = os.environ.get(
    "BETTER_AI_PYTHON310", "/Users/ninou/.local/share/uv/python/cpython-3.10-macos-aarch64-none/bin/python3.10"
)

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
    """A schema copied from the real tree (tests/fixtures/build-schemas), as a dict to change and write."""
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
    exclude=".alpha/",
)
'''

BETA_INIT = '''"""beta, shaped like research-better: one kind of unit."""

from ..skill import Skill, UnitKind

SKILL = Skill(
    name="beta-better",
    package="beta",
    kinds=(UnitKind(kind="board", folder=".beta", head="brief.json", head_type="brief"),),
    exclude=".beta/",
)
'''


def fixture_files():
    """The fixture source tree: {path under src/: text}. The schemas are copies of real ones (decisions, code's
    code, tasks, progress, next-steps and audit, research's claims) and the packages declare their unit kinds the way
    the real ones do."""
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
            self.write(f"src/{name}", text)

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


class BuildTestCase(unittest.TestCase):
    def setUp(self):
        pyz.build_python()  # skips the test when no Python 3.12 is available
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.repo = Fixture(self.tmp)

    def built_repo(self):
        """The fixture built and committed: --check passes."""
        self.repo.build()
        self.repo.commit("build")
        return self.repo

    def check(self, *args):
        result = self.repo.run("--check", *args)
        return result.returncode, result.stderr

    def entries(self, skill):
        with zipfile.ZipFile(self.repo.pyz(skill)) as z:
            return sorted(n for n in z.namelist() if not n.endswith("/"))


class TestBuild(BuildTestCase):
    def test_each_pyz_holds_what_skills_json_lists_and_no_other_skill(self):
        # S57
        self.repo.build()
        source = [k for k in fixture_files() if k != "better_ai/skills.json"]
        base = [
            "__main__.py",
            "better_ai/_build.json",
            *[k for k in source if "/alpha/" not in k and "/beta/" not in k],
        ]
        alpha = [k for k in source if "/alpha/" in k]
        beta = [k for k in source if "/beta/" in k]
        self.assertEqual(self.entries("alpha-better"), sorted([*base, *alpha]))
        self.assertEqual(self.entries("beta-better"), sorted([*base, *beta]))
        self.assertFalse(any("beta" in n for n in self.entries("alpha-better") if n != "better_ai/_build.json"))
        self.assertFalse(any("alpha" in n for n in self.entries("beta-better")))

    def test_an_untracked_file_never_enters_a_pyz(self):
        self.repo.build()
        before = self.repo.pyz("alpha-better").read_bytes()
        self.repo.write("src/better_ai/page/.DS_Store", "junk", tracked=False)
        self.repo.write("src/better_ai/alpha/.__init__.py.swp", "junk", tracked=False)
        self.repo.write("src/better_ai/alpha/new_module.py", "x = 1\n", tracked=False)
        self.repo.build()
        self.assertEqual(before, self.repo.pyz("alpha-better").read_bytes())

    def test_main_is_a_copy_of_the_entry_and_build_info_names_the_skill(self):
        self.repo.build()
        with zipfile.ZipFile(self.repo.pyz("alpha-better")) as z:
            self.assertEqual(z.read("__main__.py"), z.read("better_ai/_entry.py"))
            info = json.loads(z.read("better_ai/_build.json"))
        self.assertEqual(sorted(info), ["cutoff", "hash", "package", "skill"])
        self.assertEqual(
            (info["skill"], info["package"], info["cutoff"]), ("alpha-better", "alpha", "2026-11-22T00:00:00Z")
        )
        self.assertRegex(info["hash"], "^[0-9a-f]{16}$")

    def test_pycache_is_left_out_and_the_hash_ignores_it(self):
        self.repo.build()
        before = self.repo.pyz("alpha-better").read_bytes()
        self.repo.write("src/better_ai/alpha/__pycache__/x.pyc", "junk")
        self.repo.build()
        self.assertEqual(before, self.repo.pyz("alpha-better").read_bytes())

    def test_same_bytes_in_two_folders_and_two_time_zones_and_other_mtimes(self):
        # S38
        outputs = []
        for i, zone in enumerate(["America/New_York", "Asia/Tokyo"]):
            out = self.tmp / f"out{i}"
            result = self.repo.run("--skills", str(out), env={"TZ": zone})
            self.assertEqual(result.returncode, 0, result.stderr)
            outputs.append(out)
            for path in (self.repo.root / "src").rglob("*"):
                os.utime(path, (1_000_000_000 + i * 99999, 1_000_000_000 + i * 99999))
        for skill in ["alpha-better", "beta-better"]:
            a = (outputs[0] / skill / "scripts" / "better.pyz").read_bytes()
            self.assertEqual(a, (outputs[1] / skill / "scripts" / "better.pyz").read_bytes())

    def test_entries_are_stored_with_fixed_time_and_permissions(self):
        self.repo.build()
        with zipfile.ZipFile(self.repo.pyz("alpha-better")) as z:
            for info in z.infolist():
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED, info.filename)
                self.assertEqual(info.date_time, (2000, 1, 1, 0, 0, 0), info.filename)
                mode = info.external_attr >> 16 & 0o777
                self.assertEqual(mode, 0o755 if info.is_dir() else 0o644, info.filename)

    def test_older_python_is_refused_with_exit_2_naming_the_minimum(self):
        if not Path(PY310).exists():
            self.skipTest("no Python 3.10 at BETTER_AI_PYTHON310")
        result = self.repo.run(python=PY310)
        self.assertEqual(result.returncode, 2)
        self.assertIn("3.12", result.stderr)
        self.assertFalse((self.repo.root / "skills").exists())

    def test_the_pyz_runs_with_python_dash_i_from_a_copy_of_its_skill_folder_alone(self):
        # S67: built on 3.12+, run on every Python we have
        self.repo.build()
        interpreters = list(dict.fromkeys([sys.executable, *([PY310] if Path(PY310).exists() else [])]))
        for python in interpreters:
            copy = self.tmp / "copy" / str(interpreters.index(python))
            shutil.copytree(self.repo.root / "skills" / "alpha-better", copy)
            result = subprocess.run(
                [python, "-I", str(copy / "scripts" / "better.pyz"), "--help"], capture_output=True, text=True, cwd=copy
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertRegex(result.stdout, r"^better\.pyz alpha-better [0-9a-f]{16}\n$")

    def test_a_bad_skills_json_path_stops_the_build_and_writes_nothing(self):
        self.repo.write(
            "src/better_ai/skills.json",
            json.dumps({**json.loads(fixture_files()["better_ai/skills.json"]), "shared": ["better_ai/nope.py"]}),
        )
        result = self.repo.run()
        self.assertEqual(result.returncode, 1)
        self.assertIn("better_ai/nope.py: no such file", result.stderr)
        self.assertFalse((self.repo.root / "skills").exists())

    def test_a_symlink_in_the_source_is_refused(self):
        os.symlink("/etc/hosts", self.repo.root / "src" / "better_ai" / "page" / "link.js")
        git(self.repo.root, "add", "-f", "src/better_ai/page/link.js")
        result = self.repo.run()
        self.assertEqual(result.returncode, 1)
        self.assertIn("symlink", result.stderr)


class TestCheck(BuildTestCase):
    def test_a_clean_built_repository_passes(self):
        self.built_repo()
        code, err = self.check()
        self.assertEqual((code, err), (0, ""))

    def test_stale_names_the_build_command(self):
        self.built_repo()
        self.repo.write("src/better_ai/page/page.js", "export const a = 2;\n")
        code, err = self.check()
        self.assertEqual(code, 1)
        self.assertIn(
            "stale: skills/alpha-better/scripts/better.pyz: the source changed since the committed build; run `python3 tools/build.py`",
            err,
        )
        self.assertIn("skills/beta-better/scripts/better.pyz", err)

    def test_same_hash_different_bytes_is_not_reproducible_across_environments(self):
        self.built_repo()
        path = self.repo.pyz("alpha-better")
        with zipfile.ZipFile(path) as z:
            items = [(i, z.read(i)) for i in z.infolist()]
        rebuilt = self.tmp / "tampered.pyz"
        with zipfile.ZipFile(rebuilt, "w") as z:
            for info, data in items:
                if info.filename == "better_ai/cli.py":
                    data += b"# changed\n"
                z.writestr(info, data)
        path.write_bytes(b"#!/usr/bin/env python3\n" + rebuilt.read_bytes())
        code, err = self.check()
        self.assertEqual(code, 1)
        self.assertIn("not reproducible across environments: skills/alpha-better/scripts/better.pyz", err)
        self.assertIn("better_ai/cli.py", err)
        self.assertIn("Python ", err)
        self.assertNotIn("stale", err)

    def test_two_builds_that_differ_are_not_reproducible(self):
        if sys.version_info < (3, 12):
            self.skipTest("imports tools/build.py, which needs Python 3.12 or later")
        self.built_repo()
        spec = importlib.util.spec_from_file_location("build_under_test", BUILD)
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        original, calls = build.write_archive, []

        def noisy(files, dest):
            original(files, dest)
            calls.append(dest)
            with open(dest, "ab") as handle:
                handle.write(bytes([len(calls)]))

        build.write_archive = noisy
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
            code = build.main(["--compare", "--root", str(self.repo.root)])
        self.assertEqual(code, 1)
        self.assertIn(
            "not reproducible: skills/alpha-better/scripts/better.pyz: two builds differ in:", stderr.getvalue()
        )

    def test_a_tracked_file_under_skills_scripts_is_stray(self):
        self.built_repo()
        self.repo.write("skills/alpha-better/scripts/old.py", "print(1)\n")
        self.repo.write("skills/alpha-better/schemas/x.schema.json", "{}\n")
        self.repo.write("skills/gamma-better/scripts/better.pyz", "not listed\n")
        self.repo.write("skills/alpha-better/SKILL.md", "kept\n")
        self.repo.commit("stray")
        self.repo.write("skills/alpha-better/scripts/__pycache__/x.pyc", "untracked, not counted")
        code, err = self.check()
        self.assertEqual(code, 1)
        for path in ["scripts/old.py", "schemas/x.schema.json"]:
            self.assertIn(
                f"stray: skills/alpha-better/{path}: not produced by the build: remove it, or list it in skills.json",
                err,
            )
        self.assertIn("stray: skills/gamma-better/scripts/better.pyz", err)
        self.assertNotIn("SKILL.md", err)
        self.assertNotIn("__pycache__", err)

    def test_a_record_type_that_does_not_require_type_at_by_fails(self):
        tasks = snapshot("tasks.schema.json")
        tasks["required"] = [f for f in tasks["required"] if f not in ("at", "by")]
        self.repo.write("src/better_ai/alpha/schemas/tasks.schema.json", json.dumps(tasks))
        self.built_repo()
        code, err = self.check()
        self.assertEqual(code, 1)
        self.assertIn("base fields: better_ai/alpha/schemas/tasks.schema.json: type task does not require at", err)
        self.assertIn("type task does not require by", err)
        self.assertNotIn("does not require type", err)

    def test_a_dispatching_root_is_judged_by_the_branches_that_select_each_type(self):
        # the shape of research's logs.schema.json: the root only dispatches, and each branch requires the fields
        progress = snapshot("progress.schema.json")
        progress["required"] = ["type"]
        for branch in progress["$defs"].values():
            branch["required"] = [f for f in branch["required"] if f != "by"]
        self.repo.write("src/better_ai/alpha/schemas/progress.schema.json", json.dumps(progress))
        self.built_repo()
        code, err = self.check()
        self.assertEqual(code, 1)
        for rtype in ["progress", "problem", "resolved"]:
            self.assertIn(f"type {rtype} does not require by", err)

    def test_a_dispatching_root_whose_branches_require_the_fields_passes(self):
        progress = snapshot("progress.schema.json")
        progress["required"] = ["type"]
        self.repo.write("src/better_ai/alpha/schemas/progress.schema.json", json.dumps(progress))
        self.built_repo()
        self.assertEqual(self.check(), (0, ""))

    def test_a_bundled_schema_missing_from_the_pyz_is_reported(self):
        shared = json.loads((self.repo.root / "src/better_ai/skills.json").read_text())
        shared["shared"].remove("better_ai/schemas/")
        shared["shared"].append("better_ai/schemas/base.schema.json")  # decisions.schema.json is left out
        self.repo.write("src/better_ai/skills.json", json.dumps(shared))
        self.built_repo()
        code, err = self.check()
        self.assertEqual(code, 1)
        self.assertIn("bundled file: alpha-better: better_ai/schemas/decisions.schema.json", err)
        self.assertIn("beta-better: better_ai/schemas/decisions.schema.json", err)
        self.assertNotIn("base.schema.json", err)

    def test_architects_kinds_and_icons_must_be_in_its_pyz(self):
        config = json.loads((self.repo.root / "src/better_ai/skills.json").read_text())
        config["skills"]["architect-better"] = {"package": "architect"}
        self.repo.write("src/better_ai/skills.json", json.dumps(config))
        self.repo.write("src/better_ai/architect/__init__.py", BETA_INIT.replace("beta", "architect"))
        self.repo.write("src/better_ai/architect/kinds.json", "{}")
        self.built_repo()
        code, err = self.check()
        self.assertEqual(code, 1)
        self.assertIn("bundled file: architect-better: better_ai/architect/icons.json", err)
        self.assertNotIn("kinds.json", err)

    def test_a_third_party_import_names_the_skill_and_the_module(self):
        self.repo.write("src/better_ai/alpha/__init__.py", "import requests\nfrom yaml import safe_load\n" + ALPHA_INIT)
        self.built_repo()
        code, err = self.check()
        self.assertEqual(code, 1)
        self.assertIn("import: alpha-better: requests: imported by better_ai/alpha/__init__.py", err)
        self.assertIn("import: alpha-better: yaml:", err)
        self.assertNotIn("beta-better", err)

    def test_an_import_of_a_module_another_skill_owns_is_missing_from_the_pyz(self):
        extra = "from better_ai.beta import thing\nfrom ..cli import x\n"
        self.repo.write("src/better_ai/alpha/__init__.py", extra + ALPHA_INIT)
        self.repo.write("src/better_ai/beta/thing.py", "thing = 1\n")
        self.built_repo()
        code, err = self.check()
        self.assertEqual(code, 1)
        self.assertIn(
            "import: alpha-better: better_ai.beta: imported by better_ai/alpha/__init__.py: is in src/ but not in this skill's .pyz",
            err,
        )
        self.assertNotIn("better_ai.cli", err)

    def test_an_imported_name_that_is_another_skills_module_is_missing_from_the_pyz(self):
        # `from better_ai import beta` and `from .. import beta` import a module through the names
        self.repo.write(
            "src/better_ai/alpha/__init__.py", "from better_ai import beta\nfrom .. import beta as b2\n" + ALPHA_INIT
        )
        self.repo.write("src/better_ai/alpha/helper.py", "from . import missing_attribute\nfrom . import helper2\n")
        self.repo.write("src/better_ai/beta/helper2.py", "x = 1\n")
        self.repo.write("src/better_ai/alpha/helper2.py", "x = 2\n")
        self.built_repo()
        code, err = self.check()
        self.assertEqual(code, 1)
        self.assertIn("import: alpha-better: better_ai.beta: imported by better_ai/alpha/__init__.py: is in src/", err)
        self.assertNotIn("missing_attribute", err)  # a name that is no module anywhere is an attribute
        self.assertNotIn("helper2", err)  # a sibling module that is in the .pyz

    def test_a_module_that_from_dot_import_names_but_skills_json_does_not_list_is_reported(self):
        self.repo.write("src/better_ai/cli.py", "from . import extra\nfrom . import page\n")
        self.repo.write("src/better_ai/extra.py", "x = 1\n")
        self.built_repo()
        code, err = self.check()
        self.assertEqual(code, 1)
        self.assertIn("import: alpha-better: better_ai.extra: imported by better_ai/cli.py: is in src/ but not in", err)
        self.assertNotIn("better_ai.page:", err)

    def test_a_standard_library_module_newer_than_python_3_10_is_refused(self):
        self.repo.write(
            "src/better_ai/alpha/__init__.py", "import tomllib\nfrom asyncio import taskgroups\n" + ALPHA_INIT
        )
        self.built_repo()
        code, err = self.check()
        self.assertEqual(code, 1)
        self.assertIn(
            "import: alpha-better: tomllib: imported by better_ai/alpha/__init__.py: not in the standard library of Python 3.10",
            err,
        )

    def test_build_and_src_changed_together_fails_when_a_base_is_given(self):
        self.built_repo()
        base = git(self.repo.root, "rev-parse", "HEAD")
        self.repo.write("tools/build.py", (self.repo.root / "tools" / "build.py").read_text() + "\n# change\n")
        self.repo.write("src/better_ai/page/page.js", "export const a = 3;\n")
        self.repo.build()
        self.repo.commit("both")
        code, err = self.check("--base", base)
        self.assertEqual(code, 1)
        self.assertIn("build changed with src: tools/build.py: land the build change in its own PR", err)

    def test_build_only_or_src_only_changes_pass_with_a_base(self):
        self.built_repo()
        base = git(self.repo.root, "rev-parse", "HEAD")
        self.repo.write("tools/build.py", (self.repo.root / "tools" / "build.py").read_text() + "\n# change\n")
        self.repo.commit("build only")
        self.assertEqual(self.check("--base", base), (0, ""))
        base = git(self.repo.root, "rev-parse", "HEAD")
        self.repo.write("src/better_ai/page/page.js", "export const a = 3;\n")
        self.repo.build()
        self.repo.commit("src only")
        self.assertEqual(self.check("--base", base), (0, ""))

    def test_the_change_that_adds_the_build_is_not_held_to_the_rule(self):
        base = self.repo.commit("no build yet")
        git(self.repo.root, "rm", "-q", "-r", "--cached", "tools")
        git(self.repo.root, "commit", "-q", "-m", "drop tools")
        base = git(self.repo.root, "rev-parse", "HEAD")
        self.repo.build()
        self.repo.commit("adds build and src")
        self.assertEqual(self.check("--base", base), (0, ""))

    def test_without_a_base_the_step_is_skipped_with_a_note(self):
        self.built_repo()
        result = self.repo.run("--check")
        self.assertEqual(result.returncode, 0)
        self.assertIn("no --base given", result.stdout)

    def test_every_failure_is_reported_not_just_the_first(self):
        self.repo.write("src/better_ai/alpha/__init__.py", "import requests\n" + ALPHA_INIT)
        self.built_repo()
        self.repo.write("skills/alpha-better/scripts/old.py", "x\n")
        self.repo.commit("stray")
        self.repo.write("src/better_ai/page/page.js", "export const a = 9;\n")
        code, err = self.check()
        self.assertEqual(code, 1)
        for kind in ["stale:", "stray:", "import:"]:
            self.assertIn(kind, err)

    def test_the_hash_summary_lists_each_skill_and_entry_with_sha256(self):
        self.built_repo()
        summary = self.tmp / "summary.md"
        result = self.repo.run("--check", env={"GITHUB_STEP_SUMMARY": str(summary)})
        self.assertEqual(result.returncode, 0, result.stderr)
        text = summary.read_text()
        self.assertIn("tools/build.py sha256:", text)
        with zipfile.ZipFile(self.repo.pyz("alpha-better")) as z:
            info = json.loads(z.read("better_ai/_build.json"))
        self.assertIn(f"source hash: `{info['hash']}`", text)
        self.assertRegex(text, r"\| better_ai/cli\.py \| `[0-9a-f]{64}` \|")


class TestUnitKindInvariants(BuildTestCase):
    def expect(self, kind, subject_part):
        for args in [(), ("--check",)]:
            result = self.repo.run(*args)
            self.assertEqual(result.returncode, 1, args)
            line = next((ln for ln in result.stderr.splitlines() if ln.startswith(f"{kind}: ")), None)
            self.assertIsNotNone(line, result.stderr)
            self.assertIn(subject_part, line)

    def test_a_type_in_two_files_of_one_unit_kind_is_refused(self):
        # today's code-better `step`: in a log and in next-steps
        self.repo.write("src/better_ai/alpha/schemas/log.schema.json", snapshot_text("log.schema.json"))
        self.expect("duplicate type", "alpha-better/change: step")
        self.assertFalse((self.repo.root / "skills").exists())

    def test_one_schema_listing_two_files_for_a_type_is_refused(self):
        tasks = snapshot("tasks.schema.json")
        tasks["x-files"] = ["tasks.jsonl", "logs/*.jsonl"]
        self.repo.write("src/better_ai/alpha/schemas/tasks.schema.json", json.dumps(tasks))
        self.expect("duplicate type", "alpha-better/change: task")

    def test_two_types_sharing_an_id_prefix_in_different_files_are_refused(self):
        # x-id sits on the `id` property, as in the real schemas; next-steps takes tasks' prefix
        steps = snapshot("next-steps.schema.json")
        steps["properties"]["id"]["x-id"] = {"prefix": "T"}
        self.repo.write("src/better_ai/alpha/schemas/next-steps.schema.json", json.dumps(steps))
        self.expect("overlapping prefix", "alpha-better/change: T")

    def test_an_x_id_on_the_record_node_counts_too(self):
        steps = snapshot("next-steps.schema.json")
        del steps["properties"]["id"]["x-id"]
        steps["x-id"] = {"prefix": "T"}
        self.repo.write("src/better_ai/alpha/schemas/next-steps.schema.json", json.dumps(steps))
        self.expect("overlapping prefix", "alpha-better/change: T")

    def test_an_agent_prefix_counts_with_a_plain_one(self):
        # research's claims use C with an agent; a second type in another file taking C overlaps
        other = snapshot("claims.schema.json")
        other["properties"]["type"] = {"const": "claim2"}
        other["x-files"] = ["claims2/*.json"]
        self.repo.write("src/better_ai/beta/schemas/claims2.schema.json", json.dumps(other))
        self.expect("overlapping prefix", "beta-better/board: C")

    def test_a_prefix_by_map_counts_each_mapped_prefix(self):
        # architect's requirements map kind to F, Q or C; a mapped prefix another type's file uses overlaps
        req = snapshot("requirements.schema.json")
        req["properties"]["id"]["x-id"]["map"]["quality"] = "T"  # tasks' prefix
        self.repo.write("src/better_ai/alpha/schemas/requirements.schema.json", json.dumps(req))
        self.expect("overlapping prefix", "alpha-better/change: T")

    def test_a_shared_path_inside_a_skill_package_is_refused(self):
        for bad in ("better_ai/", "better_ai/beta/", "better_ai/beta/x.py"):
            with self.subTest(bad):
                cfg = json.loads((self.repo.root / "src/better_ai/skills.json").read_text())
                cfg["shared"].append(bad)
                self.repo.write("src/better_ai/skills.json", json.dumps(cfg))
                result = self.repo.run()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("skills.json", result.stderr)
                cfg["shared"].remove(bad)
                self.repo.write("src/better_ai/skills.json", json.dumps(cfg))

    def test_the_same_type_in_the_same_file_by_two_schemas_is_fine(self):
        self.repo.write("src/better_ai/alpha/schemas/tasks2.schema.json", snapshot_text("tasks.schema.json"))
        self.assertEqual(self.repo.run().returncode, 0)

    def test_one_prefix_shared_by_types_of_one_file_is_fine(self):
        # evidence's history, check and rule share E in one file
        evidence = snapshot("tasks.schema.json")
        second = json.loads(json.dumps(evidence))
        second["properties"]["type"] = {"const": "task2"}
        evidence["$defs"] = {"task2": second}
        evidence["allOf"] = [{"if": {"properties": {"type": {"const": "task2"}}}, "then": {"$ref": "#/$defs/task2"}}]
        self.repo.write("src/better_ai/alpha/schemas/tasks.schema.json", json.dumps(evidence))
        self.assertEqual(self.repo.run().returncode, 0)

    def test_the_same_type_in_the_audit_and_the_change_kinds_is_fine(self):
        # code-better's units are changes and audits: a type may repeat across the two kinds
        audit_tasks = snapshot("tasks.schema.json")
        audit_tasks["x-files"] = ["audit/*/tasks.jsonl"]
        self.repo.write("src/better_ai/alpha/schemas/audit-tasks.schema.json", json.dumps(audit_tasks))
        self.assertEqual(self.repo.run().returncode, 0)
        # and the same clash inside the audit kind is still refused
        audit_tasks2 = json.loads(json.dumps(audit_tasks))
        audit_tasks2["x-files"] = ["audit/*/other.jsonl"]
        self.repo.write("src/better_ai/alpha/schemas/audit-tasks2.schema.json", json.dumps(audit_tasks2))
        self.expect("duplicate type", "alpha-better/audit: task")

    def test_pointer_definitions_and_dispatching_defs_are_not_record_types(self):
        # decisions' $defs (about, answer) and progress' $defs branches are shared by two skills and pass as they are
        self.assertEqual(self.repo.run().returncode, 0)

    def test_the_other_skill_is_not_affected(self):
        other = snapshot("tasks.schema.json")
        other["x-files"] = ["other.jsonl"]
        self.repo.write("src/better_ai/beta/schemas/tasks.schema.json", json.dumps(other))
        # beta has no task elsewhere, and alpha's tasks are its own: no failure
        self.assertEqual(self.repo.run().returncode, 0)


class TestRealTree(BuildTestCase):
    """L3: every static step runs on the real src/better_ai, not only on fixtures shaped by hand."""

    KNOWN = (
        # code-better's `step` is in both log.schema.json and next-steps.schema.json until it is renamed next_step
        "duplicate type: code-better/change: step: ",
        # show-better's spec.json (`slides`) has no at and by until it gets them
        "base fields: better_ai/show/schemas/spec.schema.json: type slides does not require ",
        # nothing is built and committed in this copy
        "stale: ",
    )

    def real_copy(self):
        repo = self.tmp / "real"
        shutil.copytree(ROOT / "src", repo / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (repo / "tools").mkdir()
        shutil.copy(BUILD, repo / "tools" / "build.py")
        # files other tasks add (records.py, page/) may be missing: placeholders so skills.json resolves
        package = repo / "src" / "better_ai"
        for rel in json.loads((package / "skills.json").read_text())["shared"]:
            target = repo / "src" / rel
            if rel.endswith("/") and not target.exists():
                target.mkdir(parents=True)
                (target / "__init__.py").write_text("")
            elif not rel.endswith("/") and not target.exists():
                target.write_text("")
        git(repo, "init", "-q", "-b", "main")
        git(repo, "add", "-A")
        return repo

    def assert_only_known(self, result):
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("build.py:", result.stderr, result.stderr)  # a refused source, not a check result
        for line in result.stderr.splitlines():
            self.assertTrue(line.startswith(self.KNOWN), f"unexpected failure on the real tree: {line}")

    def test_check_and_compare_on_the_real_tree_report_only_the_known_failures(self):
        repo = self.real_copy()
        python = pyz.build_python()
        for mode in ["--check", "--compare"]:
            result = subprocess.run(
                [python, "-I", str(repo / "tools" / "build.py"), mode, "--root", str(repo)],
                capture_output=True,
                text=True,
                cwd=repo,
            )
            self.assert_only_known(result)

    def test_the_real_tree_builds_every_skill_when_the_known_failures_are_fixed_in_a_copy(self):
        # nothing but the skills' own fixes stands between the real tree and a build
        repo = self.real_copy()
        python = pyz.build_python()
        result = subprocess.run(
            [python, "-I", str(repo / "tools" / "build.py"), "--root", str(repo)],
            capture_output=True,
            text=True,
            cwd=repo,
        )
        self.assert_only_known(result)


class TestWorkflow(unittest.TestCase):
    """The shell line CI runs for the JavaScript syntax step must fail on a bad file."""

    def step_line(self):
        for line in (ROOT / ".github" / "workflows" / "scripts.yml").read_text().splitlines():
            if "node --check" in line:
                return line.split("run:", 1)[1].strip()
        self.fail("no node --check step in scripts.yml")

    def run_step(self, files):
        if not shutil.which("node"):
            self.skipTest("node is not installed")
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in files.items():
                path = Path(tmp) / "src" / "better_ai" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            return subprocess.run(["sh", "-c", self.step_line()], cwd=tmp, capture_output=True, text=True)

    def test_a_good_file_passes(self):
        self.assertEqual(self.run_step({"a.js": "const a = 1;\n", "page/b.js": "let b;\n"}).returncode, 0)

    def test_a_bad_file_fails_the_step_even_when_another_is_good(self):
        result = self.run_step({"a.js": "const a = 1;\n", "page/b.js": "function (\n", "page/c.js": "let c;\n"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SyntaxError", result.stderr)

    def test_the_workflows_pin_actions_by_sha_and_have_read_only_permissions(self):
        for name in ["scripts.yml", "base-build.yml"]:
            text = (ROOT / ".github" / "workflows" / name).read_text()
            self.assertIn("permissions:\n  contents: read", text)
            for line in text.splitlines():
                if "uses: actions/checkout" in line or "uses: actions/setup-python" in line:
                    self.assertRegex(line, r"@[0-9a-f]{40}\b")


class TestCompareAndPullRequestData(BuildTestCase):
    def test_compare_reads_a_checkout_as_data_and_never_runs_its_code(self):
        self.built_repo()
        marker = self.tmp / "ran"
        for module in ["alpha/__init__.py", "cli.py", "_entry.py"]:
            old = (self.repo.root / "src" / "better_ai" / module).read_text()
            self.repo.write(f"src/better_ai/{module}", f"open({str(marker)!r}, 'w').write('x')\n" + old)
        self.repo.write("src/better_ai/alpha/__init__.py", f"open({str(marker)!r}, 'w').write('x')\n")
        # trusted build.py from outside the checkout, PR checkout held as data
        trusted = self.tmp / "trusted"
        trusted.mkdir()
        shutil.copy(BUILD, trusted / "build.py")
        pr = self.tmp / "pr"
        shutil.copytree(self.repo.root / "src", pr / "src")
        built = self.tmp / "built"
        subprocess.run(
            [pyz.build_python(), "-I", str(trusted / "build.py"), "--src", str(pr / "src"), "--skills", str(built)],
            check=True,
        )
        result = subprocess.run(
            [
                pyz.build_python(),
                "-I",
                str(trusted / "build.py"),
                "--compare",
                "--src",
                str(pr / "src"),
                "--skills",
                str(built),
            ],
            capture_output=True,
            text=True,
            cwd=self.tmp,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())

    def test_compare_fails_on_a_hand_edited_pyz(self):
        self.built_repo()
        path = self.repo.pyz("beta-better")
        path.write_bytes(path.read_bytes() + b"x")
        result = self.repo.run("--compare", "--skills", str(self.repo.root / "skills"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("skills/beta-better/scripts/better.pyz", result.stderr)


class TestWhich(BuildTestCase):
    def test_which_prints_the_commit_whose_sources_have_the_hash(self):
        self.repo.build()
        first = self.repo.commit("one")
        with zipfile.ZipFile(self.repo.pyz("alpha-better")) as z:
            first_hash = json.loads(z.read("better_ai/_build.json"))["hash"]
        self.repo.write("src/better_ai/page/page.js", "export const a = 4;\n")
        self.repo.build()
        second = self.repo.commit("two")
        self.repo.write("README.md", "unrelated\n")
        self.repo.commit("three")
        result = self.repo.run("--which", first_hash)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"{first} alpha-better {first_hash}", result.stdout)
        self.assertNotIn(second, result.stdout)
        short = self.repo.run("--which", first_hash[:8])
        self.assertIn(first, short.stdout)

    def test_which_with_an_unknown_hash_exits_1(self):
        self.repo.build()
        self.repo.commit("one")
        result = self.repo.run("--which", "0000000000000000")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no commit", result.stderr)


if __name__ == "__main__":
    unittest.main()
