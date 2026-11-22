"""research-better: units are research boards, `.research/<slug>/`, headed by `brief.json`."""

from ..skill import Skill, UnitKind
from . import checks  # noqa: F401  (registers the hooks the schemas name)

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
