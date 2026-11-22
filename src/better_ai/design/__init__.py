"""design-better: units are `.design/<slug>/`, headed by `canvas.json`."""

from ..skill import Skill, UnitKind

SKILL = Skill(
    name="design-better",
    package="design",
    kinds=(UnitKind(kind="canvas", folder=".design", head="canvas.json", head_type="canvas"),),
    exclude=".design/",
)
