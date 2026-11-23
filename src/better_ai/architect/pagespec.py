"""The architecture page on the shared shell: its main section, its own stylesheet and script, and what it loads."""

from __future__ import annotations

import hashlib

from .. import page, paths, resources
from ..paths import Unit
from . import SKILL, model
from .commands import RENDER_FOLDER, static_data


def load(unit: Unit) -> dict:
    return model.load(unit)


def revision(unit: Unit) -> str:
    """What the page reloads on: the unit's record files and the page's own files. The conversation is not in it."""
    digest = hashlib.sha256()
    for name in model.FILES:
        try:
            digest.update(paths.read_bytes(unit, name))
        except (OSError, paths.Refused):
            digest.update(b"-")
    for name in ("architect/page.html", "architect/page.js", "architect/page.css"):
        digest.update(resources.read_bytes(name))
    return digest.hexdigest()


SPEC = page.register(
    SKILL,
    page.PageSpec(
        title="Architecture design",
        agent="architect",
        main="architect/page.html",
        load=load,
        events="architect-events.schema.json",
        assets={"/architect.css": "architect/page.css", "/architect.js": "architect/page.js"},
        css=("/architect.css",),
        js=("/architect.js",),
        capabilities=("pins", "accept", "confirm", "approve"),
        empty="Click a box, arrow or step to comment on it, or write to the architect below.",
        revision=revision,
        rendered=f"{RENDER_FOLDER}/index.html",
        static_data=static_data,
    ),
)
