"""The entry point of a built `better.pyz`: the build copies this file to the zip's root as `__main__.py`.

It reads `better_ai/_build.json` (the skill, the source hash) without importing anything else from the package, so even
an import error in the package is reported as `bug in better.pyz <skill> <hash>: ...` with exit code 5. Run from source
(the tests), there is no `_build.json`: the skill is BETTER_AI_SKILL and the hash is "source".
"""

import json
import os
import sys


def _build() -> tuple:
    try:
        from importlib.resources import files

        data = json.loads((files("better_ai") / "_build.json").read_text(encoding="utf-8"))
        return data["skill"], data["hash"]
    except (OSError, ValueError, KeyError, ImportError):
        return os.environ.get("BETTER_AI_SKILL") or "unknown", "source"


def main() -> int:
    try:
        from better_ai import cli
    except BaseException as error:  # an import error in the package itself: still the one bug line
        skill, hash = _build()
        what = f"{type(error).__name__}: {error}"
        missing = error.name if isinstance(error, ModuleNotFoundError) else None
        named = f" (missing: {missing})" if missing else ""
        line = f"bug in better.pyz {skill} {hash}: {what}{named}; set BETTER_AI_TRACEBACK=1 for the full trace"
        print(" ".join(line.split()).encode("ascii", "backslashreplace").decode("ascii"), file=sys.stderr)
        if os.environ.get("BETTER_AI_TRACEBACK") == "1":
            import traceback

            traceback.print_exc()
        return 5
    return cli.main()


if __name__ == "__main__":
    sys.exit(main())
