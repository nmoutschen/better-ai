"""Tests for the architecture diagram renderer."""

import copy
import importlib.util
import json
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "architect-better" / "scripts"
SPEC = importlib.util.spec_from_file_location("diagram", SCRIPTS / "diagram.py")
diagram = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagram)

NS = {"svg": "http://www.w3.org/2000/svg"}


def content(svg, element_id):
    group = ET.fromstring(svg).find(f".//*[@id='{element_id}']")
    return [] if group is None else [text.text for text in group.findall("svg:text", NS)]


class DiagramTests(unittest.TestCase):
    def setUp(self):
        self.design = json.loads((SCRIPTS / "example.json").read_text(encoding="utf-8"))

    def test_check_refuses_unknown_kind(self):
        result = subprocess.run(
            [sys.executable, SCRIPTS / "diagram.py", "check", "/dev/stdin"],
            input=json.dumps(
                {"containers": {"nodes": [{"id": "x", "label": "X", "kind": "unknown-widget"}]}, "flows": []}
            ),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("unknown-widget", result.stderr)

    def test_check_reports_references_and_duplicate_ids(self):
        self.design["containers"]["edges"][0]["to"] = "missing-node"
        flow = self.design["flows"][0]
        flow["participants"][0]["box"] = "missing-box"
        flow["steps"][0]["from"] = "missing-participant"
        flow["steps"].append(copy.deepcopy(flow["steps"][0]))
        with self.assertRaises(ValueError) as error:
            diagram.layout(self.design)
        for message in ("missing-node", "missing-box", "missing-participant", "Duplicate id"):
            self.assertIn(message, str(error.exception))

    def test_ids_and_marker_references_across_views(self):
        self.design["flows"].append(copy.deepcopy(self.design["flows"][0]))
        layout = diagram.layout(self.design)
        ids = []
        for state in ("before", "after"):
            views = [diagram.svg_containers(layout, state)]
            views.extend(
                diagram.svg_flow(flow, state, layout, f"flow{i}") for i, flow in enumerate(self.design["flows"], 1)
            )
            for svg in views:
                root = ET.fromstring(svg)
                local = [element.attrib["id"] for element in root.iter() if "id" in element.attrib]
                ids.extend(local)
                for element in root.iter():
                    if marker := element.get("marker-end"):
                        self.assertIn(marker.removeprefix("url(#").removesuffix(")"), local)
        self.assertEqual(len(ids), len(set(ids)))

    def test_steps_keep_numbers_and_new_flow_counts_from_one(self):
        layout = diagram.layout(self.design)
        flow, new_flow = self.design["flows"]
        before = diagram.svg_flow(flow, "before", layout, "flow1")
        after = diagram.svg_flow(flow, "after", layout, "flow1")
        self.assertEqual(ET.fromstring(before).get("viewBox"), ET.fromstring(after).get("viewBox"))
        for state, svg in (("before", before), ("after", after)):
            self.assertIn("1", content(svg, f"flow1-{state}-step-s1"))
            self.assertIn("2", content(svg, f"flow1-{state}-step-s3"))
        self.assertIn("1a", content(after, "flow1-after-step-s2"))
        svg = diagram.svg_flow(new_flow, "after", layout, "flow2")
        for i in range(1, 6):
            self.assertIn(str(i), content(svg, f"flow2-after-step-f2s{i}"))

    def test_removed_parts_only_show_in_after(self):
        layout = diagram.layout(self.design)
        for render, prefix, ids in (
            (lambda state: diagram.svg_containers(layout, state), "c", ("box-notes", "edge-e13")),
            (lambda state: diagram.svg_flow(self.design["flows"][0], state, layout, "flow1"), "flow1", ("step-s8",)),
        ):
            for part in ids:
                self.assertEqual(content(render("before"), f"{prefix}-before-{part}"), [])
                self.assertIn("REMOVED", content(render("after"), f"{prefix}-after-{part}"))

    def test_group_bands_exclude_non_members(self):
        root = ET.fromstring(diagram.svg_containers(diagram.layout(self.design), "after"))

        def bounds(part):
            rect = root.find(f".//*[@id='c-after-{part}']/svg:rect", NS)
            x, y, w, h = (float(rect.attrib[k]) for k in ("x", "y", "width", "height"))
            return x, y, x + w, y + h

        for group in self.design["containers"]["groups"]:
            left, top, right, bottom = bounds(f"group-{group['id']}")
            for node in self.design["containers"]["nodes"]:
                x1, y1, x2, y2 = bounds(f"box-{node['id']}")
                intersects = x1 < right and x2 > left and y1 < bottom and y2 > top
                self.assertEqual(intersects, node["id"] in group["members"])

    def test_return_edge_label_has_room_inside_viewbox(self):
        design = {
            "containers": {
                "nodes": [{"id": name, "kind": "service", "label": name} for name in ("a", "b")],
                "edges": [
                    {"id": "send", "from": "a", "to": "b"},
                    {"id": "reply", "from": "b", "to": "a", "label": "Returns the result", "in": ["before"]},
                ],
            }
        }
        root = ET.fromstring(diagram.svg_containers(diagram.layout(design), "after"))
        left = float(root.get("viewBox").split()[0])
        labels = root.findall(".//*[@id='c-after-edge-reply']/svg:text", NS)
        self.assertEqual([label.text for label in labels], ["Returns the result", "REMOVED"])
        for label in labels:
            self.assertGreater(float(label.get("x")) - left, diagram.width(label.text, diagram.LABEL))

    def test_participant_uses_the_containers_box_style(self):
        flow = self.design["flows"][0]
        flow["participants"][0]["in"] = ["after"]
        positions = diagram.layout(self.design)
        before = diagram.svg_flow(flow, "before", positions, "flow1")
        after = diagram.svg_flow(flow, "after", positions, "flow1")
        self.assertEqual(content(before, "flow1-before-box-user"), [])
        self.assertEqual(
            content(after, "flow1-after-box-user"),
            content(diagram.svg_containers(positions, "after"), "c-after-box-user"),
        )

    def test_step_findings_can_target_one_of_two_flows_with_the_same_step_id(self):
        first = self.design["flows"][0]
        second = copy.deepcopy(first)
        self.design["flows"].append(second)
        self.design["findings"] = {
            "flow1:step:s6": [("S1", "Check the first flow", "security")],
        }
        positions = diagram.layout(self.design)
        for flow, view, expected in ((first, "flow1", ["security"]), (second, "flow3", [])):
            root = ET.fromstring(diagram.svg_flow(flow, "after", positions, view))
            self.assertEqual([mark.get("data-p") for mark in root.findall(".//svg:g[@class='mark']", NS)], expected)

    def test_check_names_unknown_finding_targets(self):
        targets = ("missing-box", "edge:missing-edge", "step:missing-step", "flow1:step:missing-step")
        self.design["findings"] = dict.fromkeys(targets, [])
        errors = diagram.validate(self.design)
        for target in targets:
            with self.subTest(target=target):
                self.assertIn(f"Finding target {target!r}: missing or ambiguous diagram part", errors)

    def test_check_names_string_participant(self):
        self.design["flows"][0]["participants"].append("missing-participant")
        errors = diagram.validate(self.design)
        self.assertTrue(
            any(e.startswith("flows[0].participants[") and "expected object, got string" in e for e in errors), errors
        )

    def test_findings_are_hidden_and_follow_parts_across_views(self):
        self.design["findings"] = {
            "page": [("S1", "Browser trust boundary", "security")],
            "edge:e3": [("O1", "Track failed posts", "observability")],
            "step:s6": [("O1", "Track failed posts", "observability")],
        }
        layout = diagram.layout(self.design)
        for svg in (
            diagram.svg_containers(layout, "after"),
            diagram.svg_flow(self.design["flows"][0], "after", layout, "flow1"),
        ):
            marks = ET.fromstring(svg).findall(".//svg:g[@class='mark']", NS)
            self.assertEqual([mark.get("data-p") for mark in marks], ["security", "observability"])
            self.assertTrue(all(mark.get("hidden") == "hidden" for mark in marks))
            self.assertIn(".mark[hidden] { display: none; }", svg)


if __name__ == "__main__":
    unittest.main()
