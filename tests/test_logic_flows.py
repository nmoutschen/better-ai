"""Tests for logic flows (decisions, loops back, exits, states) and the groupings of the Containers view (trust, where
things run), issue #123."""

import copy
import json
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from itertools import pairwise
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from better_ai.architect import diagram, model  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "src" / "better_ai" / "architect"
FIXTURE = ROOT / "tests" / "fixtures" / "architect-logic" / "design.json"
NS = {"svg": "http://www.w3.org/2000/svg"}


def example():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def logic(design, ident="review"):
    return next(flow for flow in design["flows"] if flow["id"] == ident)


def errors(design):
    return "\n".join(diagram.validate(design))


def rect_of(root, element_id):
    rect = root.find(f".//*[@id='{element_id}']/svg:rect", NS)
    return tuple(float(rect.attrib[k]) for k in ("x", "y", "width", "height"))


def texts(root, element_id):
    element = root.find(f".//*[@id='{element_id}']", NS)
    return [] if element is None else [node.text for node in element.iter() if node.text and node.text.strip()]


def segments(points):
    return [(a, b) for a, b in pairwise(points) if a != b]


def cross(s, t):
    """Whether two axis-parallel segments meet at a point inside both (touching at shared endpoints aside)."""
    (a, b), (c, d) = s, t
    if a[0] == b[0] and c[1] == d[1]:  # s vertical, t horizontal
        x, y = a[0], c[1]
        return min(c[0], d[0]) < x < max(c[0], d[0]) and min(a[1], b[1]) < y < max(a[1], b[1])
    if a[1] == b[1] and c[0] == d[0]:
        return cross(t, s)
    if a[0] == b[0] == c[0] == d[0]:  # both vertical on one line: overlapping runs read as one edge
        return min(a[1], b[1]) < max(c[1], d[1]) and min(c[1], d[1]) < max(a[1], b[1])
    if a[1] == b[1] == c[1] == d[1]:
        return min(a[0], b[0]) < max(c[0], d[0]) and min(c[0], d[0]) < max(a[0], b[0])
    return False


def through(segment, box):
    """Whether a segment runs through the inside of a box."""
    (a, b), (x, y, w, h) = segment, box
    if a[0] == b[0]:
        return x + 1 < a[0] < x + w - 1 and min(a[1], b[1]) < y + h - 1 and max(a[1], b[1]) > y + 1
    return y + 1 < a[1] < y + h - 1 and min(a[0], b[0]) < x + w - 1 and max(a[0], b[0]) > x + 1


def overlap(r, s):
    return r[0] < s[0] + s[2] and s[0] < r[0] + r[2] and r[1] < s[1] + s[3] and s[1] < r[1] + r[3]


def run_page_js(expression, data):
    result = subprocess.run(
        [
            "node",
            "-e",
            """
            const vm = require('node:vm');
            const fs = require('node:fs');
            const data = JSON.parse(fs.readFileSync(0, 'utf8'));
            const context = {data, fetch: () => new Promise(() => {}),
              document: {querySelector: () => ({}), getElementById: () => null}};
            vm.createContext(context);
            for (const file of [process.argv[1], process.argv[2]]) vm.runInContext(fs.readFileSync(file, 'utf8'), context);
            process.stdout.write(String(vm.runInContext(process.argv[3], context)));
            """,
            str(PACKAGE.parent / "page" / "page.js"),
            str(PACKAGE / "page.js"),
            expression,
        ],
        input=json.dumps(data),
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


class LogicFlowChecks(unittest.TestCase):
    def test_logic_flow_schema(self):
        design = example()
        self.assertEqual(diagram.validate(design), [])
        sequence = copy.deepcopy(design)
        sequence["flows"] = [f for f in sequence["flows"] if f.get("kind") != "logic"]
        self.assertEqual(diagram.validate(sequence), [])
        logic(design)["edges"][0]["back"] = True
        self.assertIn("back", errors(design))

    def test_decision_needs_two_labelled_outcomes(self):
        design = example()
        flow = logic(design)
        flow["edges"] = [e for e in flow["edges"] if e["id"] != "e-reject"]
        found = errors(design)
        self.assertIn("'ok'", found)
        self.assertIn("two", found)
        design = example()
        next(e for e in logic(design)["edges"] if e["id"] == "e-yes").pop("label")
        found = errors(design)
        self.assertIn("'ok'", found)
        self.assertIn("label", found)

    def test_logic_flow_needs_one_start(self):
        design = example()
        logic(design)["nodes"].append({"id": "start2", "type": "start"})
        logic(design)["edges"].append({"id": "e-s2", "from": "start2", "to": "draft"})
        self.assertIn("start", errors(design))
        design = example()
        flow = logic(design)
        flow["nodes"] = [n for n in flow["nodes"] if n["type"] != "start"]
        flow["edges"] = [e for e in flow["edges"] if e["from"] != "start"]
        self.assertIn("start", errors(design))

    def test_unreachable_and_dead_end_nodes(self):
        design = example()
        logic(design)["nodes"].append({"id": "orphan", "type": "step", "label": "Never reached"})
        logic(design)["edges"].append({"id": "e-orphan", "from": "orphan", "to": "done"})
        found = errors(design)
        self.assertIn("'orphan'", found)
        self.assertIn("reach", found)
        design = example()
        logic(design)["nodes"].append({"id": "stuck", "type": "step", "label": "Stuck", "in": ["after"]})
        logic(design)["edges"].append({"id": "e-stuck", "from": "draft", "to": "stuck", "label": "try", "in": ["after"]})
        found = errors(design)
        self.assertIn("'stuck'", found)
        self.assertIn("after", found)

    def test_exit_needs_label_and_outcome(self):
        design = example()
        next(n for n in logic(design)["nodes"] if n["id"] == "done").pop("outcome")
        self.assertIn("outcome", errors(design))
        design = example()
        next(n for n in logic(design)["nodes"] if n["id"] == "done").pop("label")
        self.assertIn("label", errors(design))
        design = example()
        next(n for n in logic(design)["nodes"] if n["id"] == "done")["outcome"] = "maybe"
        self.assertIn("outcome", errors(design))

    def test_logic_references(self):
        design = example()
        logic(design)["edges"][0]["to"] = "nowhere"
        self.assertIn("'nowhere'", errors(design))
        design = example()
        next(n for n in logic(design)["nodes"] if n["id"] == "draft")["by"] = "ghost"
        self.assertIn("'ghost'", errors(design))
        design = example()
        logic(design)["edges"][0]["id"] = "draft"  # the id of a node of the same flow
        self.assertIn("Duplicate id 'draft'", errors(design))


class LogicFlowDrawing(unittest.TestCase):
    def setUp(self):
        self.design = example()
        self.layout = diagram.layout(self.design)
        self.flow = logic(self.design)
        self.view = f"flow{self.design['flows'].index(self.flow) + 1}"
        self.shape = diagram.logic_layout(self.flow, self.layout)

    def svg(self, state="after"):
        return ET.fromstring(diagram.svg_flow(self.flow, state, self.layout, self.view))

    def test_logic_parts_on_page(self):
        parts, _, _ = model.diagram_parts(self.design)
        root = self.svg()
        for key in ("step:review/ok", "step:review/e-again"):
            self.assertIn(key, parts)
            drawn = [i for i in parts[key]["ids"] if root.find(f".//*[@id='{i}']") is not None]
            self.assertTrue(drawn, key)
        marked = diagram.layout({**self.design, "findings": {f"{self.view}:step:ok": [["S1", "tip", "security"]]}})
        self.assertIn("S1", diagram.svg_flow(self.flow, "after", marked, self.view))

    def test_logic_flow_runs_left_to_right(self):
        boxes = self.shape["boxes"]
        start_x = boxes["start"][0]
        self.assertEqual(start_x, min(box[0] for box in boxes.values()))
        for ident, points in self.shape["routes"].items():
            self.assertGreater(points[-1][0], points[0][0], ident)

    def test_loops_back_drawn_apart(self):
        loops = self.shape["loops"]
        self.assertEqual(set(loops), {"e-again", "e-remind"})
        self.assertIn(loops["e-again"]["kind"], ("arc", "connector"))
        self.assertEqual(loops["e-remind"]["kind"], "self")
        self.assertNotIn("e-again", self.shape["routes"])
        words = texts(self.svg(), diagram.part_id(f"{self.view}-after", "step", "e-again"))
        self.assertIn("changes asked", " ".join(words))

    def test_exits_below_with_outcome_word(self):
        boxes = self.shape["boxes"]
        types = {n["id"]: n["type"] for n in self.flow["nodes"]}
        for ident, (x, y, _, _) in boxes.items():
            if types[ident] != "exit":
                continue
            column = [boxes[o][1] for o in boxes if boxes[o][0] == x and types[o] != "exit"]
            self.assertTrue(all(y > other for other in column), ident)
        root = self.svg()
        self.assertIn("POSITIVE END", texts(root, diagram.part_id(f"{self.view}-after", "step", "done")))
        self.assertIn("NEGATIVE END", texts(root, diagram.part_id(f"{self.view}-after", "step", "drop")))

    def test_example_logic_flow_geometry(self):
        shape = self.shape
        lines = {ident: segments(points) for ident, points in shape["routes"].items()}
        for ident, loop in shape["loops"].items():
            lines[ident] = [s for points in loop["paths"] for s in segments(points)]
        idents = list(lines)
        for i, a in enumerate(idents):
            for b in idents[i + 1 :]:
                for s in lines[a]:
                    for t in lines[b]:
                        self.assertFalse(cross(s, t), (a, b, s, t))
        edges = {e["id"]: e for e in self.flow["edges"]}
        for ident, parts in lines.items():
            ends = {edges[ident]["from"], edges[ident]["to"]}
            for node, box in shape["boxes"].items():
                if node in ends:
                    continue
                for s in parts:
                    self.assertFalse(through(s, box), (ident, node, s))
        labels = list(shape["label_boxes"].items())
        for ident, rect in labels:
            for node, box in shape["boxes"].items():
                self.assertFalse(overlap(rect, box), (ident, node))
        for i, (a, r) in enumerate(labels):
            for b, s in labels[i + 1 :]:
                self.assertFalse(overlap(r, s), (a, b))

    def test_logic_before_after(self):
        before, after = self.svg("before"), self.svg("after")
        new = diagram.part_id(f"{self.view}-after", "step", "e-auto")
        self.assertIsNone(before.find(f".//*[@id='{diagram.part_id(f'{self.view}-before', 'step', 'e-auto')}']"))
        group = after.find(f".//*[@id='{new}']")
        self.assertIsNotNone(group)
        self.assertIn(diagram.TERRA, ET.tostring(group, encoding="unicode"))
        draft_before = rect_of(before, diagram.part_id(f"{self.view}-before", "step", "draft"))
        draft_after = rect_of(after, diagram.part_id(f"{self.view}-after", "step", "draft"))
        self.assertEqual(draft_before, draft_after)

    def test_step_shows_actor(self):
        words = texts(self.svg(), diagram.part_id(f"{self.view}-after", "step", "draft"))
        self.assertIn("Design agent", " ".join(words))


class Groupings(unittest.TestCase):
    def test_group_kinds_schema(self):
        self.assertEqual(diagram.validate(example()), [])

    def test_group_kind_rules(self):
        design = example()
        groups = design["containers"]["groups"]
        next(g for g in groups if g["id"] == "vendor")["members"].append("api")  # api is also in trust group local
        self.assertIn("'api'", errors(design))
        design = example()
        next(g for g in design["containers"]["groups"] if g["id"] == "tab")["within"] = "local"  # a trust group
        self.assertIn("within", errors(design))
        design = example()
        next(g for g in design["containers"]["groups"] if g["id"] == "tab")["within"] = "missing"
        self.assertIn("within", errors(design))
        design = example()
        next(g for g in design["containers"]["groups"] if g["id"] == "laptop")["within"] = "tab"
        self.assertIn("cycle", errors(design))
        self.assertEqual(diagram.validate(example()), [])  # api is in a boundary, a trust and a runs group at once

    def test_overlay_drawings(self):
        design = example()
        files = diagram.drawings(design)
        layout = diagram.layout(design)
        for overlay in ("trust", "runs"):
            self.assertIn(f"containers-{overlay}-after.svg", files)
            root = ET.fromstring(files[f"containers-{overlay}-after.svg"])
            prefix = f"c{overlay}-after"
            kinds = {g["id"]: g.get("kind", "boundary") for g in design["containers"]["groups"]}
            members = {g["id"]: set(g["members"]) for g in design["containers"]["groups"]}
            for group, kind in kinds.items():
                drawn = root.find(f".//*[@id='{prefix}-group-{group}']") is not None
                self.assertEqual(drawn, kind == overlay, group)
            within = {g["id"]: g.get("within") for g in design["containers"]["groups"]}
            for group, kind in kinds.items():
                if kind != overlay:
                    continue
                inside = set(members[group])
                for child, parent in within.items():
                    if parent == group:
                        inside |= members[child]
                gx, gy, gw, gh = rect_of(root, f"{prefix}-group-{group}")
                for node in design["containers"]["nodes"]:
                    x, y, w, h = rect_of(root, f"{prefix}-box-{node['id']}")
                    hit = x < gx + gw and x + w > gx and y < gy + gh and y + h > gy
                    self.assertEqual(hit, node["id"] in inside, (overlay, group, node["id"]))
            self.assertEqual(layout["overlays"][overlay]["x"], layout["x"])

    def test_nested_runs_outlines(self):
        root = ET.fromstring(diagram.drawings(example())["containers-runs-after.svg"])
        ox, oy, ow, oh = rect_of(root, "cruns-after-group-laptop")
        ix, iy, iw, ih = rect_of(root, "cruns-after-group-tab")
        self.assertTrue(ox < ix and oy < iy and ix + iw < ox + ow and iy + ih < oy + oh)

    def test_trust_crossing_marks(self):
        design = example()
        root = ET.fromstring(diagram.drawings(design)["containers-trust-after.svg"])
        zone = {}
        for group in design["containers"]["groups"]:
            if group.get("kind") == "trust":
                zone.update(dict.fromkeys(group["members"], group["id"]))
        for edge in design["containers"]["edges"]:
            group = root.find(f".//*[@id='ctrust-after-edge-{edge['id']}']", NS)
            marked = group.find(".//*[@class='crossing']", NS) is not None
            self.assertEqual(marked, zone.get(edge["from"]) != zone.get(edge["to"]), edge["id"])
        self.assertIn("Crosses a trust boundary", ET.tostring(root, encoding="unicode"))
        plain = ET.tostring(ET.fromstring(diagram.drawings(design)["containers-after.svg"]), encoding="unicode")
        self.assertNotIn("crossing", plain)

    def test_overlay_switch(self):
        overlays = [{"id": "trust", "name": "Trust"}, {"id": "runs", "name": "Where it runs"}]
        html = run_page_js("controls([], false, [], data)", overlays)
        self.assertEqual(
            [b.split('"')[0] for b in html.split('data-overlay="')[1:]], ["systems", "trust", "runs"]
        )
        for word in ("Systems", "Trust", "Where it runs"):
            self.assertIn(">" + word + "<", html)
        self.assertNotIn("data-overlay", run_page_js("controls([], false, [], data)", []))
        data = model.render_diagrams(example(), {})
        self.assertEqual([o["id"] for o in data[2]], ["trust", "runs"])
        self.assertEqual([o["name"] for o in data[2]], ["Trust", "Where it runs"])
        plain = example()
        plain["containers"]["groups"] = [g for g in plain["containers"]["groups"] if g.get("kind", "boundary") == "boundary"]
        self.assertEqual(model.render_diagrams(plain, {})[2], [])


class UserOnTheLeft(unittest.TestCase):
    def test_person_boxes_first_column(self):
        design = example()
        self.assertEqual(design["containers"]["edges"][0]["to"], "user")  # an arrow to the user is listed first
        layout = diagram.layout(design)
        self.assertEqual(layout["x"]["user"], min(layout["x"][n["id"]] for n in design["containers"]["nodes"]))
        self.assertEqual(layout["x"]["user"], 0)

    def test_person_participants_first(self):
        design = example()
        flow = next(f for f in design["flows"] if f.get("kind") != "logic")
        self.assertNotEqual(flow["participants"][0]["box"], "user")
        root = ET.fromstring(diagram.svg_flow(flow, "after", diagram.layout(design), "flow1"))
        boxes = {p["box"]: rect_of(root, f"flow1-after-box-{p['id']}")[0] for p in flow["participants"]}
        self.assertEqual(boxes["user"], min(boxes.values()))
        order = [p["box"] for p in flow["participants"] if p["box"] != "user"]
        self.assertEqual(sorted(order, key=boxes.get), order)


if __name__ == "__main__":
    unittest.main()
