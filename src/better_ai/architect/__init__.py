"""architect-better: units are `.architect/<change>/`, headed by `architect.json`.

The package holds the change folder's reader (`model`), the diagram (`diagram`), the checks the schemas name
(`checks`), the skill's own verbs (`commands`: review, specs, register, render) and the page (`pagespec`, with
`page.html`, `page.js` and `page.css`). `better.pyz` is the only entry.
"""

from ..skill import Skill, UnitKind

SKILL = Skill(
    name="architect-better",
    package="architect",
    kinds=(UnitKind(kind="change", folder=".architect", head="architect.json", head_type="architect"),),
)

from . import checks, commands, pagespec  # noqa: E402,F401  (register the hooks, the verbs and the page)
