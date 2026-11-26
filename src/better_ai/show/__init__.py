"""show-better: units are `.show/<slug>/`, headed by `spec.json`."""

from .. import page
from ..skill import Skill, UnitKind
from . import checks, commands  # noqa: F401  (registers the hooks the schemas name, and the verbs)

SKILL = Skill(
    name="show-better",
    package="show",
    kinds=(UnitKind(kind="slides", folder=".show", head="spec.json", head_type="slides"),),
)

page.register(SKILL, commands.PAGE_SPEC)
