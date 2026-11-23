"""research-better: units are research boards, `.research/<slug>/`, headed by `brief.json`."""

from ..skill import Skill, UnitKind
from . import checks, hooks  # noqa: F401  (register the hooks the schemas and the record verbs use)

SKILL = Skill(
    name="research-better",
    package="research",
    kinds=(
        UnitKind(
            kind="board",
            folder=".research",
            head="brief.json",
            head_type="brief",
            folders=("questions", "claims", "sources", "logs"),
        ),
    ),
    exclude=".research/",
)

from . import board  # noqa: E402,F401  (registers the page and `render`; it needs SKILL above)
