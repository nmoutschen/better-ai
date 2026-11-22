"""code-better: units are `.code/<change>/` (headed by `code.json`) and `.code/audit/<date>/` (`audit.json`)."""

from ..skill import Skill, UnitKind
from . import checks  # noqa: F401  (registers the hooks the schemas name)

SKILL = Skill(
    name="code-better",
    package="code",
    kinds=(
        UnitKind(kind="change", folder=".code", head="code.json", head_type="code", folders=("logs",)),
        UnitKind(kind="audit", folder=".code/audit", head="audit.json", head_type="audit"),
    ),
    exclude=".code/",
)
