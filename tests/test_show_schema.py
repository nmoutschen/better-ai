"""Tests for show-better's spec.json schema, and for `show.py check`, which validates a spec through schema.py.

The valid specs below passed `show.py check` before the schema existed, except that `type` ("slides") is now required.
Every broken one is refused by schema.py with the field named: its shape (types, required fields, allowed values), what
its parts say about each other (a node an edge names, a row's cell count, the overview and focus: the `show_spec` hook),
and number limits (`minimum`, `maximum`). show.py keeps only what the drawing needs: a tree deeper than four levels,
more than 100 units, an svg's elements, and the warnings and the digest; those specs pass the schema and are refused
by `show.py check`. A field that is optional accepts null as absent, and no wrongly typed value crashes a check.
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
    return schema.check_record(spec, ["spec.schema.json"], SCHEMAS, cross=True)


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
    kind_break("groups", pop_in(["groups", 0], "label"), "groups[0].label"),
    kind_break("bars", pop_in(["items", 0], "label"), "items[0].label"),
    kind_break("slope", pop_in(["items", 0], "label"), "items[0].label"),
    kind_break("dots", pop_in(["groups", 0], "label"), "groups[0].label"),
    kind_break("quadrant", pop_in(["items", 0], "label"), "items[0].label"),
    kind_break("line", pop_in(["series", 0], "name"), "series[0].name"),
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
        for name, spec, field in BROKEN:
            with self.subTest(name):
                fields = [f for f, _ in shape_problems(spec)]
                self.assertTrue(
                    any(f == field or f.startswith(field + ".") or f.startswith(field + "[") for f in fields),
                    (field, fields),
                )

    def test_show_py_check_refuses_each_one_and_names_the_field(self):
        for name, spec, field in BROKEN:
            with self.subTest(name):
                errors, _, _ = show.check(spec)
                self.assertTrue(errors, "accepted")
                self.assertTrue(any(field in e for e in errors), (field, errors))


def tree_of(*children, value=None):
    return {"label": "All", **({"value": value} if value is not None else {}), "children": list(children)}


def deep_tree():
    node = {"label": "e", "value": 1}
    for name in "dcba":
        node = {"label": name, "children": [node]}
    return {"label": "All", "children": [node]}


def overview_panel():
    return edited(visual("flow"), put("overview", True))


# What refers to something else in the spec, and the limits a number must keep: refused by schema.py, with the field.
CROSS_BREAKS = [
    (
        "an edge names a node that is not there",
        spec_of(edited(visual("concept"), lambda p: p["edges"][0].update({"to": "zzz"}))),
        "panels[0].edges[0].to",
    ),
    (
        "an edge's source names a node that is not there",
        spec_of(edited(visual("concept"), lambda p: p["edges"][0].update({"from": "zzz"}))),
        "panels[0].edges[0].from",
    ),
    (
        "an edge in a compare side names a node that is not there",
        spec_of(
            {
                **OTHER_PANELS["compare"],
                "a": {"label": "A", **edited(visual("concept"), lambda p: p["edges"][0].update({"to": "zzz"}))},
            }
        ),
        "panels[0].a.edges[0].to",
    ),
    (
        "a region names a set that is not there",
        spec_of(edited(visual("sets"), lambda p: p["regions"][0].update({"in": ["Z"]}))),
        "panels[0].regions[0].in",
    ),
    (
        "a lane step names another actor",
        spec_of(edited(visual("lanes"), lambda p: p["steps"][0].update({"actor": "Z"}))),
        "panels[0].steps[0].actor",
    ),
    (
        "a matrix row has too few cells",
        spec_of(edited(visual("matrix"), lambda p: p["rows"][0].update({"cells": [None]}))),
        "panels[0].rows[0].cells",
    ),
    (
        "a table row has too few cells",
        spec_of(edited(visual("table"), lambda p: p["rows"][1].pop())),
        "panels[0].rows[1]",
    ),
    (
        "a unit part counts zero",
        spec_of(edited(visual("units"), lambda p: p["parts"][0].update({"count": 0}))),
        "panels[0].parts[0].count",
    ),
    (
        "a quadrant position beyond 1",
        spec_of(edited(visual("quadrant"), lambda p: p["items"][0].update({"x": 1.5}))),
        "panels[0].items[0].x",
    ),
    (
        "a quadrant position below 0",
        spec_of(edited(visual("quadrant"), lambda p: p["items"][0].update({"y": -0.1}))),
        "panels[0].items[0].y",
    ),
    (
        "a pair has three columns",
        spec_of(edited(visual("pairs"), lambda p: p["columns"].append("c"))),
        "panels[0].columns",
    ),
    (
        "a line point has a text y",
        spec_of(edited(visual("line"), lambda p: p["series"][0]["points"][0].__setitem__(1, "a"))),
        "panels[0].series[0].points[0][1]",
    ),
    (
        "a tree whose children outweigh the parent",
        spec_of(edited(visual("tree"), lambda p: p["root"].update({"value": 1}))),
        "panels[0].root",
    ),
    (
        "a map without sections",
        spec_of({"headline": HEAD, "source": "t", "kind": "map"}),
        "panels[0].sections",
    ),
    (
        "an action pointing past the last panel",
        spec_of({**OTHER_PANELS["title"], "actions": [{"text": "go", "panel": 4}]}),
        "panels[0].actions[0].panel",
    ),
    (
        "an action pointing at panel 0",
        spec_of({**OTHER_PANELS["title"], "actions": [{"text": "go", "panel": 0}]}),
        "panels[0].actions[0].panel",
    ),
    (
        "focus without an overview",
        spec_of(visual("flow"), edited(visual("text"), put("focus", ["One"]))),
        "panels[1].focus",
    ),
    (
        "two overviews",
        spec_of(overview_panel(), overview_panel()),
        "panels[1].overview",
    ),
    (
        "an overview that is not a flow, timeline, concept or groups",
        spec_of(edited(visual("text"), put("overview", True))),
        "panels[0].kind",
    ),
    (
        "an overview that is not a visual panel",
        spec_of({**OTHER_PANELS["statement"], "overview": True}),
        "panels[0].template",
    ),
    (
        "a focus label the overview lacks",
        spec_of(overview_panel(), edited(visual("text"), put("focus", ["Nine"]))),
        "panels[1].focus",
    ),
]
CROSS_BREAKS += [
    (
        "a bar is negative",
        spec_of(edited(visual("bars"), lambda p: p["items"][0].update({"value": -1}))),
        "panels[0].items[0].value",
    )
]
BROKEN = SHAPE_BREAKS + KIND_BREAKS + CROSS_BREAKS

# What stays in show.py, because the drawing cannot show it: the schema accepts these specs.
RENDERING_BREAKS = [
    (
        "units above 100",
        spec_of(edited(visual("units"), lambda p: p["parts"][0].update({"count": 101}))),
        "units",
    ),
    (
        "a tree deeper than four levels",
        spec_of(edited(visual("tree"), lambda p: p.update({"root": deep_tree()}))),
        "levels",
    ),
    (
        "an svg that is not one element",
        spec_of(edited(visual("svg"), lambda p: p.update({"svg": "<p>x</p>"}))),
        "svg",
    ),
    (
        "an svg with a script",
        spec_of(edited(visual("svg"), lambda p: p.update({"svg": '<svg viewBox="0 0 8 8"><script>x</script></svg>'}))),
        "svg",
    ),
]


class RenderingChecks(unittest.TestCase):
    def test_what_the_drawing_cannot_show_is_accepted_by_the_schema_and_refused_by_show_py_check(self):
        for name, spec, word in RENDERING_BREAKS:
            with self.subTest(name):
                self.assertEqual(shape_problems(spec), [])
                errors, _, _ = show.check(spec)
                self.assertTrue(errors, "accepted")
                self.assertTrue(any(word in e for e in errors), (word, errors))

    def test_a_note_or_read_on_a_panel_keeps_the_old_hint_to_move_it_into_source(self):
        for old in ("note", "read"):
            with self.subTest(old):
                errors, _, _ = show.check(edited(BASE, lambda s, old=old: s["panels"][0].__setitem__(old, "x")))
                self.assertEqual(len(errors), 1)
                self.assertTrue(
                    errors[0].startswith(f"panels[0].{old}: '{old}' is no longer used: move it into 'source'")
                )

    def test_a_missing_template_is_worded_as_absent(self):
        spec = edited(BASE, lambda s: s["panels"][0].pop("kind"))
        self.assertIn(("panels[0].kind", "required when template is absent"), shape_problems(spec))

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
        problems = note_problems("show-better", "show-events.schema.json", note())
        self.assertEqual([(f, m.split(" ")[0]) for f, m in problems], [("on", "required")])

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


# The crashes a verifier found: wrongly typed values the hook once met with a TypeError.
CRASH_1 = {
    "type": "slides",
    "title": "The answer.",
    "question": "Why?",
    "panels": [
        {
            "headline": HEAD,
            "source": "t",
            "kind": "concept",
            "nodes": [{"id": ["a"], "label": "A"}, {"id": "b", "label": "B"}],
            "edges": [{"from": "a", "to": "b"}],
        }
    ],
}
CRASH_2 = {
    "type": "slides",
    "title": "The answer.",
    "question": "Why?",
    "panels": [
        {
            "headline": HEAD,
            "source": "t",
            "kind": "tree",
            "unit": "p",
            "root": {"label": "All", "value": 5, "children": 3},
        }
    ],
}
WRONG_TYPES = [
    ("a concept node id that is a list", CRASH_1, "panels[0].nodes[0].id"),
    (
        "a concept node id that is an object",
        edited(CRASH_1, lambda s: s["panels"][0]["nodes"][0].update(id={})),
        "panels[0].nodes[0].id",
    ),
    (
        "an edge end that is a list",
        spec_of(edited(visual("concept"), lambda p: p["edges"][0].update({"from": ["a"]}))),
        "panels[0].edges[0].from",
    ),
    (
        "an edge end that is an object",
        spec_of(edited(visual("concept"), lambda p: p["edges"][0].update({"to": {"a": 1}}))),
        "panels[0].edges[0].to",
    ),
    (
        "a region set that is a list",
        spec_of(edited(visual("sets"), lambda p: p["regions"][0].update({"in": [["P"]]}))),
        "panels[0].regions[0].in",
    ),
    (
        "a region set that is an object",
        spec_of(edited(visual("sets"), lambda p: p["regions"][0].update({"in": [{}]}))),
        "panels[0].regions[0].in",
    ),
    ("tree children that is a number", CRASH_2, "panels[0].root.children"),
    (
        "tree children that is a boolean",
        edited(CRASH_2, lambda s: s["panels"][0]["root"].update(children=True)),
        "panels[0].root.children",
    ),
    (
        "a lane actor that is a list",
        spec_of(edited(visual("lanes"), lambda p: p["steps"][0].update({"actor": ["A"]}))),
        "panels[0].steps[0].actor",
    ),
    (
        "overview labels that are not lists",
        spec_of(
            edited(visual("groups"), lambda p: p.update({"overview": True, "groups": [{"label": "G", "items": 3}]})),
            edited(visual("text"), put("focus", ["G"])),
        ),
        "panels[0].groups[0].items",
    ),
    (
        "a focus that is an object",
        spec_of(overview_panel(), edited(visual("text"), put("focus", {"a": 1}))),
        "panels[1].focus",
    ),
    (
        "table rows that are not lists",
        spec_of(edited(visual("table"), lambda p: p.update({"rows": [{"a": 1}, 3]}))),
        "panels[0].rows[0]",
    ),
]


class WrongTypes(unittest.TestCase):
    def test_no_hook_or_check_raises_on_a_wrongly_typed_value_and_the_schema_names_the_field(self):
        for name, spec, field in WRONG_TYPES:
            with self.subTest(name):
                fields = [f for f, _ in shape_problems(spec)]
                self.assertTrue(any(f.startswith(field) for f in fields), (field, fields))
                errors, _, _ = show.check(spec)
                self.assertTrue(any(field in e for e in errors), (field, errors))

    def test_schema_py_check_on_the_file_does_not_raise_either(self):
        for name, spec, field in WRONG_TYPES:
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                path = Path(d) / "spec.json"
                path.write_text(json.dumps(spec))
                errors = schema.check_paths([path], SCHEMAS)
                self.assertTrue(any(e.field.startswith(field) for e in errors), (field, errors))

    def test_every_leaf_of_every_valid_spec_set_to_a_wrong_value_gives_an_answer_and_no_exception(self):
        values = [None, "x", "", -1, 2.5, [], {}, True, ["x"], [{}]]

        def leaves(o, path=()):
            yield path
            if isinstance(o, dict):
                for k, v in o.items():
                    yield from leaves(v, (*path, k))
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    yield from leaves(v, (*path, i))

        bases = [spec_of(visual(k)) for k in KIND_OK] + [spec_of(copy.deepcopy(p)) for p in OTHER_PANELS.values()]
        for base in bases:
            for path in leaves(base):
                if not path:
                    continue
                for value in [*values, "<delete>"]:
                    spec = copy.deepcopy(base)
                    target = spec
                    for step in path[:-1]:
                        target = target[step]
                    if value == "<delete>":
                        target.pop(path[-1])
                    else:
                        target[path[-1]] = copy.deepcopy(value)
                    try:
                        show.check(spec)
                        shape_problems(spec)
                    except Exception as error:
                        self.fail(f"{path} = {value!r} in a {base['panels'][0].get('kind')} panel raised {error!r}")


# Optional fields: (kind of panel, path to the field in the panel, or "top" and a path in the spec).
NULLABLE = [
    ("top", ["question"]),
    ("top", ["summary"]),
    ("top", ["source"]),
    ("top", ["lang"]),
    ("top", ["document"]),
    ("top", ["style"]),
    ("top", ["at"]),
    ("top", ["by"]),
    ("text", ["part"]),
    ("text", ["source"]),
    ("text", ["overview"]),
    ("text", ["focus"]),
    ("text", ["template"]),
    ("map", ["highlight"]),
    ("map", ["sections", 0, "gist"]),
    ("map", ["sections", 0, "id"]),
    ("flow", ["steps", 0, "note"]),
    ("groups", ["groups", 0, "items"]),
    ("tree", ["unit"]),
    ("tree", ["root", "value"]),
    ("sets", ["regions", 0, "label"]),
    ("sets", ["regions", 0, "count"]),
    ("matrix", ["rows", 0, "group"]),
    ("matrix", ["rows", 1, "cells", 0, "mark"]),
    ("effects", ["rows", 0, "outcome"]),
    ("effects", ["rows", 0, "group"]),
    ("pairs", ["rows", 0, "left"]),
    ("pairs", ["rows", 0, "right", 0, "effect"]),
    ("units", ["unit"]),
    ("bars", ["unit"]),
    ("bars", ["max"]),
    ("bars", ["items", 0, "detail"]),
    ("slope", ["unit"]),
    ("slope", ["y_from_zero"]),
    ("slope", ["y_note"]),
    ("dots", ["unit"]),
    ("scatter", ["points", 1, "label"]),
    ("line", ["unit"]),
    ("line", ["x_label"]),
    ("line", ["y_from_zero"]),
    ("table", ["highlight_rows"]),
    ("fork", ["branches", 0, "note"]),
    ("statement", ["compare"]),
    ("title", ["body"]),
    ("title", ["actions"]),
    ("compare", ["a", "detail"]),
    ("lanes", ["steps", 0, "highlight"]),
]
# Required fields stay non-null: (kind of panel, path).
NOT_NULLABLE = [
    ("top", ["title"]),
    ("top", ["panels"]),
    ("top", ["type"]),
    ("text", ["headline"]),
    ("text", ["kind"]),
    ("text", ["body"]),
    ("bars", ["items"]),
    ("bars", ["items", 0, "value"]),
    ("concept", ["edges", 0, "label"]),
    ("flow", ["arrow"]),
    ("flow", ["steps", 0, "label"]),
    ("statement", ["figure"]),
    ("statement", ["sentence"]),
    ("slope", ["from"]),
    ("fork", ["branches", 0, "outcome"]),
    ("svg", ["alt"]),
    ("groups", ["groups", 0, "label"]),
    ("quadrant", ["items", 0, "label"]),
    ("bars", ["items", 0, "label"]),
    ("slope", ["items", 0, "label"]),
    ("dots", ["groups", 0, "label"]),
    ("line", ["series", 0, "name"]),
]


def with_value(where, path, value):
    """The spec of that panel kind with the field set to value, or removed when value is the string <absent>."""
    if where == "top":
        spec = spec_of(visual("text"))
        spec["at"] = AT
        spec["by"] = "agent"
        spec["document"] = {"title": "D", "address": "https://example.com/d"}
        spec["style"] = {"point": "#FF0000"}
        holder = spec
    else:
        panel = copy.deepcopy(OTHER_PANELS[where]) if where in OTHER_PANELS else visual(where)
        if where == "map":
            panel["sections"].append({"id": "s2", "label": "More"})
        if where == "text":
            panel["overview"] = False
        spec = spec_of(panel)
        holder = panel
    for step in path[:-1]:
        holder = holder[step]
    if value == "<absent>":
        holder.pop(path[-1], None)
    else:
        holder[path[-1]] = value
    return spec


class Nulls(unittest.TestCase):
    def test_an_optional_field_set_to_null_is_accepted_and_means_the_same_as_leaving_it_out(self):
        for where, path in NULLABLE:
            with self.subTest(f"{where} {path}"):
                nulled = with_value(where, path, None)
                self.assertEqual(shape_problems(nulled), [], "the schema")
                absent = with_value(where, path, "<absent>")
                self.assertEqual(show.check(nulled), show.check(absent))
                self.assertEqual(show.check(nulled)[0], [])

    def test_a_null_means_the_same_to_the_page_and_to_the_text(self):
        for where, path in NULLABLE:
            with self.subTest(f"{where} {path}"):
                a, b = with_value(where, path, None), with_value(where, path, "<absent>")
                self.assertEqual(show.render(show.without_nulls(a)), show.render(show.without_nulls(b)))
                self.assertEqual(show.render_text(show.without_nulls(a)), show.render_text(show.without_nulls(b)))

    def test_a_required_field_set_to_null_is_refused(self):
        for where, path in NOT_NULLABLE:
            with self.subTest(f"{where} {path}"):
                spec = with_value(where, path, None)
                self.assertTrue(shape_problems(spec), "the schema accepted it")
                self.assertTrue(show.check(spec)[0], "show.py accepted it")

    def test_a_null_in_a_list_is_kept(self):
        spec = spec_of(visual("matrix"))
        self.assertEqual(spec["panels"][0]["rows"][0]["cells"][0], None)
        self.assertEqual(show.without_nulls(spec)["panels"][0]["rows"][0]["cells"], [None, "up"])

    def test_a_pair_row_with_a_null_side_and_an_empty_one_has_nothing_in_it(self):
        spec = spec_of(edited(visual("pairs"), lambda p: p["rows"][0].update({"left": None, "right": []})))
        self.assertIn("panels[0].rows[0]", [f for f, _ in shape_problems(spec)])

    def test_a_region_with_an_empty_label_and_a_null_count_is_refused(self):
        spec = spec_of(edited(visual("sets"), lambda p: p["regions"][0].update({"label": "", "count": None})))
        self.assertIn("panels[0].regions[0]", [f for f, _ in shape_problems(spec)])


class TypeHint(unittest.TestCase):
    def test_a_spec_without_type_is_told_to_add_it(self):
        spec = spec_of(visual("text"))
        del spec["type"]
        errors, _, _ = show.check(spec)
        self.assertEqual(errors, ['type: add "type": "slides" at the top of the spec'])

    def test_a_wrong_type_value_keeps_the_schemas_message(self):
        spec = {**spec_of(visual("text")), "type": "deck"}
        self.assertEqual(show.check(spec)[0], ['type: must be "slides"'])


class DesignBetterFixtures(unittest.TestCase):
    """The planted conversations of the design-better eval cases are typed events canvas.py reads."""

    CASES = ("acceptance-walk", "design-before-build", "direction-review-before-build", "handback-three-things")

    def folder(self, case):
        return ROOT / "evals" / "cases" / "design-better" / case / "repo" / ".design" / "shift-swap"

    def test_each_file_passes_the_schemas_and_pending_lists_the_planted_items(self):
        for case in self.CASES:
            with self.subTest(case):
                log = self.folder(case) / "conversation.jsonl"
                self.assertEqual(schema.check_paths([log], CANVAS / "schemas"), [])
                with tempfile.TemporaryDirectory() as d:
                    copy_to = Path(d) / "shift-swap"
                    copy_to.mkdir()
                    (copy_to / "conversation.jsonl").write_text(log.read_text())
                    script = str(CANVAS / "scripts" / "canvas.py")
                    done = subprocess.run(
                        [sys.executable, "-I", script, "pending", str(copy_to)], capture_output=True, text=True
                    )
                self.assertIn("3 not done", done.stdout)
                self.assertIn('"id": "d-1k9"', done.stdout)


if __name__ == "__main__":
    unittest.main()
