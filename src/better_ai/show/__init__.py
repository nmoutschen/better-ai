"""show-better: units are `.show/<slug>/`, headed by `spec.json`."""

from ..skill import Skill, UnitKind
from . import checks  # noqa: F401  (registers the hooks the schemas name)

SKILL = Skill(
    name="show-better",
    package="show",
    kinds=(UnitKind(kind="slides", folder=".show", head="spec.json", head_type="slides"),),
    exclude=".show/",
)
