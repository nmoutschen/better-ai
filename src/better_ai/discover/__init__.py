"""discover-better: units are discoveries, `.discover/<idea>/`, headed by `discover.json`.

The package holds the unit kind and its schemas (`schemas/`), the one function that derives what an item is from the
records (`derive`), the rules the coordinator's writes must meet (`rules_changes`, `rules_evidence`, `rules_moves`), the
verbs `summary` and `brief`, and the page (`pagespec`). Nothing here makes a network call: a verifier reads a page
itself, from the shell, and hands `better.pyz` the file.
"""

from ..skill import Skill, UnitKind

SKILL = Skill(
    name="discover-better",
    package="discover",
    kinds=(
        UnitKind(
            kind="discovery",
            folder=".discover",
            head="discover.json",
            head_type="discover",
            folders=("evidence", "sources"),
        ),
    ),
)

from . import (  # noqa: E402,F401  (each registers its rules, verbs or page when imported; they need SKILL above)
    brief,
    derive,
    pagespec,
    rules_changes,
    rules_evidence,
    rules_moves,
    summary,
)
