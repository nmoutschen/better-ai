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


def base(kind, **more):
    return {"type": kind, "at": AT, "by": "architect", **more}


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

    def test_the_example_folder_and_every_planted_eval_folder_check_clean(self):
        folders = [
            SCRIPTS / "example",
            *sorted((ROOT / "evals" / "cases" / "architect-better").glob("*/repo/docs/designs/*")),
        ]
        self.assertGreater(len(folders), 10)
        for folder in folders:
            with self.subTest(folder=str(folder.relative_to(ROOT))):
                files = [p for p in folder.iterdir() if p.is_file() and p.name in (*KINDS, "conversation.jsonl")]
                self.assertEqual([str(e) for e in schema.check_paths(files, SCHEMAS)], [])
                self.assertFalse((folder / "request.md").exists())


class OneBadRecordPerKind(unittest.TestCase):
    """A bad record is reported with its file, its line and the field, the good ones around it are not, and the page
    still shows the bad one, marked."""

    BAD = {
        "architect.json": (lambda r: {k: v for k, v in r.items() if k != "title"}, "title"),
        "design.json": (lambda r: {**r, "flows": [{k: v for k, v in r["flows"][0].items() if k != "id"}]}, "flows"),
        "requirements.jsonl": (lambda r: {**r, "kind": "weird"}, "kind"),
        "perspectives.jsonl": (lambda r: {**r, "from": {"type": "built in"}}, "from"),
        "findings.jsonl": (lambda r: {**r, "status": "handled"}, "handled_by"),
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
                listed = [e for e in data["errors"] if e["file"] == name and e["field"].split("[")[0] == field]
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
            self.assertTrue(any(e.field.startswith("flows[0]") and "id" in e.message for e in errors), errors)
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
