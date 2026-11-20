"""Tests for the deterministic graders in skill_evals/grading/files.py, on local planted repositories."""

from conftest import Plant

from skill_evals.grading import files

FEES = "def rush(minutes):\n    return 5 if minutes > 15 else 0\n"
FIXED = "def rush(minutes):\n    return 5 if minutes >= 15 else 0\n"
TEST = (
    "from unittest import TestCase, main\nfrom fees import rush\n\n\nclass Tests(TestCase):\n"
    "    def test_boundary(self):\n        self.assertEqual(rush(15), 5)\n\n\nif __name__ == '__main__':\n    main()\n"
)


async def test_file_unchanged_and_planted_unchanged(plant: Plant) -> None:
    """A changed planted file fails both, unless planted_unchanged lists it; new files are allowed."""
    repo = await plant({"fees.py": FEES, "notes.txt": "keep\n"})
    await repo.sandbox_env.write_file("fees.py", FIXED)
    await repo.sandbox_env.write_file("NEW.md", "a note\n")
    assert await files.file_unchanged({"path": "notes.txt"}, repo)
    assert not await files.file_unchanged({"path": "fees.py"}, repo)
    assert not await files.file_unchanged({"path": "missing.py"}, repo)
    assert not await files.planted_unchanged({}, repo)
    assert await files.planted_unchanged({"except": ["fee*.py"]}, repo)


async def test_file_keeps(plant: Plant) -> None:
    """Additions and re-indentation pass; a removed line fails."""
    repo = await plant({"a.py": "x = 1\n\ny = 2\n"})
    await repo.sandbox_env.write_file("a.py", "x = 1\nz = 3\n    y = 2\n")
    assert await files.file_keeps({"path": "a.py"}, repo)
    await repo.sandbox_env.write_file("a.py", "y = 2\n")
    assert not await files.file_keeps({"path": "a.py"}, repo)


async def test_file_keeps_accepts_an_extended_import(plant: Plant) -> None:
    """Importing more names from the same module keeps the planted import; dropping one or switching module does not."""
    repo = await plant({"test_fees.py": TEST})
    await repo.sandbox_env.write_file(
        "test_fees.py", TEST.replace("from fees import rush", "from fees import late, rush")
    )
    assert await files.file_keeps({"path": "test_fees.py"}, repo)
    await repo.sandbox_env.write_file("test_fees.py", TEST.replace("from fees import rush", "from fees import late"))
    assert not await files.file_keeps({"path": "test_fees.py"}, repo)
    await repo.sandbox_env.write_file("test_fees.py", TEST.replace("from fees import rush", "from other import rush"))
    assert not await files.file_keeps({"path": "test_fees.py"}, repo)


async def test_file_contains_and_not_contains(plant: Plant) -> None:
    """Both need the file; each passes on the matching outcome."""
    repo = await plant({"a.py": "TODO = 1\n"})
    assert await files.file_contains({"path": "a.py", "pattern": r"TODO"}, repo)
    assert not await files.file_not_contains({"path": "a.py", "pattern": r"TODO"}, repo)
    assert not await files.file_contains({"path": "gone.py", "pattern": "x"}, repo)
    assert not await files.file_not_contains({"path": "gone.py", "pattern": "x"}, repo)


async def test_notes_only(plant: Plant) -> None:
    """Markdown notes pass; any other changed or new file fails, Python caches excepted."""
    repo = await plant({"a.py": "x = 1\n"})
    await repo.sandbox_env.write_file("QUESTIONS.md", "Which one?\n")
    await repo.sandbox_env.write_file("__pycache__/a.cpython-312.pyc", "cache")
    assert await files.notes_only({}, repo)
    await repo.sandbox_env.write_file("b.py", "y = 2\n")
    repo = files.Checkout(repo.sandbox_env, repo.start, repo.workdir)
    assert not await files.notes_only({}, repo)


async def test_note_written(plant: Plant) -> None:
    """A new Markdown note passes, also in a folder Git ignores; an edited planted note or a code file does not."""
    repo = await plant({"a.py": "x = 1\n", "README.md": "Shop\n"})
    await repo.sandbox_env.write_file("README.md", "Shop, audited\n")
    await repo.sandbox_env.write_file("b.py", "y = 2\n")
    assert not await files.note_written({}, repo)
    await repo.sandbox_env.exec(["sh", "-c", "echo .code/ >> .git/info/exclude"])
    await repo.sandbox_env.write_file(".code/audit/findings.md", "1. VAT\n")
    repo = files.Checkout(repo.sandbox_env, repo.start, repo.workdir)
    assert await files.note_written({}, repo)


async def test_diff_max_lines(plant: Plant) -> None:
    """Counts added plus removed lines in planted files only."""
    repo = await plant({"a.py": "x = 1\n"})
    await repo.sandbox_env.write_file("a.py", "x = 2\n")
    await repo.sandbox_env.write_file("test_new.py", "\n" * 50)
    assert await files.diff_max_lines({"max": 2}, repo)
    assert not await files.diff_max_lines({"max": 1}, repo)


async def test_command_passes_and_fails(plant: Plant) -> None:
    """The hidden file is found under $GRADE_FILES and the planted commit under $START_COMMIT."""
    repo = await plant({"fees.py": FEES})
    await repo.sandbox_env.write_file("fees.py", FIXED)
    check = {"check.py": "from fees import rush\nassert rush(15) == 5\n"}
    spec = {"cmd": 'PYTHONPATH=. python "$GRADE_FILES/check.py"', "files": check}
    assert await files.command_passes(spec, repo)
    assert not await files.command_fails(spec, repo)
    planted = {"cmd": 'git show "$START_COMMIT:fees.py" | grep -q "> 15"'}
    assert await files.command_passes(planted, repo)
    assert not repo.notes


async def test_command_timeout_is_noted(plant: Plant) -> None:
    """A timeout fails the grader and leaves a note."""
    repo = await plant({"a.py": ""})
    assert not await files.command_passes({"cmd": "sleep 5", "timeout": 1}, repo)
    assert repo.notes


async def test_catches_bug_with_restore(plant: Plant) -> None:
    """A new test that passes on the fix and fails on the planted code catches the bug."""
    repo = await plant({"fees.py": FEES})
    await repo.sandbox_env.write_file("fees.py", FIXED)
    await repo.sandbox_env.write_file("test_fees.py", TEST)
    assert await files.catches_bug({"tests": ["test_fees.py"], "restore": ["fees.py"]}, repo)


async def test_catches_bug_with_replacement_files(plant: Plant) -> None:
    """A test that cannot tell the replacement apart from the fix does not catch the bug."""
    repo = await plant({"fees.py": FEES})
    await repo.sandbox_env.write_file("fees.py", FIXED)
    weak = TEST.replace("rush(15), 5", "rush(16), 5")
    await repo.sandbox_env.write_file("test_fees.py", weak)
    assert not await files.catches_bug({"files": {"fees.py": FEES}}, repo)


async def test_catches_bug_needs_a_passing_test(plant: Plant) -> None:
    """A test that fails on the submitted code does not count, and neither does an unchanged planted test."""
    repo = await plant({"fees.py": FEES, "test_fees.py": TEST})
    assert not await files.catches_bug({"tests": ["test_fees.py"], "restore": ["fees.py"]}, repo)


async def test_changed_lists_markdown_notes_git_ignores(plant: Plant) -> None:
    """A Markdown note in a folder Git ignores counts as new; other ignored files do not."""
    repo = await plant({"fees.py": FEES})
    await repo.sandbox_env.exec(["bash", "-c", "echo .code/ >> .git/info/exclude"])
    await repo.sandbox_env.write_file(".code/fix/tasks.md", "# Tasks\n")
    await repo.sandbox_env.write_file(".code/fix/check.py", "x = 1\n")
    assert await repo.all_changed() == {".code/fix/tasks.md"}
