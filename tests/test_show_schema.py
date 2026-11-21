"""Tests for show-better's spec.json schema, and for `show.py check`, which validates a spec's shape through schema.py.

Every valid spec below passed `show.py check` before the schema existed, except that `type` ("slides") is now required;
every broken one was rejected for its shape before, and is now rejected by schema.py with the field named. Rules that
need rendering knowledge (a node an edge names, a row's cell count, the overview and focus) stay in show.py: those
specs pass the schema and are refused by `show.py check`.
"""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOW = ROOT / "skills" / "show-better"
CANVAS = ROOT / "skills" / "design-better"
ARCHITECT = ROOT / "skills" / "architect-better"
AT = "2026-11-21T10:00:00Z"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(SHOW / "scripts"))
schema = load(SHOW / "scripts" / "schema.py", "show_schema_py")
show = load(SHOW / "scripts" / "show.py", "show_py")
SCHEMAS = SHOW / "schemas"
HEAD = "The slide states one clear point."


def shape_problems(spec):
    """(field, message) of each problem the spec schema finds."""
    return schema.check_record(spec, ["spec.schema.json"], SCHEMAS)


# One valid panel of each kind: the least the kind needs.
KIND_OK = {
    "map": {"kind": "map", "sections": [{"id": "s1", "label": "Intro", "gist": "why"}], "highlight": ["s1"]},
    "concept": {
        "kind": "concept",
        "nodes": [{"id": "a", "label": "A", "highlight": True}, {"id": "b", "label": "B"}],
        "edges": [{"from": "a", "to": "b", "label": "causes"}],
    },
    "flow": {"kind": "flow", "arrow": "then", "steps": [{"label": "One", "note": "n"}, {"label": "Two"}]},
    "groups": {"kind": "groups", "groups": [{"label": "G", "items": ["x", "y"], "highlight": True}]},
    "tree": {
        "kind": "tree",
        "unit": "people",
        "root": {"label": "All", "children": [{"label": "A", "value": 3}, {"label": "B", "value": 2}]},
    },
    "sets": {"kind": "sets", "sets": ["P", "Q"], "regions": [{"label": "both", "in": ["P", "Q"], "count": 3}]},
    "matrix": {
        "kind": "matrix",
        "columns": ["c1", {"label": "c2"}],
        "rows": [{"label": "r", "cells": [None, "up"]}, {"label": "s", "cells": [{"mark": "yes"}, "no"]}],
    },
    "effects": {"kind": "effects", "rows": [{"label": "f", "outcome": "o", "effect": "up", "group": "g"}]},
    "pairs": {
        "kind": "pairs",
        "columns": ["a", "b"],
        "rows": [{"label": "r", "left": [{"label": "x", "effect": "up"}], "right": [{"label": "y"}]}],
    },
    "quadrant": {
        "kind": "quadrant",
        "basis": "judgment",
        "x": {"label": "Effort", "low": "small", "high": "large"},
        "y": {"label": "Value", "low": "low", "high": "high"},
        "items": [{"label": "o", "x": 0.2, "y": 0.8}],
    },
    "numbers": {"kind": "numbers", "figures": [{"value": "12%", "label": "of users"}, {"value": 4, "label": "x"}]},
    "units": {"kind": "units", "unit": "q", "parts": [{"label": "p", "count": 3}, {"label": "q", "count": 2}]},
    "bars": {"kind": "bars", "unit": "ms", "items": [{"label": "a", "value": 3}, {"label": "b", "value": 2.5}]},
    "slope": {
        "kind": "slope",
        "from": "2020",
        "to": "2021",
        "unit": "%",
        "items": [{"label": "a", "before": 1, "after": 2}],
    },
    "dots": {"kind": "dots", "unit": "ms", "groups": [{"label": "g", "values": [1, 2, 3.5]}]},
    "scatter": {
        "kind": "scatter",
        "x_label": "x (u)",
        "y_label": "y (u)",
        "points": [{"x": 1, "y": 2, "label": "p"}, {"x": 2, "y": 3}],
    },
    "line": {
        "kind": "line",
        "unit": "%",
        "x_label": "year",
        "series": [{"name": "s", "points": [["2020", 1], ["2021", 2]]}],
    },
    "timeline": {"kind": "timeline", "events": [{"date": "2020", "label": "start"}]},
    "table": {
        "kind": "table",
        "columns": ["item", {"label": "n", "unit": "ms"}],
        "rows": [["a", 1], ["b", 2]],
        "highlight_rows": [1],
    },
    "text": {"kind": "text", "body": ["One short paragraph."]},
    "svg": {
        "kind": "svg",
        "alt": "a box",
        "svg": '<svg viewBox="0 0 800 100"><rect x="1" y="1" width="10" height="10"/></svg>',
    },
    "lanes": {
        "kind": "lanes",
        "actors": ["A", "B"],
        "steps": [{"label": "one", "actor": "A"}, {"label": "two", "actor": "B", "highlight": True}],
    },
    "fork": {
        "kind": "fork",
        "input": "in",
        "decider": "who",
        "branches": [{"label": "x", "outcome": "helps"}, {"label": "y", "outcome": "never", "note": "n"}],
    },
}


def spec_of(*panels, **top):
    return {"type": "slides", "title": "The answer.", "question": "Why?", "panels": list(panels), **top}


def visual(kind):
    return {"headline": HEAD, "source": "test", **copy.deepcopy(KIND_OK[kind])}


OTHER_PANELS = {
    "compare": {
        "template": "compare",
        "headline": HEAD,
        "a": {"label": "Before", **copy.deepcopy(KIND_OK["bars"])},
        "b": {"label": "After", **copy.deepcopy(KIND_OK["bars"])},
        "source": {"text": "test", "section": "Results"},
    },
    "statement": {
        "template": "statement",
        "headline": HEAD,
        "figure": "12%",
        "sentence": "of users left.",
        "compare": "against 4% before",
        "source": "test",
    },
    "title": {
        "template": "title",
        "part": "Next",
        "headline": HEAD,
        "body": "A short paragraph.",
        "actions": [{"text": "Read it", "panel": 1}],
        "source": "test",
    },
}


def full_spec():
    return spec_of(*[visual(k) for k in KIND_OK], *copy.deepcopy(list(OTHER_PANELS.values())))


def edited(spec, change):
    spec = copy.deepcopy(spec)
    change(spec)
    return spec


def drop(key):
    return lambda o: o.pop(key)


def put(key, value):
    return lambda o: o.__setitem__(key, value)


class ValidSpecs(unittest.TestCase):
    def test_the_spec_with_every_kind_and_template_passes_the_schema_and_show_py(self):
        spec = full_spec()
        self.assertEqual(shape_problems(spec), [])
        errors, _, digest = show.check(spec)
        self.assertEqual(errors, [])
        self.assertTrue(digest)
        show.render(spec)
        show.render_text(spec)

    def test_each_kind_alone_passes(self):
        for kind in KIND_OK:
            with self.subTest(kind=kind):
                spec = spec_of(visual(kind))
                self.assertEqual(shape_problems(spec), [])
                self.assertEqual(show.check(spec)[0], [])

    def test_the_optional_top_level_fields_pass(self):
        spec = spec_of(
            visual("text"),
            document={"title": "Doc", "address": "https://example.com/doc", "sections": [{"id": 1, "label": "A"}]},
            lang="en",
            kicker_free=True,
            style={"background": "#fff", "point": "rgb(1, 2, 3)", "serif": "'Inter', sans-serif"},
            at=AT,
            by="agent",
        )
        self.assertEqual(shape_problems(spec), [])
        self.assertEqual(show.check(spec)[0], [])

    def test_an_item_with_a_detail_passes(self):
        panel = visual("bars")
        panel["items"][0]["detail"] = {"text": "why", "source": "s", "evidence": "strong"}
        self.assertEqual(shape_problems(spec_of(panel)), [])
        self.assertEqual(show.check(spec_of(panel))[0], [])

    def test_a_spec_without_type_is_refused_but_at_and_by_are_not_needed(self):
        spec = spec_of(visual("text"))
        self.assertEqual(shape_problems(spec), [])
        del spec["type"]
        self.assertIn("type", [f for f, _ in shape_problems(spec)])
        self.assertTrue(show.check(spec)[0])
        spec["type"] = "deck"
        self.assertIn("type", [f for f, _ in shape_problems(spec)])


# Top-level and panel-level rules: (name, spec, field the answer names).
BASE = spec_of(visual("text"))
SHAPE_BREAKS = [
    ("no title", edited(BASE, drop("title")), "title"),
    ("empty title", edited(BASE, put("title", "")), "title"),
    ("no panels", edited(BASE, drop("panels")), "panels"),
    ("no panel at all", edited(BASE, put("panels", [])), "panels"),
    ("panels not a list", edited(BASE, put("panels", {"a": 1})), "panels"),
    ("question not text", edited(BASE, put("question", 5)), "question"),
    ("document without title", edited(BASE, put("document", {"address": "https://x.org"})), "document.title"),
    (
        "document address not a URL",
        edited(BASE, put("document", {"title": "D", "address": "ftp://x"})),
        "document.address",
    ),
    ("document sections empty", edited(BASE, put("document", {"title": "D", "sections": []})), "document.sections"),
    (
        "document section without label",
        edited(BASE, put("document", {"title": "D", "sections": [{"id": "a"}]})),
        "document.sections[0].label",
    ),
    (
        "document section without id",
        edited(BASE, put("document", {"title": "D", "sections": [{"label": "a"}]})),
        "document.sections[0].id",
    ),
    ("style not an object", edited(BASE, put("style", "dark")), "style"),
    ("style unknown key", edited(BASE, put("style", {"colour": "#fff"})), "style.colour"),
    ("style bad colour", edited(BASE, put("style", {"point": "red!"})), "style.point"),
    ("style bad font", edited(BASE, put("style", {"serif": "<b>"})), "style.serif"),
    ("panel not an object", edited(BASE, put("panels", [3])), "panels[0]"),
    ("panel with note", edited(BASE, lambda s: s["panels"][0].__setitem__("note", "x")), "panels[0].note"),
    ("panel with read", edited(BASE, lambda s: s["panels"][0].__setitem__("read", "x")), "panels[0].read"),
    ("unknown template", edited(BASE, lambda s: s["panels"][0].__setitem__("template", "grid")), "panels[0].template"),
    ("no headline", edited(BASE, lambda s: s["panels"][0].pop("headline")), "panels[0].headline"),
    ("blank headline", edited(BASE, lambda s: s["panels"][0].__setitem__("headline", "  ")), "panels[0].headline"),
    ("part not text", edited(BASE, lambda s: s["panels"][0].__setitem__("part", 3)), "panels[0].part"),
    ("no kind", edited(BASE, lambda s: s["panels"][0].pop("kind")), "panels[0].kind"),
    ("unknown kind", edited(BASE, lambda s: s["panels"][0].__setitem__("kind", "pie")), "panels[0].kind"),
    (
        "source object without text or section",
        edited(BASE, lambda s: s["panels"][0].__setitem__("source", {"x": 1})),
        "panels[0].source",
    ),
    ("source a number", edited(BASE, lambda s: s["panels"][0].__setitem__("source", 5)), "panels[0].source"),
    (
        "overview not a flag",
        edited(BASE, lambda s: s["panels"][0].__setitem__("overview", "yes")),
        "panels[0].overview",
    ),
    ("focus a number", edited(BASE, lambda s: s["panels"][0].__setitem__("focus", 3)), "panels[0].focus"),
    (
        "detail without text",
        edited(spec_of(visual("bars")), lambda s: s["panels"][0]["items"][0].__setitem__("detail", {"source": "s"})),
        "panels[0].items[0].detail.text",
    ),
    (
        "detail with unknown evidence",
        edited(
            spec_of(visual("bars")),
            lambda s: s["panels"][0]["items"][0].__setitem__("detail", {"text": "t", "evidence": "huge"}),
        ),
        "panels[0].items[0].detail.evidence",
    ),
    (
        "statement without figure",
        spec_of({**OTHER_PANELS["statement"], "figure": ""}),
        "panels[0].figure",
    ),
    (
        "statement without sentence",
        spec_of({k: v for k, v in OTHER_PANELS["statement"].items() if k != "sentence"}),
        "panels[0].sentence",
    ),
    ("title body not text", spec_of({**OTHER_PANELS["title"], "body": 3}), "panels[0].body"),
    ("title actions not a list", spec_of({**OTHER_PANELS["title"], "actions": "go"}), "panels[0].actions"),
    (
        "action without text",
        spec_of({**OTHER_PANELS["title"], "actions": [{"panel": 1}]}),
        "panels[0].actions[0].text",
    ),
    (
        "action panel not a number",
        spec_of({**OTHER_PANELS["title"], "actions": [{"text": "go", "panel": "1"}]}),
        "panels[0].actions[0].panel",
    ),
    (
        "compare without side a",
        spec_of({k: v for k, v in OTHER_PANELS["compare"].items() if k != "a"}),
        "panels[0].a",
    ),
    (
        "compare side without label",
        spec_of(edited(OTHER_PANELS["compare"], lambda p: p["b"].pop("label"))),
        "panels[0].b.label",
    ),
    (
        "compare side with unknown kind",
        spec_of(edited(OTHER_PANELS["compare"], lambda p: p["a"].__setitem__("kind", "pie"))),
        "panels[0].a.kind",
    ),
    (
        "compare side with a broken kind",
        spec_of(edited(OTHER_PANELS["compare"], lambda p: p["a"]["items"][0].pop("value"))),
        "panels[0].a.items[0].value",
    ),
]


def kind_break(kind, change, field):
    panel = visual(kind)
    change(panel)
    return (f"{kind}: {field}", spec_of(panel), f"panels[0].{field}")


# One broken panel per rule of each kind.
def item(key, index=0):
    return lambda p: p[key][index]


def set_in(path, key, value):
    """Set `key` on the object at `path` (a list of keys and indexes) in a panel."""

    def change(p):
        o = p
        for step in path:
            o = o[step]
        o[key] = value

    return change


def pop_in(path, key):
    def change(p):
        o = p
        for step in path:
            o = o[step]
        o.pop(key)

    return change


KIND_BREAKS = [
    kind_break("map", set_in([], "sections", "all"), "sections"),
    kind_break("map", pop_in(["sections", 0], "label"), "sections[0].label"),
    kind_break("concept", pop_in([], "nodes"), "nodes"),
    kind_break("concept", set_in([], "nodes", []), "nodes"),
    kind_break("concept", pop_in(["nodes", 0], "id"), "nodes[0].id"),
    kind_break("concept", pop_in(["nodes", 1], "label"), "nodes[1].label"),
    kind_break("concept", pop_in([], "edges"), "edges"),
    kind_break("concept", pop_in(["edges", 0], "label"), "edges[0].label"),
    kind_break("concept", pop_in(["edges", 0], "to"), "edges[0].to"),
    kind_break("flow", pop_in([], "arrow"), "arrow"),
    kind_break("flow", set_in([], "steps", []), "steps"),
    kind_break("flow", pop_in(["steps", 1], "label"), "steps[1].label"),
    kind_break("groups", set_in([], "groups", []), "groups"),
    kind_break("groups", set_in(["groups", 0], "items", "x"), "groups[0].items"),
    kind_break("tree", pop_in([], "root"), "root"),
    kind_break("tree", pop_in(["root"], "label"), "root.label"),
    kind_break("tree", set_in(["root", "children", 0], "value", "3"), "root.children[0].value"),
    kind_break("tree", pop_in(["root", "children", 1], "label"), "root.children[1].label"),
    kind_break("sets", pop_in([], "sets"), "sets"),
    kind_break("sets", set_in([], "regions", []), "regions"),
    kind_break("sets", pop_in(["regions", 0], "in"), "regions[0].in"),
    kind_break("sets", set_in(["regions", 0], "in", []), "regions[0].in"),
    kind_break("sets", lambda p: p["regions"][0].update(label="") or p["regions"][0].pop("count"), "regions[0]"),
    kind_break("matrix", pop_in([], "columns"), "columns"),
    kind_break("matrix", pop_in(["rows", 0], "cells"), "rows[0].cells"),
    kind_break("matrix", pop_in(["rows", 1], "label"), "rows[1].label"),
    kind_break("matrix", set_in(["rows", 0], "cells", [None, "maybe"]), "rows[0].cells[1]"),
    kind_break("effects", set_in([], "rows", []), "rows"),
    kind_break("effects", set_in(["rows", 0], "effect", "sideways"), "rows[0].effect"),
    kind_break("effects", pop_in(["rows", 0], "label"), "rows[0].label"),
    kind_break("pairs", set_in([], "columns", ["a"]), "columns"),
    kind_break("pairs", set_in([], "rows", []), "rows"),
    kind_break("pairs", pop_in(["rows", 0], "label"), "rows[0].label"),
    kind_break("pairs", set_in(["rows", 0], "left", [{"effect": "up"}]), "rows[0].left[0].label"),
    kind_break("pairs", set_in(["rows", 0, "left", 0], "effect", "sideways"), "rows[0].left[0].effect"),
    kind_break("pairs", lambda p: p["rows"][0].update(left=[], right=[]), "rows[0]"),
    kind_break("quadrant", pop_in([], "basis"), "basis"),
    kind_break("quadrant", pop_in(["x"], "low"), "x.low"),
    kind_break("quadrant", pop_in([], "y"), "y"),
    kind_break("quadrant", set_in(["items", 0], "x", "0.2"), "items[0].x"),
    kind_break("quadrant", set_in([], "items", []), "items"),
    kind_break("numbers", set_in([], "figures", []), "figures"),
    kind_break("numbers", pop_in(["figures", 0], "value"), "figures[0].value"),
    kind_break("numbers", pop_in(["figures", 0], "label"), "figures[0].label"),
    kind_break("units", set_in([], "parts", []), "parts"),
    kind_break("units", set_in(["parts", 0], "count", 2.5), "parts[0].count"),
    kind_break("units", pop_in(["parts", 0], "label"), "parts[0].label"),
    kind_break("bars", set_in([], "items", []), "items"),
    kind_break("bars", set_in(["items", 0], "value", "3"), "items[0].value"),
    kind_break("bars", set_in(["items", 0], "value", True), "items[0].value"),
    kind_break("slope", pop_in([], "from"), "from"),
    kind_break("slope", pop_in([], "to"), "to"),
    kind_break("slope", set_in(["items", 0], "after", "2"), "items[0].after"),
    kind_break("slope", set_in([], "y_from_zero", False), "y_note"),
    kind_break("dots", set_in([], "groups", []), "groups"),
    kind_break("dots", set_in(["groups", 0], "values", []), "groups[0].values"),
    kind_break("dots", set_in(["groups", 0], "values", [1, "2"]), "groups[0].values[1]"),
    kind_break("scatter", pop_in([], "x_label"), "x_label"),
    kind_break("scatter", pop_in([], "y_label"), "y_label"),
    kind_break("scatter", set_in([], "points", []), "points"),
    kind_break("scatter", set_in(["points", 1], "y", None), "points[1].y"),
    kind_break("line", set_in([], "series", []), "series"),
    kind_break("line", set_in(["series", 0], "points", [["2020", 1]]), "series[0].points"),
    kind_break("line", set_in([], "y_from_zero", False), "y_note"),
    kind_break("timeline", set_in([], "events", []), "events"),
    kind_break("timeline", pop_in(["events", 0], "date"), "events[0].date"),
    kind_break("timeline", pop_in(["events", 0], "label"), "events[0].label"),
    kind_break("table", pop_in([], "columns"), "columns"),
    kind_break("table", set_in([], "columns", []), "columns"),
    kind_break("table", set_in([], "rows", []), "rows"),
    kind_break("table", set_in([], "rows", ["a", "b"]), "rows[0]"),
    kind_break("table", set_in([], "highlight_rows", "1"), "highlight_rows"),
    kind_break("text", pop_in([], "body"), "body"),
    kind_break("text", set_in([], "body", []), "body"),
    kind_break("text", set_in([], "body", ""), "body"),
    kind_break("svg", pop_in([], "alt"), "alt"),
    kind_break("svg", pop_in([], "svg"), "svg"),
    kind_break("lanes", set_in([], "actors", []), "actors"),
    kind_break("lanes", set_in([], "steps", []), "steps"),
    kind_break("lanes", pop_in(["steps", 0], "label"), "steps[0].label"),
    kind_break("lanes", pop_in(["steps", 0], "actor"), "steps[0].actor"),
    kind_break("fork", pop_in([], "input"), "input"),
    kind_break("fork", pop_in([], "decider"), "decider"),
    kind_break("fork", set_in([], "branches", [{"label": "x", "outcome": "helps"}]), "branches"),
    kind_break("fork", set_in(["branches", 0], "outcome", "wins"), "branches[0].outcome"),
    kind_break("fork", pop_in(["branches", 1], "label"), "branches[1].label"),
]


class BrokenSpecs(unittest.TestCase):
    def test_each_broken_spec_is_refused_by_the_schema_with_its_field_named(self):
        for name, spec, field in SHAPE_BREAKS + KIND_BREAKS:
            with self.subTest(name):
                fields = [f for f, _ in shape_problems(spec)]
                self.assertTrue(
                    any(f == field or f.startswith(field + ".") or f.startswith(field + "[") for f in fields),
                    (field, fields),
                )

    def test_show_py_check_refuses_each_one_and_names_the_field(self):
        for name, spec, field in SHAPE_BREAKS + KIND_BREAKS:
            with self.subTest(name):
                errors, _, _ = show.check(spec)
                self.assertTrue(errors, "accepted")
                self.assertTrue(any(field in e for e in errors), (field, errors))


# Rules show.py keeps because they need the rendering's own knowledge: the schema accepts these specs.
RENDERING_BREAKS = [
    (
        "an edge names a node that is not there",
        spec_of(edited(visual("concept"), lambda p: p["edges"][0].update({"to": "zzz"}))),
        "edge",
    ),
    (
        "a region names a set that is not there",
        spec_of(edited(visual("sets"), lambda p: p["regions"][0].update({"in": ["Z"]}))),
        "region",
    ),
    (
        "a lane step names another actor",
        spec_of(edited(visual("lanes"), lambda p: p["steps"][0].update({"actor": "Z"}))),
        "actor",
    ),
    (
        "a matrix row has too few cells",
        spec_of(edited(visual("matrix"), lambda p: p["rows"][0].update({"cells": [None]}))),
        "cell",
    ),
    ("a table row has too few cells", spec_of(edited(visual("table"), lambda p: p["rows"][0].pop())), "row 1"),
    ("a bar is negative", spec_of(edited(visual("bars"), lambda p: p["items"][0].update({"value": -1}))), "negative"),
    (
        "a unit part counts zero",
        spec_of(edited(visual("units"), lambda p: p["parts"][0].update({"count": 0}))),
        "count",
    ),
    ("units above 100", spec_of(edited(visual("units"), lambda p: p["parts"][0].update({"count": 101}))), "units"),
    (
        "a quadrant position beyond 1",
        spec_of(edited(visual("quadrant"), lambda p: p["items"][0].update({"x": 1.5}))),
        "between 0 and 1",
    ),
    ("a pair has three columns", spec_of(edited(visual("pairs"), lambda p: p["columns"].append("c"))), "two headings"),
    (
        "a line point has a text y",
        spec_of(edited(visual("line"), lambda p: p["series"][0]["points"][0].__setitem__(1, "a"))),
        "non-numeric",
    ),
    (
        "a tree deeper than four levels",
        spec_of(
            edited(
                visual("tree"),
                lambda p: p["root"].update(
                    {
                        "children": [
                            {
                                "label": "a",
                                "children": [
                                    {
                                        "label": "b",
                                        "children": [
                                            {
                                                "label": "c",
                                                "children": [{"label": "d", "children": [{"label": "e", "value": 1}]}],
                                            }
                                        ],
                                    }
                                ],
                            }
                        ]
                    }
                ),
            )
        ),
        "levels",
    ),
    (
        "a tree whose children outweigh the parent",
        spec_of(edited(visual("tree"), lambda p: p["root"].update({"value": 1}))),
        "sum",
    ),
    ("a map without sections", spec_of({"headline": HEAD, "source": "t", "kind": "map"}), "sections"),
    ("an svg that is not one element", spec_of(edited(visual("svg"), lambda p: p.update({"svg": "<p>x</p>"}))), "svg"),
    (
        "an svg with a script",
        spec_of(edited(visual("svg"), lambda p: p.update({"svg": '<svg viewBox="0 0 8 8"><script>x</script></svg>'}))),
        "svg",
    ),
    (
        "an action pointing past the last panel",
        spec_of({**OTHER_PANELS["title"], "actions": [{"text": "go", "panel": 4}]}),
        "points to panel 4",
    ),
    ("focus without an overview", spec_of(visual("flow"), edited(visual("text"), put("focus", ["One"]))), "overview"),
    (
        "two overviews",
        spec_of(edited(visual("flow"), put("overview", True)), edited(visual("flow"), put("overview", True))),
        "overview",
    ),
    (
        "an overview that is not a flow, timeline, concept or groups",
        spec_of(edited(visual("text"), put("overview", True))),
        "overview",
    ),
    (
        "a focus label the overview lacks",
        spec_of(edited(visual("flow"), put("overview", True)), edited(visual("text"), put("focus", ["Nine"]))),
        "focus",
    ),
]


class RenderingChecks(unittest.TestCase):
    def test_the_schema_accepts_them_and_show_py_check_refuses_them(self):
        for name, spec, word in RENDERING_BREAKS:
            with self.subTest(name):
                self.assertEqual(shape_problems(spec), [])
                errors, _, _ = show.check(spec)
                self.assertTrue(errors, "accepted")
                self.assertTrue(any(word in e for e in errors), (word, errors))

    def test_a_shape_error_stops_the_rendering_checks_and_prints_no_digest(self):
        errors, _, digest = show.check(edited(BASE, drop("title")))
        self.assertEqual(digest, [])
        self.assertTrue(all(e.startswith("title:") or ": " in e for e in errors))


class Warnings(unittest.TestCase):
    def test_the_readability_warnings_stay(self):
        spec = spec_of({**visual("bars"), "headline": "Topic"}, {**OTHER_PANELS["statement"], "compare": ""})
        _, warnings, _ = show.check(spec)
        self.assertTrue(any("full sentence" in w for w in warnings), warnings)
        self.assertTrue(any("no 'compare'" in w for w in warnings), warnings)

    def test_the_digest_lists_every_value(self):
        _, _, digest = show.check(full_spec())
        text = "\n".join(digest)
        for word in ("TITLE: The answer.", "[1] VISUAL MAP", "causes", "12% of users left.", "Read it"):
            self.assertIn(word, text)


class CommandLine(unittest.TestCase):
    def run_check(self, spec):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "spec.json"
            path.write_text(json.dumps(spec))
            script = str(SHOW / "scripts" / "show.py")
            return subprocess.run([sys.executable, "-I", script, "check", str(path)], capture_output=True, text=True)

    def test_check_exits_zero_for_a_valid_spec(self):
        done = self.run_check(full_spec())
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_check_exits_one_and_names_the_field(self):
        done = self.run_check(edited(spec_of(visual("bars")), lambda s: s["panels"][0]["items"][0].pop("value")))
        self.assertEqual(done.returncode, 1)
        self.assertIn("panels[0].items[0].value", done.stderr)

    def test_schema_py_checks_the_spec_file_as_a_folder_entry(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / ".show" / "deck"
            folder.mkdir(parents=True)
            (folder / "spec.json").write_text(json.dumps(full_spec()))
            self.assertEqual(schema.check_paths([folder / "spec.json"], SCHEMAS), [])
            bad = edited(spec_of(visual("bars")), lambda s: s["panels"][0]["items"][0].pop("value"))
            (folder / "spec.json").write_text(json.dumps(bad))
            errors = schema.check_paths([folder / "spec.json"], SCHEMAS)
            self.assertEqual([e.field for e in errors], ["panels[0].items[0].value"])


def note(**more):
    return {"type": "note", "at": AT, "by": "user", "id": "m-1", "text": "hi", "to": None, **more}


def note_problems(skill, events, event):
    names = ["conversation.schema.json", events]
    return schema.check_record(event, names, ROOT / "skills" / skill / "schemas")


class SlideOnNotes(unittest.TestCase):
    ON = {"slide": 2, "part": "Does it arrive?"}

    def test_a_show_note_needs_the_slide_it_was_written_on(self):
        self.assertIn(("on", "required"), note_problems("show-better", "show-events.schema.json", note()))

    def test_a_show_note_with_its_slide_is_accepted(self):
        self.assertEqual(note_problems("show-better", "show-events.schema.json", note(on=self.ON)), [])
        self.assertEqual(
            note_problems("show-better", "show-events.schema.json", note(on={"slide": 1, "part": None})), []
        )

    def test_a_show_note_with_a_slide_that_is_not_a_number_is_refused(self):
        fields = [
            f for f, _ in note_problems("show-better", "show-events.schema.json", note(on={"slide": "2", "part": "p"}))
        ]
        self.assertIn("on.slide", fields)

    def test_a_canvas_note_with_on_is_refused(self):
        fields = [f for f, _ in note_problems("design-better", "canvas-events.schema.json", note(on=self.ON))]
        self.assertIn("on", fields)
        self.assertEqual(note_problems("design-better", "canvas-events.schema.json", note()), [])

    def test_an_architect_note_with_on_is_refused(self):
        fields = [f for f, _ in note_problems("architect-better", "architect-events.schema.json", note(on=self.ON))]
        self.assertIn("on", fields)
        self.assertEqual(note_problems("architect-better", "architect-events.schema.json", note()), [])

    def test_the_slide_page_sends_the_slide_with_each_note(self):
        source = (SHOW / "scripts" / "show.js").read_text(encoding="utf-8")
        self.assertRegex(source, r"noteParams:\s*function \(\) \{ return \{ on: \{ slide: cur \+ 1, part: [^}]*null")


if __name__ == "__main__":
    unittest.main()
