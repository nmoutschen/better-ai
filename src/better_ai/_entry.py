"""The entry point of a built `better.pyz`: the build copies this file to the zip's root as `__main__.py`.

It reads `better_ai/_build.json` (the skill, the source hash) without importing anything else from the package, so even
an import error in the package is reported as `bug in better.pyz <skill> <hash>: ...` with exit code 5. Run from source
(the tests), there is no `_build.json`: the skill is BETTER_AI_SKILL and the hash is "source".
"""

import contextlib
import json
import os
import sys
import traceback


def _build() -> tuple:
    try:
        from importlib.resources import files

        data = json.loads((files("better_ai") / "_build.json").read_text(encoding="utf-8"))
        return data["skill"], data["hash"]
    except (OSError, ValueError, KeyError, ImportError):
        return os.environ.get("BETTER_AI_SKILL") or "unknown", "source"


def report_bug(skill: str, hash: str, error: BaseException) -> int:
    """Print the one line for an internal error, `bug in better.pyz <skill> <hash>: <what> ...`, naming the module or
    file a missing piece is, and the traceback when BETTER_AI_TRACEBACK is 1; return exit code 5. `cli` uses it too."""
    what = f"{type(error).__name__}: {error}" if str(error) else type(error).__name__
    missing = error.name if isinstance(error, ModuleNotFoundError) else None
    if missing is None and isinstance(error, FileNotFoundError) and error.filename:
        missing = error.filename
    named = f" (missing: {missing})" if missing else ""
    line = f"bug in better.pyz {skill} {hash}: {what}{named}; set BETTER_AI_TRACEBACK=1 for the full trace"
    with contextlib.suppress(Exception):  # stderr may be closed: the exit code still says it
        print(" ".join(line.split()).encode("ascii", "backslashreplace").decode("ascii"), file=sys.stderr)
        if os.environ.get("BETTER_AI_TRACEBACK") == "1":
            traceback.print_exception(error, file=sys.stderr)
    return 5


def main() -> int:
    try:
        from better_ai import cli
    except BaseException as error:  # an import error in the package itself: still the one bug line
        skill, hash = _build()
        return report_bug(skill, hash, error)
    return cli.main(detach=True)


if __name__ == "__main__":
    sys.exit(main())
