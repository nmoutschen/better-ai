"""design-better: units are `.design/<slug>/`, headed by `canvas.json`."""

from ..skill import Skill, UnitKind
from . import checks  # noqa: F401  (registers the hooks the schemas name)

SKILL = Skill(
    name="design-better",
    package="design",
    kinds=(UnitKind(kind="canvas", folder=".design", head="canvas.json", head_type="canvas"),),
)

from . import canvas  # noqa: E402  (registers `render` and the page; needs SKILL above)

canvas.register(SKILL)
