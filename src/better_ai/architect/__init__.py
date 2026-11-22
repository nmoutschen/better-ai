"""architect-better: units are `.architect/<change>/`, headed by `architect.json`."""

from ..skill import Skill, UnitKind
from . import checks  # noqa: F401  (registers the hooks the schemas name)

SKILL = Skill(
    name="architect-better",
    package="architect",
    kinds=(UnitKind(kind="change", folder=".architect", head="architect.json", head_type="architect"),),
    exclude=".architect/",
)
