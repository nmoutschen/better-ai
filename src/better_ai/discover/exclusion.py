"""`create` says so when it adds `.discover/` to the repository's git exclusion.

The shared `create` already adds the skill's `exclude` line to the repository's `info/exclude` and mentions it only when
it had to skip it. The discovery folder holds the user's evidence, so this skill also tells the user when the line was
added: the folder is theirs, and no agent commits it.
"""

from .. import paths, records


@records.create_step("discover-better")
def say_when_the_folder_is_excluded(ctx: records.CreateContext):
    """After the head is written: add the exclusion first, so the shared step finds it present, and say that it was added."""
    line = ctx.run.skill.exclude

    def add() -> None:
        if line and paths.add_exclude(ctx.unit, line) == "added":
            ctx.run.out(f"added {line} to the repository's git exclusion: nothing in it is committed unless you ask")

    return add
