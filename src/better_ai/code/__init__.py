"""code-better: units are `.code/<change>/` (headed by `code.json`) and `.code/audit/<date>/` (`audit.json`)."""

from .. import page
from ..skill import Skill, UnitKind
from . import checks, hooks  # noqa: F401  (register the hooks the schemas and the commands name)

SKILL = Skill(
    name="code-better",
    package="code",
    kinds=(
        UnitKind(kind="change", folder=".code", head="code.json", head_type="code", folders=("logs",)),
        UnitKind(kind="audit", folder=".code/audit", head="audit.json", head_type="audit"),
    ),
)

from . import dashboard  # noqa: E402  (registers `render`)

page.register(SKILL, dashboard.SPEC)
