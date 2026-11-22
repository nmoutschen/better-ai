"""architect-better's files as typed JSON: the schemas of every file kind on the spec page, and architect.py that reads them.

The examples of the spec page (tests/fixtures/architect-better-examples.json) are the fixtures: each must validate. A
folder built from them must check clean, one bad record per kind must be reported with file:line and field and stay on
the page marked, `architect.py check` must exit 1 on a bad folder and 0 on a good one, and the specs.md written from
spec.jsonl must say it is generated and match the records.
"""

import copy
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "architect-better"
SCRIPTS = SKILL / "scripts"
SCHEMAS = SKILL / "schemas"
EXAMPLES = json.loads((Path(__file__).parent / "fixtures" / "architect-better-examples.json").read_text())
AT = "2026-11-21T10:00:00Z"
DIGEST = "3a7f" * 16  # the spec page shows a digest as 3a7f…, cut short; the schema wants all 64 hex digits


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


schema = load("schema", SCRIPTS / "schema.py")
diagram = load("architect_formats_diagram", SCRIPTS / "diagram.py")
architect = load("architect_formats_architect", SCRIPTS / "architect.py")

# The spec page's file kinds, and the schema each is checked against.
KINDS = {
    "architect.json": "architect.schema.json",
    "design.json": "design.schema.json",
    "requirements.jsonl": "requirements.schema.json",
    "perspectives.jsonl": "perspectives.schema.json",
    "findings.jsonl": "findings.schema.json",
    "decisions.jsonl": "decisions.schema.json",
    "reviews.jsonl": "reviews.schema.json",
    "spec.jsonl": "spec.schema.json",
}
JSON_FILES = ("architect.json", "design.json")


def examples(kind):
    out = []
    for e in EXAMPLES[kind]:
        record = json.loads(e["line"])
        if kind == "reviews.jsonl":
            record["hashes"] = {key: DIGEST for key in record["hashes"]}
        out.append((e["title"], record))
    return out


def write(folder: Path, name: str, records):
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if name in JSON_FILES:
        path.write_text(json.dumps(records[0], indent=1) + "\n", encoding="utf-8")
    else:
        path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


def read(folder: Path, name: str):
    text = (folder / name).read_text(encoding="utf-8")
    return json.loads(text) if name in JSON_FILES else [json.loads(line) for line in text.splitlines()]


def base(type_, **more):
    return {"type": type_, "at": AT, "by": "architect", **more}


def design():
    node = lambda ident, label, kind: {"id": ident, "label": label, "kind": kind}  # noqa: E731
    return base(
        "design",
        containers={
            "nodes": [node("user", "You", "person"), node("page", "Page", "page"), node("server", "Server", "service")],
            "edges": [
                {"id": "e1", "from": "user", "to": "page", "label": "reads"},
                {"id": "e3", "from": "page", "to": "server", "label": "POST /rpc"},
                {"id": "e4", "from": "server", "to": "page", "label": "answer"},
            ],
            "groups": [],
        },
        flows=[
            {
                "id": "ask",
                "name": "A builder asks",
                "participants": [{"id": "page", "box": "page"}, {"id": "server", "box": "server"}],
                "steps": [
                    {"id": "s6", "from": "page", "to": "server", "label": "POST"},
                    {"id": "s7", "from": "server", "to": "page", "label": "answer", "kind": "response"},
                ],
            }
        ],
    )


def folder_records():
    """A consistent folder: every pointer resolves, built from the spec page's examples."""
    request = "Add a dashboard that shows each agent's task, mode and state.\nShow each agent's task, mode and state."
    requirements = [r for _, r in examples("requirements.jsonl")]
    for ident, kind in (("F3", "functional"), ("Q1", "quality"), ("C1", "constraint")):
        requirements.append(base("requirement", id=ident, kind=kind, text=f"{ident} text.", source={"type": "guessed"}))
    review = examples("reviews.jsonl")[0][1]
    review["hashes"] = {"box:user": DIGEST, "edge:e1": DIGEST}
    review["labels"] = {"box:user": "You", "edge:e1": "You to Page: reads"}
    return {
        "architect.json": [
            {**examples("architect.json")[0][1], "request": {"text": request, "from": {"type": "chat"}}}
        ],
        "design.json": [design()],
        "requirements.jsonl": requirements,
        "perspectives.jsonl": [r for _, r in examples("perspectives.jsonl")],
        "findings.jsonl": [r for _, r in examples("findings.jsonl")],
        "decisions.jsonl": [r for _, r in examples("decisions.jsonl")],
        "reviews.jsonl": [review],
        "spec.jsonl": [r for _, r in examples("spec.jsonl")],
    }


def make_folder(root: Path, **changes):
    """A change folder in a repo (a .git next to it); `changes` replaces a file's records, or None leaves it out."""
    (root / ".git").mkdir(exist_ok=True)
    folder = root / "docs" / "designs" / "c"
    files = folder_records()
    files.update(changes)
    for name, records in files.items():
        if records is not None:
            write(folder, name, records)
    return folder


def check(folder: Path):
    return schema.check_paths([folder], SCHEMAS)


def run_check(folder: Path):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = architect.main(["check", str(folder)])
    return code, out.getvalue(), err.getvalue()


class Examples(unittest.TestCase):
    """Every example of the spec page validates against the schema of its file kind."""

    def test_every_example_has_a_schema_that_accepts_it(self):
        for kind, name in KINDS.items():
            for title, record in examples(kind):
                with self.subTest(kind=kind, example=title):
                    self.assertEqual(schema.check_record(record, [name], SCHEMAS), [])

    def test_a_folder_built_from_the_examples_checks_clean(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            self.assertEqual([str(e) for e in check(folder)], [])
            self.assertEqual(run_check(folder)[0], 0)

    def test_the_example_folder_checks_clean(self):
        """The planted eval folders are checked in MovedChecks, as repositories of their own."""
        folder = SCRIPTS / "example"
        self.assertEqual([str(e) for e in schema.check_paths([folder], SCHEMAS)], [])
        self.assertEqual(run_check(folder)[0], 0)
        self.assertFalse((folder / "request.md").exists())


class OneBadRecordPerKind(unittest.TestCase):
    """A bad record is reported with its file, its line and the field, the good ones around it are not, and the page
    still shows the bad one, marked."""

    BAD = {
        "architect.json": (lambda r: {k: v for k, v in r.items() if k != "title"}, "title"),
        "design.json": (lambda r: {**r, "flows": [{k: v for k, v in r["flows"][0].items() if k != "id"}]}, "flows"),
        "requirements.jsonl": (lambda r: {**r, "kind": "weird"}, "kind"),
        "perspectives.jsonl": (lambda r: {**r, "from": {"type": "built in"}}, "from"),
        "findings.jsonl": (lambda r: {k: v for k, v in r.items() if k != "handled_by"}, "handled_by"),
        "decisions.jsonl": (lambda r: {**r, "drivers": ["Z9"]}, "drivers"),
        "reviews.jsonl": (lambda r: {**r, "at": "2026-11-20T19:42:54"}, "at"),
        "spec.jsonl": (lambda r: {k: v for k, v in r.items() if k != "statement"}, "statement"),
    }
    SHOWN = {
        "requirements.jsonl": "requirements",
        "perspectives.jsonl": "perspectives",
        "findings.jsonl": "findings",
        "decisions.jsonl": "decisions",
        "reviews.jsonl": "reviews",
        "spec.jsonl": "spec",
    }

    def test_each_kind(self):
        for name, (mutate, field) in self.BAD.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                folder = make_folder(Path(d))
                records = read(folder, name)
                if name in JSON_FILES:
                    records = [mutate(records)]
                else:
                    if len(records) < 2:  # one good record above the bad one
                        records.append({**records[0], **({"id": "X9"} if "id" in records[0] else {})})
                        if name == "decisions.jsonl":
                            records[1]["id"] = "D2"
                        if name == "spec.jsonl":
                            records[1]["id"] = "S2"
                    records[1] = mutate(records[1])
                write(folder, name, records)
                errors = [e for e in check(folder) if e.field.split(".")[0].split("[")[0] == field]
                self.assertTrue(errors, f"{name}: no error on {field}")
                self.assertEqual(errors[0].line, 1 if name in JSON_FILES else 2)
                self.assertTrue(str(errors[0].file).endswith(name))
                data = architect.load(folder)
                json.dumps(data)
                listed = [
                    e for e in data["errors"] if e["file"] == name and e["field"].split(".")[0].split("[")[0] == field
                ]
                self.assertTrue(listed, f"{name}: the page's errors band lacks it")
                self.assertEqual(listed[0]["line"], errors[0].line)
                if name in self.SHOWN:
                    shown = data[self.SHOWN[name]]
                    self.assertTrue(
                        [r for r in shown if r.get("_errors")], f"{name}: the bad record is not on the page"
                    )
                    self.assertEqual(len(shown), len(records))

    def test_the_good_records_next_to_a_bad_one_are_not_reported(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            records = read(folder, "requirements.jsonl")
            records[1]["kind"] = "weird"
            write(folder, "requirements.jsonl", records)
            self.assertEqual({e.line for e in check(folder)}, {2})
            data = architect.load(folder)
            self.assertEqual({e["line"] for e in data["errors"]}, {2})
            self.assertEqual(len(data["requirements"]), len(records))


class CheckCommand(unittest.TestCase):
    def test_exit_codes_and_the_errors_it_prints(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            code, out, _ = run_check(folder)
            self.assertEqual(code, 0)
            self.assertIn("Valid change folder", out)
            records = read(folder, "findings.jsonl")
            records[0]["parts"] = ["box:nowhere"]
            write(folder, "findings.jsonl", records)
            code, out, _ = run_check(folder)
            self.assertEqual(code, 1)
            self.assertIn("findings.jsonl:1: parts[0]", out)
            self.assertEqual(out.strip().splitlines(), [str(e).replace(f"{folder}/", "") for e in check(folder)])

    def test_check_prints_the_errors_the_page_shows(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            requirements = read(folder, "requirements.jsonl")
            requirements[0]["source"] = {"type": "request", "sentence": "Not in the request."}
            write(folder, "requirements.jsonl", requirements)
            write(folder, "decisions.jsonl", [{**read(folder, "decisions.jsonl")[0], "title": 5}])
            code, out, _ = run_check(folder)
            shown = {f"{e['file']}:{e['line']}: {e['field']}: {e['message']}" for e in architect.load(folder)["errors"]}
            self.assertEqual(code, 1)
            self.assertEqual(set(out.strip().splitlines()), shown)
            self.assertEqual(len(shown), 2)

    def test_a_missing_design_json_is_an_error_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d), **{"design.json": None})
            code, out, _ = run_check(folder)
            self.assertEqual(code, 1)
            self.assertIn("design.json:1:", out)
            data = architect.load(folder)
            self.assertTrue(data["errors"])
            json.dumps(data)


class Pointers(unittest.TestCase):
    def test_a_finding_part_key_naming_no_part_is_reported(self):
        for part in ("step:ask/missing", "step:flow1/s6", "edge:nope", "box:a+box:user", "step:ask", "page:user"):
            with self.subTest(part), tempfile.TemporaryDirectory() as d:
                folder = make_folder(Path(d))
                records = read(folder, "findings.jsonl")
                records[0]["parts"] = [part]
                write(folder, "findings.jsonl", records)
                errors = check(folder)
                self.assertEqual(
                    [(e.file.split("/")[-1], e.line, e.field) for e in errors], [("findings.jsonl", 1, "parts[0]")]
                )
                data = architect.load(folder)
                self.assertEqual([e["field"] for e in data["errors"]], ["parts[0]"])

    def test_a_part_the_last_review_knew_and_the_design_dropped_still_resolves(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            findings = read(folder, "findings.jsonl")
            findings[0]["parts"] = ["box:user", "edge:e1"]
            write(folder, "findings.jsonl", findings)
            made = read(folder, "design.json")
            made["containers"]["edges"] = [e for e in made["containers"]["edges"] if e["id"] != "e1"]
            write(folder, "design.json", [made])
            self.assertEqual([str(e) for e in check(folder)], [])

    def test_a_flow_without_an_id_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            made = read(folder, "design.json")
            del made["flows"][0]["id"]
            write(folder, "design.json", [made])
            errors = check(folder)
            self.assertTrue(any(e.field.startswith("flows[0]") and "id" in e.field for e in errors), errors)
            self.assertEqual(run_check(folder)[0], 1)
            data = architect.load(folder)
            self.assertTrue(any(e["file"] == "design.json" for e in data["errors"]))
            self.assertEqual(data["flows"], [])

    def test_a_flow_id_used_twice_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            made = read(folder, "design.json")
            made["flows"].append(copy.deepcopy(made["flows"][0]))
            write(folder, "design.json", [made])
            self.assertTrue(any(e.file.endswith("design.json") for e in check(folder)))

    def test_pointers_by_id_across_the_files(self):
        cases = {
            "findings.jsonl": ("perspective", "ghost"),
            "decisions.jsonl": ("drivers", ["F1", "Z9"]),
            "reviews.jsonl": ("perspectives", ["ghost"]),
        }
        for name, (field, value) in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                folder = make_folder(Path(d))
                records = read(folder, name)
                records[0][field] = value
                write(folder, name, records)
                self.assertTrue([e for e in check(folder) if e.file.endswith(name) and e.line == 1], name)

    def test_a_finding_on_a_perspective_that_does_not_apply_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            perspectives = read(folder, "perspectives.jsonl")
            perspectives[0]["applies"] = False
            write(folder, "perspectives.jsonl", perspectives)
            self.assertTrue(
                [e for e in check(folder) if e.file.endswith("findings.jsonl") and e.field == "perspective"]
            )

    def test_a_request_sentence_must_be_in_the_request(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            requirements = read(folder, "requirements.jsonl")
            requirements[0]["source"]["sentence"] = "A sentence nobody wrote."
            write(folder, "requirements.jsonl", requirements)
            errors = check(folder)
            self.assertEqual([(e.line, e.field.split(".")[0]) for e in errors], [(1, "source")])

    def test_a_review_changes_only_parts_it_or_the_one_before_hashed(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            reviews = read(folder, "reviews.jsonl")
            reviews[0]["changed"] = ["box:user", "box:elsewhere"]
            write(folder, "reviews.jsonl", reviews)
            self.assertTrue(
                [e for e in check(folder) if e.file.endswith("reviews.jsonl") and e.field.startswith("changed")]
            )

    def test_the_approve_event_and_a_confirmation_point_to_ids(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            events = [
                {
                    "type": "approve",
                    "at": AT,
                    "by": "user",
                    "id": "a1",
                    "again": False,
                    "perspectives": ["security", "ghost"],
                    "changes": [],
                    "text": "Design approved",
                },
                {
                    "type": "confirm",
                    "at": AT,
                    "by": "user",
                    "id": "k1",
                    "requirement": "Z9",
                    "wording": "w",
                    "text": "ok",
                },
            ]
            write(folder, "conversation.jsonl", events)
            errors = check(folder)
            self.assertEqual(
                {(e.line, e.field.split("[")[0]) for e in errors}, {(1, "perspectives"), (2, "requirement")}
            )


class StatusRules(unittest.TestCase):
    def test_a_finding_is_handled_with_handled_by_and_open_without(self):
        good = examples("findings.jsonl")
        self.assertEqual({r["status"] for _, r in good}, {"open", "handled"})
        for status, extra, field in (("open", {"handled_by": "x"}, "handled_by"), ("handled", {}, "handled_by")):
            with self.subTest(status):
                record = {k: v for k, v in good[0][1].items() if k != "handled_by"} | {"status": status, **extra}
                problems = schema.check_record(record, ["findings.schema.json"], SCHEMAS)
                self.assertEqual([p[0] for p in problems], [field])

    def test_perspective_from_is_a_sum_type(self):
        record = examples("perspectives.jsonl")[0][1]
        for wrong in (
            {"type": "built_in", "file": "x.md"},
            {"type": "standard", "method": "STRIDE"},
            {"type": "standard"},
            "built in",
            {"type": "repo"},
        ):
            with self.subTest(wrong=wrong):
                problems = schema.check_record({**record, "from": wrong}, ["perspectives.schema.json"], SCHEMAS)
                self.assertTrue(problems)

    def test_ids_have_the_prefixes_of_the_page(self):
        finding = examples("findings.jsonl")[0][1]
        self.assertTrue(schema.check_record({**finding, "id": "F1"}, ["findings.schema.json"], SCHEMAS))
        self.assertTrue(schema.check_record({**finding, "id": "T1"}, ["findings.schema.json"], SCHEMAS))
        decision = examples("decisions.jsonl")[0][1]
        self.assertTrue(schema.check_record({**decision, "id": "D-2"}, ["decisions.schema.json"], SCHEMAS))

    def test_no_extra_fields_and_no_aliases(self):
        review = examples("reviews.jsonl")[0][1]
        problems = schema.check_record({**review, "aliases": {"a": "b"}}, ["reviews.schema.json"], SCHEMAS)
        self.assertEqual([p[0] for p in problems], ["aliases"])
        problems = schema.check_record(
            {**examples("architect.json")[0][1], "page": 1}, ["architect.schema.json"], SCHEMAS
        )
        self.assertEqual([p[0] for p in problems], ["page"])


class GeneratedSpecs(unittest.TestCase):
    def test_specs_md_says_it_is_generated_and_matches_spec_jsonl(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            out = Path(d) / "docs" / "specs.md"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(architect.main(["specs", str(folder), "--out", str(out)]), 0)
            text = out.read_text(encoding="utf-8")
            self.assertTrue(text.startswith(architect.GENERATED))
            self.assertIn("generated", architect.GENERATED.lower())
            records = read(folder, "spec.jsonl")
            rows = [
                [cell.strip() for cell in line.strip().strip("|").split("|")]
                for line in text.splitlines()
                if re.match(r"\|\s*S\d+\s*\|", line)
            ]
            self.assertEqual([r[0] for r in rows], [r["id"] for r in records if r["type"] == "spec"])
            self.assertEqual([r[1] for r in rows], [r["statement"] for r in records if r["type"] == "spec"])
            self.assertEqual([r[3] for r in rows], [r["checked_by"] for r in records if r["type"] == "spec"])
            self.assertIn("requirement Q1", rows[0][2])

    def test_gaps_and_unlinked_items_are_listed(self):
        records = [
            *folder_records()["spec.jsonl"],
            base("gap", id="G1", text="Retry?", status="assumed", choice="No retry", if_wrong="A failure shows once"),
            base("unlinked", item="Log format", why="no behaviour"),
        ]
        text = architect.specs_md(records, {"title": "T", "summary": "S"})
        self.assertIn("Retry?", text)
        self.assertIn("No retry", text)
        self.assertIn("Log format", text)
        self.assertTrue(text.startswith(architect.GENERATED))

    def test_specs_refuses_an_invalid_spec(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            records = read(folder, "spec.jsonl")
            del records[0]["statement"]
            write(folder, "spec.jsonl", records)
            out = Path(d) / "specs.md"
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                architect.main(["specs", str(folder), "--out", str(out)])
            self.assertFalse(out.exists())


class Review(unittest.TestCase):
    def test_review_records_perspective_ids_utc_and_the_base_fields(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d), **{"reviews.jsonl": None})
            with redirect_stdout(io.StringIO()):
                architect.main(["review", str(folder), "--perspectives", "security", "observability"])
            (record,) = read(folder, "reviews.jsonl")
            self.assertEqual(record["perspectives"], ["security", "observability"])
            self.assertEqual(record["type"], "review")
            self.assertEqual(record["by"], "architect")
            self.assertRegex(record["at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
            self.assertNotIn("aliases", record)
            self.assertIn("step:ask/s6", record["hashes"])
            self.assertEqual([str(e) for e in check(folder)], [])

    def test_review_refuses_a_name_that_is_not_an_applicable_perspective_id(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d), **{"reviews.jsonl": None})
            for name in ("Security", "api-standards"):
                with self.subTest(name), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    architect.main(["review", str(folder), "--perspectives", name])
            self.assertFalse((folder / "reviews.jsonl").exists())


class WrongTypes(unittest.TestCase):
    """For every field of every record architect.py reads, each wrong type, one at a time: `check` and `load` do not
    fail, the payload serialises, and the page's own code draws it."""

    WRONG = [[1], {"k": 1}, 5, True, None, "x"]

    def variants(self, records):
        for index, record in enumerate(records):
            for key, value in record.items():
                options = [(key,), *([(key, inner) for inner in value] if isinstance(value, dict) else [])]
                for path in options:
                    original = value if len(path) == 1 else value[path[1]]
                    for wrong in self.WRONG:
                        if wrong == original and type(wrong) is type(original):
                            continue
                        changed = json.loads(json.dumps(records))
                        target = changed[index][key] if len(path) == 2 else changed[index]
                        target[path[-1]] = wrong
                        yield f"{'.'.join(path)}[{index}]={wrong!r}", changed

    def test_no_wrong_type_breaks_check_load_or_the_page(self):
        node = shutil.which("node")
        payloads = []
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            base_files = {name: read(folder, name) for name in KINDS}
            base_files["architect.json"] = [base_files["architect.json"]]
            base_files["design.json"] = [base_files["design.json"]]
            for name, records in base_files.items():
                for label, changed in self.variants(records):
                    key = f"{name}: {label}"
                    with self.subTest(key):
                        write(folder, name, changed)
                        data = architect.load(folder)
                        json.dumps(data)
                        with redirect_stdout(io.StringIO()):
                            code = architect.main(["check", str(folder)])
                        self.assertIn(code, (0, 1))
                        payloads.append({"label": key, "data": data})
                write(folder, name, records)
            self.assertGreater(len(payloads), 500)
            if node:
                path = Path(d) / "payloads.json"
                path.write_text(json.dumps(payloads))
                run = subprocess.run(
                    [node, str(ROOT / "tests" / "render-architect-payloads.js"), str(path)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(run.returncode, 0, run.stderr[:3000])

    def test_an_invalid_record_shows_without_the_fields_that_failed(self):
        with tempfile.TemporaryDirectory() as d:
            records = folder_records()["requirements.jsonl"]
            records[0] = {**records[0], "kind": 5, "text": ["x"]}
            folder = make_folder(Path(d), **{"requirements.jsonl": records})
            data = architect.load(folder)
        first = data["requirements"][0]
        self.assertTrue(first["_errors"])
        self.assertEqual(first["id"], "F1")
        self.assertEqual({e["field"] for e in data["errors"]}, {"kind", "text"})
        self.assertEqual(data["requirements"][1]["id"], "F3")
        self.assertNotIn("_errors", data["requirements"][1])


class RawLines(unittest.TestCase):
    """Whatever a line holds, `check` and `load` do not raise and the payload is JSON the browser can read."""

    LINES = [
        "[1]",
        "5",
        "null",
        '"x"',
        "",
        "{",
        '{"a": NaN}',
        '{"type": "requirement", "id": Infinity}',
        '{"n": 1e999}',
        "[" * 50000 + "]" * 50000,
        '{"a": ' * 50000 + "1" + "}" * 50000,
    ]

    def test_no_line_breaks_check_load_or_the_payload(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            write(
                folder,
                "conversation.jsonl",
                [{"type": "note", "at": AT, "by": "user", "id": "n1", "text": "hi", "to": None}],
            )
            for name in (*KINDS, "conversation.jsonl"):
                original = (folder / name).read_text()
                for line in self.LINES:
                    with self.subTest(name=name, line=line[:30]):
                        if name in JSON_FILES:
                            (folder / name).write_text(line + "\n")
                        else:
                            (folder / name).write_text(original + line + "\n")
                        data = architect.load(folder)
                        json.dumps(data, allow_nan=False)
                        with redirect_stdout(io.StringIO()):
                            self.assertIn(architect.main(["check", str(folder)]), (0, 1))
                (folder / name).write_text(original)

    def test_a_value_the_schema_accepts_but_the_page_cannot_read_is_an_error_on_its_line(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            records = read(folder, "requirements.jsonl")
            text = "".join(json.dumps(r) + "\n" for r in records[:1])
            (folder / "requirements.jsonl").write_text(text.rstrip("\n").removesuffix("}") + ', "n": NaN}\n')
            data = architect.load(folder)
            self.assertEqual([(e["file"], e["line"]) for e in data["errors"]][:1], [("requirements.jsonl", 1)])
            json.dumps(data, allow_nan=False)


class EveryAcceptedExampleRenders(unittest.TestCase):
    """A schema that accepts a value the page cannot draw is a bug in the schema: what the schemas accept is drawn."""

    def odd_ids(self, folder):
        made = read(folder, "design.json")
        for node in made["containers"]["nodes"]:
            node["id"] = node["id"] + "\"<b>&'"
        for edge in made["containers"]["edges"]:
            edge["from"] += "\"<b>&'"
            edge["to"] += "\"<b>&'"
        flow = made["flows"][0]
        flow["id"] = "a\"<i>&'"
        for p in flow["participants"]:
            p["box"] += "\"<b>&'"
        write(folder, "design.json", [made])
        findings = read(folder, "findings.jsonl")
        for finding in findings:
            finding["parts"] = [part.replace("step:ask/", "step:a\"<i>&'/") for part in finding["parts"]]
        write(folder, "findings.jsonl", findings)

    def test_the_example_the_planted_folders_and_odd_ids_render(self):
        node = shutil.which("node")
        payloads = []
        folders = [
            SCRIPTS / "example",
            *sorted((ROOT / "evals" / "cases" / "architect-better").glob("*/repo/docs/designs/*/architect.json")),
        ]
        for folder in [f.parent if f.name == "architect.json" else f for f in folders]:
            data = architect.load(folder)
            json.dumps(data, allow_nan=False)
            payloads.append({"label": str(folder.relative_to(ROOT)), "data": data})
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            self.assertEqual(check(folder), [])
            self.odd_ids(folder)
            self.assertEqual([str(e) for e in check(folder)], [])
            data = architect.load(folder)
            self.assertEqual(data["errors"], [])
            self.assertIn("&lt;b&gt;", data["containers"]["after"])
            payloads.append({"label": "odd ids", "data": data})
            if node:
                path = Path(d) / "payloads.json"
                path.write_text(json.dumps(payloads))
                run = subprocess.run(
                    [node, str(ROOT / "tests" / "render-architect-payloads.js"), str(path)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(run.returncode, 0, run.stderr[:3000])


class MovedChecks(unittest.TestCase):
    """The diagram's references and the sources' files are checked by schema.py, so `schema.py check` alone rejects what
    `architect.py check` rejects."""

    def design_with(self, change):
        made = design()
        change(made)
        return made

    def broken_designs(self):
        def edge_to(d):
            d["containers"]["edges"][0]["to"] = "nowhere"

        def edge_from(d):
            d["containers"]["edges"][0]["from"] = "nowhere"

        def step_from(d):
            d["flows"][0]["steps"][0]["from"] = "ghost"

        def participant_box(d):
            d["flows"][0]["participants"][0]["box"] = "nowhere"

        def group_member(d):
            d["containers"]["groups"] = [{"id": "g", "label": "G", "members": ["user", "nowhere"]}]

        def box_in_two_groups(d):
            d["containers"]["groups"] = [
                {"id": "g1", "label": "G1", "members": ["user"]},
                {"id": "g2", "label": "G2", "members": ["user"]},
            ]

        def duplicate_node(d):
            d["containers"]["nodes"].append(dict(d["containers"]["nodes"][0]))

        def duplicate_step(d):
            d["flows"][0]["steps"].append(dict(d["flows"][0]["steps"][0]))

        def unknown_kind(d):
            d["containers"]["nodes"][0]["kind"] = "unknown-widget"

        return {
            "edge to a missing box": (edge_to, "nowhere"),
            "edge from a missing box": (edge_from, "nowhere"),
            "step from a missing participant": (step_from, "ghost"),
            "participant on a missing box": (participant_box, "nowhere"),
            "group member that is no box": (group_member, "nowhere"),
            "box in two groups": (box_in_two_groups, "more than one group"),
            "node id used twice": (duplicate_node, "Duplicate id"),
            "step id used twice": (duplicate_step, "Duplicate id"),
            "box kind not in the register": (unknown_kind, "unknown-widget"),
        }

    def test_schema_check_alone_rejects_each_broken_design_and_architect_check_agrees(self):
        for label, (change, word) in self.broken_designs().items():
            with self.subTest(label), tempfile.TemporaryDirectory() as d:
                folder = make_folder(Path(d), **{"findings.jsonl": [], "reviews.jsonl": None})
                write(folder, "design.json", [self.design_with(change)])
                errors = [e for e in check(folder) if e.file.endswith("design.json")]
                self.assertTrue(errors, label)
                self.assertTrue(any(word in e.message for e in errors), [str(e) for e in errors])
                code, out, _ = run_check(folder)
                self.assertEqual(code, 1)
                for e in errors:
                    self.assertIn(f"design.json:{e.line}: {e.field}: {e.message}", out)
                self.assertNotIn("(diagram)", out)

    def test_a_good_design_passes_both(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            self.assertEqual([str(e) for e in check(folder)], [])
            self.assertEqual(run_check(folder)[0], 0)

    def test_every_box_kind_of_the_register_is_accepted(self):
        kinds = [k["name"] for k in json.loads((SCRIPTS / "kinds.json").read_text())]
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            made = read(folder, "design.json")
            for i, kind in enumerate(kinds):
                made["containers"]["nodes"].append({"id": f"k{i}", "label": kind, "kind": kind})
            write(folder, "design.json", [made])
            self.assertEqual([str(e) for e in check(folder)], [])

    def test_a_requirement_source_file_must_exist_in_the_repo(self):
        cases = {
            "docs/there.md": None,
            "docs/missing.md": "missing or out-of-scope source",
            "../outside.md": "invalid source path",
            "/etc/passwd": "invalid source path",
            ".git/config": "invalid source path",
            "docs": "missing or out-of-scope source",
        }
        for path, message in cases.items():
            with self.subTest(path), tempfile.TemporaryDirectory() as d:
                folder = make_folder(Path(d))
                (Path(d) / "docs").mkdir(exist_ok=True)
                (Path(d) / "docs" / "there.md").write_text("x\n")
                requirements = read(folder, "requirements.jsonl")
                requirements[0]["source"] = {"type": "file", "file": path, "symbol": "s"}
                write(folder, "requirements.jsonl", requirements)
                errors = [e for e in check(folder) if e.file.endswith("requirements.jsonl")]
                if message is None:
                    self.assertEqual(errors, [])
                    self.assertEqual(run_check(folder)[0], 0)
                else:
                    self.assertEqual([(e.line, e.field) for e in errors], [(1, "source.file")], errors)
                    self.assertIn(message, errors[0].message)
                    self.assertIn(f"requirements.jsonl:1: source.file: {errors[0].message}", run_check(folder)[1])

    def test_the_planted_eval_repos_pass_schema_check_as_repos_of_their_own(self):
        """An eval case's `repo/` is checked out as a repository of its own; its sources are files of that repository."""
        cases = sorted((ROOT / "evals" / "cases" / "architect-better").glob("*/repo/docs/designs/*/architect.json"))
        self.assertGreater(len(cases), 10)
        for architect_json in cases:
            repo = architect_json.parents[3]
            with self.subTest(case=repo.parent.name), tempfile.TemporaryDirectory() as d:
                copy = Path(d) / "repo"
                shutil.copytree(repo, copy)
                (copy / ".git").mkdir()
                folder = copy / architect_json.parent.relative_to(repo)
                self.assertEqual([str(e) for e in schema.check_paths([folder], SCHEMAS)], [])
                self.assertEqual(run_check(folder)[0], 0)

    def test_the_schema_does_not_duplicate_what_diagram_py_still_checks(self):
        """diagram.py keeps only what needs the drawing: a finding target that names no part of the layout."""
        text = (SCRIPTS / "diagram.py").read_text()
        self.assertNotIn("belongs to more than one group", text)
        self.assertNotIn("references missing", text)
        self.assertIn("Finding target", text)


class Templates(unittest.TestCase):
    """Each line of a template, with its placeholders filled, is a record its schema accepts, and the templates state
    the conventions and show every shape of a record that depends on a status or a tagged source."""

    SCHEMA_OF = {
        "architect": "architect.schema.json",
        "design": "design.schema.json",
        "requirement": "requirements.schema.json",
        "perspective": "perspectives.schema.json",
        "finding": "findings.schema.json",
        "decision": "decisions.schema.json",
        "review": "reviews.schema.json",
        "spec": "spec.schema.json",
        "gap": "spec.schema.json",
        "unlinked": "spec.schema.json",
    }

    def lines(self):
        found = []
        for path in sorted((SKILL / "templates").glob("*.md")):
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if line.startswith("{") and line.endswith("}"):
                    found.append((path.name, number, line))
        return found

    @staticmethod
    def fill(line):
        line = line.replace("<UTC time>", AT).replace("<agent>", "architect").replace("<n>", "1")
        line = re.sub(r"<SHA-256[^>]*>", DIGEST, line)
        return re.sub(r"<[^<>\"]+>", "text", line)

    def test_every_template_line_is_a_valid_record_once_filled(self):
        found = self.lines()
        self.assertGreater(len(found), 20)
        for name, number, line in found:
            with self.subTest(template=name, line=number):
                record = json.loads(self.fill(line))
                self.assertEqual(
                    schema.check_record(record, [self.SCHEMA_OF[record["type"]]], SCHEMAS), [], self.fill(line)
                )

    def test_each_shape_has_a_line(self):
        records = [json.loads(self.fill(line)) for _, _, line in self.lines()]
        shapes = {
            ("gap", "asked"),
            ("gap", "assumed"),
            ("gap", "answered"),
            ("finding", "open"),
            ("finding", "handled"),
            *(("requirement", t) for t in ("request", "file", "user", "guessed")),
            *(("spec", t) for t in ("design", "request", "decision", "requirement")),
            *(("perspective", t) for t in ("built_in", "standard")),
            *(("architect", t) for t in ("chat", "issue", "file")),
            ("unlinked", None),
            ("decision", None),
            ("review", None),
            ("design", None),
        }
        seen = set()
        for r in records:
            kind = r["type"]
            if kind in ("gap", "finding"):
                seen.add((kind, r["status"]))
            elif kind in ("requirement", "spec"):
                seen.add((kind, r["source"]["type"]))
            elif kind == "perspective":
                seen.add((kind, r["from"]["type"]))
            elif kind == "architect":
                seen.add((kind, r["request"]["from"]["type"]))
            else:
                seen.add((kind, None))
        self.assertEqual(shapes - seen, set())

    def test_the_templates_state_the_conventions(self):
        text = "\n".join(p.read_text() for p in (SKILL / "templates").glob("*.md") if "{" in p.read_text())
        for convention in (
            "`type`, `at` (UTC, ending in Z) and `by`",
            "`null`",
            "JSON array",
            "the record a pointer names before the pointer",
            "A field the schema does not name is an error",
            "schema.py check",
        ):
            self.assertIn(convention, text)

    def test_a_template_holds_placeholders_only(self):
        for name, number, line in self.lines():
            with self.subTest(template=name, line=number):
                values = re.findall(r'": "([^"]*)"', line)
                for value in values:
                    self.assertTrue(
                        "<" in value
                        or value in ("architect", "chat", "asked", "assumed", "answered", "open", "handled")
                        or value in KINDWORDS,
                        value,
                    )


KINDWORDS = {
    "design", "request", "decision", "requirement", "file", "user", "guessed", "issue", "built_in", "standard",
    "functional", "quality", "constraint", "spec", "gap", "unlinked", "perspective", "finding", "review", "architect",
    "service", "person", "box", "step", "async", "response", "dashboard", "after", "before",
}  # fmt: skip


class DiagramShapeFirst(unittest.TestCase):
    """diagram.py checks the shape with the schema first, and the references only of a design that has the shape."""

    def plain(self):
        d = design()
        return {"containers": d["containers"], "flows": d["flows"]}

    def test_a_step_kind_the_renderer_cannot_draw_is_refused_by_check(self):
        made = self.plain()
        made["flows"][0]["steps"][0]["kind"] = "foo"
        errors = diagram.validate(made)
        self.assertTrue(any("kind" in e and "foo" in e or "kind" in e for e in errors), errors)
        with self.assertRaises(ValueError):
            diagram.layout(made)

    def test_a_node_id_that_is_not_text_gives_the_shape_error_and_no_reference_errors(self):
        made = self.plain()
        made["containers"]["nodes"][0]["id"] = 5
        errors = diagram.validate(made)
        self.assertTrue(errors)
        self.assertFalse([e for e in errors if "references missing" in e], errors)
        self.assertTrue(any("containers.nodes[0].id" in e for e in errors), errors)

    def test_a_well_shaped_design_still_gets_the_reference_checks(self):
        made = self.plain()
        made["containers"]["edges"][0]["to"] = "nowhere"
        self.assertTrue(any("references missing 'nowhere'" in e for e in diagram.validate(made)))

    def test_the_findings_the_page_adds_are_not_a_shape_error(self):
        made = self.plain()
        made["findings"] = {"user": [["V1", "t", "security"]]}
        self.assertEqual(diagram.validate(made), [])

    def test_check_and_render_agree_on_a_good_and_a_bad_design(self):
        for change, ok in (({}, True), ({"kind": "foo"}, False)):
            made = self.plain()
            made["flows"][0]["steps"][0].update(change)
            try:
                diagram.layout(made)
                rendered = True
            except ValueError:
                rendered = False
            self.assertEqual((diagram.validate(made) == []), ok)
            self.assertEqual(rendered, ok)


class LoadNeverRaises(unittest.TestCase):
    def test_a_source_file_that_goes_away_between_check_and_read_is_an_error_entry(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            (Path(d) / "docs").mkdir(exist_ok=True)
            (Path(d) / "docs" / "there.md").write_text("x\n")
            requirements = read(folder, "requirements.jsonl")
            requirements[0]["source"] = {"type": "file", "file": "docs/there.md", "symbol": "s"}
            write(folder, "requirements.jsonl", requirements)
            self.assertEqual(architect.load(folder)["errors"], [])
            with mock.patch.object(architect, "source_file", side_effect=ValueError("missing or out-of-scope source")):
                data = architect.load(folder)
                json.dumps(data, allow_nan=False)
                self.assertEqual(
                    [(e["file"], e["line"], e["field"]) for e in data["errors"]],
                    [("requirements.jsonl", 1, "source.file")],
                )
                code, out, _ = run_check(folder)
            self.assertEqual(code, 1)
            self.assertIn("requirements.jsonl:1: source.file:", out)


class SpecsNeedRecords(unittest.TestCase):
    def test_no_spec_records_writes_nothing_and_says_so(self):
        for records in (None, []):
            with self.subTest(records=records), tempfile.TemporaryDirectory() as d:
                folder = make_folder(Path(d), **{"spec.jsonl": records})
                out = Path(d) / "specs.md"
                err = io.StringIO()
                with redirect_stdout(io.StringIO()), redirect_stderr(err), self.assertRaises(SystemExit):
                    architect.main(["specs", str(folder), "--out", str(out)])
                self.assertIn("spec.jsonl has no records: write the spec first", err.getvalue())
                self.assertFalse(out.exists())

    def test_gaps_alone_are_not_a_spec(self):
        with tempfile.TemporaryDirectory() as d:
            gap = base("gap", id="G1", text="t", status="assumed", choice="c", if_wrong="w")
            folder = make_folder(Path(d), **{"spec.jsonl": [gap]})
            out = Path(d) / "specs.md"
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                architect.main(["specs", str(folder), "--out", str(out)])
            self.assertFalse(out.exists())


class NullIsAbsent(unittest.TestCase):
    """An optional field may be null, which means the same as leaving it out; a field a status drives may not."""

    OPTIONAL = {
        "design.schema.json": [
            ("containers.nodes[0].detail", None),
            ("containers.nodes[0].in", None),
            ("containers.edges[0].label", None),
            ("containers.edges[0].in", None),
            ("containers.edges", None),
            ("containers.groups", None),
            ("flows[0].in", None),
            ("flows[0].participants[0].in", None),
            ("flows[0].steps[0].kind", None),
            ("flows[0].steps[0].label", None),
            ("flows[0].steps[0].in", None),
        ],
    }

    @staticmethod
    def put(record, path, value):
        parts = re.findall(r"[^.\[\]]+|\[\d+\]", path)
        target = record
        for part in parts[:-1]:
            target = target[int(part[1:-1])] if part.startswith("[") else target[part]
        last = parts[-1]
        target[last] = value

    def test_the_schemas_accept_null_for_an_optional_field(self):
        for name, cases in self.OPTIONAL.items():
            for path, value in cases:
                with self.subTest(path):
                    record = design()
                    self.put(record, path, value)
                    self.assertEqual(schema.check_record(record, [name], SCHEMAS), [])
        record = examples("perspectives.jsonl")[0][1]
        record["from"] = {"type": "built_in", "method": None}
        self.assertEqual(schema.check_record(record, ["perspectives.schema.json"], SCHEMAS), [])
        record = examples("reviews.jsonl")[0][1]
        record["labels"] = None
        self.assertEqual(schema.check_record(record, ["reviews.schema.json"], SCHEMAS), [])

    def test_a_status_driven_field_is_still_refused_as_null(self):
        finding = {**examples("findings.jsonl")[0][1], "status": "open", "handled_by": None}
        problems = schema.check_record(finding, ["findings.schema.json"], SCHEMAS)
        self.assertEqual([p[0] for p in problems], ["handled_by"])
        self.assertIn("status", problems[0][1])

    def test_a_folder_with_nulls_loads_draws_and_hashes_like_one_without(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a").mkdir()
            (Path(d) / "b").mkdir()
            plain = make_folder(Path(d) / "a")
            nulls = make_folder(Path(d) / "b")
            made = read(nulls, "design.json")
            made["containers"]["nodes"][0]["detail"] = None
            made["containers"]["edges"][0]["in"] = None
            made["containers"]["groups"] = None
            made["flows"][0]["steps"][0]["kind"] = None
            made["flows"][0]["in"] = None
            write(nulls, "design.json", [made])
            perspectives = read(nulls, "perspectives.jsonl")
            perspectives[0]["from"] = {"type": "built_in", "method": None}
            write(nulls, "perspectives.jsonl", perspectives)
            reviews = read(nulls, "reviews.jsonl")
            reviews[0]["labels"] = None
            write(nulls, "reviews.jsonl", reviews)
            self.assertEqual([str(e) for e in check(nulls)], [])
            a, b = architect.load(plain), architect.load(nulls)
            self.assertEqual(b["errors"], [])
            json.dumps(b, allow_nan=False)
            self.assertEqual(a["containers"], b["containers"])
            self.assertEqual(a["flows"], b["flows"])
            self.assertEqual(
                {k: v["label"] for k, v in a["parts"].items()}, {k: v["label"] for k, v in b["parts"].items()}
            )
            self.assertEqual(architect.read_folder(plain)["hashes"], architect.read_folder(nulls)["hashes"])

    def test_diagram_py_treats_null_like_absent(self):
        plain = DiagramShapeFirst().plain()
        nulls = DiagramShapeFirst().plain()
        nulls["containers"]["nodes"][0]["detail"] = None
        nulls["containers"]["edges"][0]["in"] = None
        nulls["containers"]["groups"] = None
        nulls["flows"][0]["steps"][0]["kind"] = None
        self.assertEqual(diagram.validate(nulls), [])
        self.assertEqual(
            diagram.svg_containers(diagram.layout(nulls), "after"),
            diagram.svg_containers(diagram.layout(plain), "after"),
        )


class DiagramCli(unittest.TestCase):
    """`diagram.py check` and `render` agree on every design the schema accepts, and never show a traceback."""

    def run_cli(self, command, text, tmp):
        path = Path(tmp) / "design.json"
        path.write_text(text)
        argv = [sys.executable, "-I", str(SCRIPTS / "diagram.py"), command, str(path)]
        if command == "render":
            argv += ["--out", str(Path(tmp) / "out")]
        return subprocess.run(argv, capture_output=True, text=True)

    def full_design(self):
        made = design()
        made["containers"]["groups"] = [{"id": "g", "label": "G", "members": ["user"], "in": ["after"]}]
        made["containers"]["nodes"][0].update(detail="d", **{"in": ["after"]})
        made["containers"]["edges"][0].update(**{"in": ["after"]})
        made["flows"][0].update(**{"in": ["after"]})
        made["flows"][0]["participants"][0].update(**{"in": ["after"]})
        made["flows"][0]["steps"][0].update(**{"in": ["after"]})
        return made

    def optional_paths(self, value, prefix=()):
        """Every optional field of a design, as a path: those a schema marks null-able and the design holds."""
        required = {
            "type",
            "at",
            "by",
            "id",
            "label",
            "kind",
            "from",
            "to",
            "members",
            "name",
            "box",
            "nodes",
            "flows",
            "containers",
            "participants",
            "steps",
        }
        if isinstance(value, dict):
            for key, inner in value.items():
                here = (*prefix, key)
                optional = key not in required or (
                    key in ("label", "kind") and (prefix[-2:-1] == ("steps",) or prefix[-2:-1] == ("edges",))
                )
                if optional and key not in ("type", "at", "by"):
                    yield here
                yield from self.optional_paths(inner, here)
        elif isinstance(value, list):
            for index, inner in enumerate(value):
                yield from self.optional_paths(inner, (*prefix, index))

    def test_every_optional_field_set_to_null_checks_and_renders(self):
        paths = sorted(set(self.optional_paths(self.full_design())), key=str)
        names = {p[-1] for p in paths}
        for needed in ("detail", "in", "label", "kind", "edges", "groups"):
            self.assertIn(needed, names)
        for path in paths:
            with self.subTest(path=path), tempfile.TemporaryDirectory() as tmp:
                made = self.full_design()
                target = made
                for part in path[:-1]:
                    target = target[part]
                target[path[-1]] = None
                self.assertEqual(schema.check_record(made, ["design.schema.json"], SCHEMAS), [])
                check = self.run_cli("check", json.dumps(made), tmp)
                self.assertEqual((check.returncode, check.stderr), (0, ""))
                render = self.run_cli("render", json.dumps(made), tmp)
                self.assertEqual((render.returncode, render.stderr), (0, ""))

    def test_a_design_that_is_not_an_object_is_an_error_not_a_traceback(self):
        for text in ("[]", "5", "null", '"x"', "true"):
            for command in ("check", "render"):
                with self.subTest(text=text, command=command), tempfile.TemporaryDirectory() as tmp:
                    run = self.run_cli(command, text, tmp)
                    self.assertEqual(run.returncode, 1)
                    self.assertIn("design: expected an object", run.stderr)
                    self.assertNotIn("Traceback", run.stderr)

    def test_a_design_nested_very_deep_is_an_error_not_a_traceback(self):
        for depth in (2000, 50000):
            text = '{"a": ' * depth + "1" + "}" * depth
            for command in ("check", "render"):
                with self.subTest(depth=depth, command=command), tempfile.TemporaryDirectory() as tmp:
                    run = self.run_cli(command, text, tmp)
                    self.assertEqual(run.returncode, 1)
                    self.assertEqual(run.stderr.strip(), "design: nested too deeply")
                    self.assertFalse((Path(tmp) / "out").exists())

    def test_an_answered_gap_is_written_as_answered(self):
        records = [
            base("spec", id="S1", statement="s", source={"type": "design", "section": "x"}, checked_by="c"),
            base("gap", id="G1", text="t", status="answered", decision="D2", if_wrong="w"),
            base("gap", id="G2", text="t", status="asked", decision="D3", if_wrong="w"),
        ]
        text = architect.specs_md(records, {"title": "T"})
        self.assertIn("answered (D2)", text)
        self.assertNotIn("asked (D2)", text)
        self.assertIn("asked (D3)", text)


class RequiredFiles(unittest.TestCase):
    """A folder missing a file its other files need fails `schema.py check <folder>` too, not only architect.py check."""

    def test_a_folder_missing_design_json_or_architect_json_fails_both_checks(self):
        for missing in ("design.json", "architect.json"):
            with self.subTest(missing), tempfile.TemporaryDirectory() as d:
                folder = make_folder(Path(d), **{missing: None})
                errors = check(folder)
                self.assertEqual([(Path(e.file).name, e.line, e.field) for e in errors], [(missing, 1, "(file)")])
                code, out, _ = run_check(folder)
                self.assertEqual(code, 1)
                self.assertIn(f"{missing}:1: (file): missing file", out)
                self.assertTrue(errors[0].file.endswith(missing))
                self.assertIn(f"{missing}:1: (file): {errors[0].message}", out)

    def test_a_good_folder_and_a_folder_with_no_architect_files_pass(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(check(make_folder(Path(d))), [])
            other = Path(d) / "elsewhere"
            write(
                other,
                "conversation.jsonl",
                [{"type": "note", "at": AT, "by": "user", "id": "n1", "text": "hi", "to": None}],
            )
            self.assertEqual([str(e) for e in check(other)], [])

    def test_the_requirement_is_declared_in_the_schemas_not_in_architect_py(self):
        for name in ("architect", "design", "requirements", "perspectives", "findings", "decisions", "reviews"):
            doc = json.loads((SCHEMAS / f"{name}.schema.json").read_text())
            self.assertEqual(doc["x-required-files"], ["architect.json", "design.json"], name)

    def test_a_schema_with_a_malformed_required_files_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / "schemas"
            shutil.copytree(SCHEMAS, copy)
            doc = json.loads((copy / "design.schema.json").read_text())
            doc["x-required-files"] = "design.json"
            (copy / "design.schema.json").write_text(json.dumps(doc))
            with self.assertRaises(schema.SchemaError):
                schema.load_schemas(copy)


class SpecRowsCheck(unittest.TestCase):
    """The eval check for spec.jsonl skips gap and unlinked rows only: a row with no type is held to the rules."""

    CHECK = ROOT / "evals" / "cases" / "architect-better" / "spec-covers-failure-cases" / "checks" / "spec_rows.py"

    def run_check(self, rows):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "docs" / "designs" / "2026-11-order-export"
            folder.mkdir(parents=True)
            (folder / "spec.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
            return subprocess.run([sys.executable, str(self.CHECK)], cwd=tmp, capture_output=True, text=True)

    GOOD = base("spec", id="S1", statement="s", source={"type": "design", "section": "x"}, checked_by="c")

    def test_a_row_with_no_type_is_checked(self):
        run = self.run_check([self.GOOD, {"id": "S2"}])
        self.assertEqual(run.returncode, 1)
        self.assertIn("S2: statement is empty or missing", run.stderr)

    def test_gap_and_unlinked_rows_are_skipped_and_a_spec_row_is_required(self):
        gap = base("gap", id="G1", text="t", status="assumed", choice="c", if_wrong="w")
        unlinked = base("unlinked", item="i", why="w")
        self.assertEqual(self.run_check([self.GOOD, gap, unlinked]).returncode, 0)
        run = self.run_check([gap, unlinked])
        self.assertEqual(run.returncode, 1)
        self.assertIn("holds no spec requirement", run.stderr)


class ModeText(unittest.TestCase):
    """The mode files, the example and the templates name the new files, and say once where to check every write."""

    SENTENCE = (
        "AFTER every write to a JSON or JSONL file in the change folder, RUN "
        "`python3 <skill dir>/scripts/schema.py check <file>` and FIX every error before your next step."
    )

    def test_each_mode_says_to_check_every_write_with_the_skill_dir_form(self):
        for name in ("design.md", "audit.md"):
            with self.subTest(name):
                text = (SKILL / "modes" / name).read_text()
                self.assertEqual(text.count(self.SENTENCE), 1)
                self.assertLess(text.index(self.SENTENCE), text.index("\n## "))

    def test_no_skill_text_names_the_old_files(self):
        self.assertNotIn("request.md", (SKILL / "SKILL.md").read_text())
        for path in [
            *(SKILL / "modes").glob("*.md"),
            *(SKILL / "agents").glob("*.md"),
            *(SKILL / "templates").glob("*.md"),
        ]:
            with self.subTest(path.name):
                self.assertNotIn("request.md", path.read_text())
        readme = (SCRIPTS / "example" / "README.md").read_text()
        for word in ("request.md", "aliases", "flow<N>"):
            self.assertNotIn(word, readme)
        for name in ("architect.json", "findings.jsonl", "conversation.jsonl", "specs.md"):
            self.assertIn(name, readme)
        self.assertIn("## What checks what", readme)
        self.assertIn(
            "a folder that holds only `spec.jsonl` passes `schema.py check` and fails `architect.py check`", readme
        )


class Serving(unittest.TestCase):
    def test_the_page_payload_carries_errors_and_is_not_an_offline_notice(self):
        with tempfile.TemporaryDirectory() as d:
            folder = make_folder(Path(d))
            records = read(folder, "decisions.jsonl")
            records[0]["drivers"] = ["Z9"]
            write(folder, "decisions.jsonl", records)
            with mock.patch.object(architect.webbrowser, "open"):
                data = architect.load(folder)
            self.assertEqual([e["file"] for e in data["errors"]], ["decisions.jsonl"])
            self.assertEqual(data["title"], read(folder, "architect.json")["title"])
            self.assertTrue(data["containers"]["after"])

    def test_the_page_script_shows_an_errors_band_and_reads_the_new_fields(self):
        page = (SCRIPTS / "architect.html").read_text() + (SCRIPTS / "architect.js").read_text()
        self.assertIn("errors", page)
        self.assertNotIn("request.md", page)


if __name__ == "__main__":
    unittest.main()
