"""Skill evals: run Claude Code on planted cases in a Docker sandbox and grade what it did.

`cases` turns case folders into Inspect samples, `agent` runs the real Claude Code CLI (or a scripted
fake for plumbing runs), `transcript` turns its stream-json output into Inspect messages, and
`grading` scores the result with deterministic file checks and an LLM judge.
"""

from pathlib import Path


def planted_repo_files(directory: Path) -> dict[str, Path]:
    """Map planted paths to their source files, with case files overriding the skill base."""
    files: dict[str, Path] = {}
    for repo in (directory.parent / "_base", directory / "repo"):
        files.update(
            (path.relative_to(repo).as_posix(), path)
            for path in sorted(repo.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
        )
    return files
