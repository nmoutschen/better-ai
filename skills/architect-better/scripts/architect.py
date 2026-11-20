#!/usr/bin/env python3
"""Serve the live architecture design and carry review requests to the architect.

The change-folder format and review handoff are documented in example/README.md.
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import sys
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import diagram  # noqa: E402
import page  # noqa: E402

FILES = (
    "design.json",
    "request.md",
    "requirements.jsonl",
    "perspectives.jsonl",
    "findings.jsonl",
    "reviews.jsonl",
    "decisions.jsonl",
    "spec.jsonl",
)
ASSETS = {
    "/": ("architect.html", "text/html"),
    "/page.css": ("page.css", "text/css"),
    "/architect.css": ("architect.css", "text/css"),
    "/page.js": ("page.js", "text/javascript"),
    "/architect.js": ("architect.js", "text/javascript"),
}
ITEMS = ("comment", "note", "approve", "confirm")
TABS = ("requirements", "containers", "flows", "perspectives", "decisions", "spec")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(record, **schema):
    require(isinstance(record, dict), f"expected an object with {', '.join(schema)}")
    for key, kind in schema.items():
        require(type(record.get(key)) is kind, f"{key}: expected {kind.__name__}")


def read_text(folder, name):
    try:
        return (folder / name).read_bytes().decode("utf-8")
    except FileNotFoundError:
        if name == "reviews.jsonl":
            return ""
        raise ValueError(f"{name}:1: missing file") from None
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"{name}:1: {exc}") from exc


def read_records(folder, name, validate, unique=None):
    records, seen, errors = [], set(), []
    content = read_text(folder, name)
    lines = content.removesuffix("\n").split("\n") if content else []
    for line, raw in enumerate(lines, 1):
        try:
            record = json.loads(raw)
            require(isinstance(record, dict), "expected an object")
            if unique:
                fields(record, **{unique: str})
                value = record[unique]
                require(value.strip() and value not in seen, f"empty or duplicate {unique} {value!r}")
            validate(record)
            records.append(record)
            if unique:
                seen.add(value)
        except (AttributeError, KeyError, OSError, TypeError, ValueError) as exc:
            errors.append(f"{name}:{line}: {exc}")
    require(not errors, "\n".join(errors))
    return records


def source_file(folder, path):
    """Serve only explicitly linked files, scoped to the change folder or its repository."""
    if path == "request.md":
        root = folder
    else:
        root = next((p for p in (folder, *folder.parents) if (p / ".git").exists()), folder)
    name = Path(path)
    require(
        not name.is_absolute() and not set(name.parts).intersection({"..", ".git"}), f"invalid source path {path!r}"
    )
    target = (root / name).resolve()
    require(target.is_relative_to(root) and target.is_file(), f"missing or out-of-scope source {path!r}")
    return target


def read_folder(folder: Path) -> dict:
    """Read and validate the page files, including traced references and diagram targets."""
    folder = folder.resolve()
    request = read_text(folder, "request.md")
    try:
        design = json.loads(read_text(folder, "design.json"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"design.json:{exc.lineno}: {exc.msg}") from exc
    try:
        fields(design, title=str, summary=str, scope=str, accepted=list, containers=dict, flows=list)
        require(set(design["accepted"]) <= set(TABS), "unknown accepted section")
        errors = diagram.validate(design)
        require(not errors, "\n".join(errors))
        for flow in design["flows"]:
            fields(flow, name=str)
            if "id" in flow:
                fields(flow, id=str)
        parts = diagram_parts(design)
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError("\n".join(f"design.json:1: {error}" for error in str(exc).splitlines())) from exc

    sources = {}

    def requirement(record):
        fields(record, kind=str, text=str, source=dict)
        require(record["kind"] in ("functional", "quality", "constraint"), "unknown requirement kind")
        source = record["source"]
        fields(source, type=str)
        match source["type"]:
            case "request":
                fields(source, sentence=str)
                require(source["sentence"] and source["sentence"] in request, "request sentence is missing")
                sources["request.md"] = source_file(folder, "request.md")
            case "file":
                fields(source, file=str, symbol=str)
                sources[source["file"]] = source_file(folder, source["file"])
            case "user":
                fields(source, at=str)
            case "guessed":
                pass
            case _:
                raise ValueError(f"unknown source type {source['type']!r}")

    def perspective(record):
        fields(record, applies=bool, why=str, **{"from": str})

    def references(values, allowed, label):
        for value in values:
            require(isinstance(value, str) and value in allowed, f"unknown {label} {value!r}")

    def finding(record):
        fields(record, perspective=str, parts=list, text=str)
        require(record["perspective"] in applicable, f"unknown or inapplicable perspective {record['perspective']!r}")
        require(
            "handled_by" in record and (record["handled_by"] is None or isinstance(record["handled_by"], str)),
            "handled_by: expected string or null",
        )
        require(record["parts"], "parts: expected at least one diagram part")
        for group in record["parts"]:
            require(isinstance(group, str), "parts: expected a string")
            references(group.split("+"), parts, "diagram part")

    def review(record):
        fields(record, at=str, perspectives=list, changed=list)
        references(record["perspectives"], applicable, "review perspective")
        references(record["changed"], parts, "changed part")

    def decision(record):
        fields(record, title=str, drivers=list, chosen=str, rejected=list, drawback=str)
        references(record["drivers"], req_ids, "driver")
        for rejected in record["rejected"]:
            fields(rejected, option=str, why=str)

    def spec_row(record):
        fields(record, requirement=str, source=str, checked_by=str)

    requirements = read_records(folder, "requirements.jsonl", requirement, "id")
    req_ids = {record["id"] for record in requirements}
    perspectives = read_records(folder, "perspectives.jsonl", perspective, "name")
    applicable = {record["name"] for record in perspectives if record["applies"]}
    return {
        "design": design,
        "request": request,
        "requirements": requirements,
        "perspectives": perspectives,
        "findings": read_records(folder, "findings.jsonl", finding, "id"),
        "reviews": read_records(folder, "reviews.jsonl", review),
        "decisions": read_records(folder, "decisions.jsonl", decision, "id"),
        "spec": read_records(folder, "spec.jsonl", spec_row, "id"),
        "parts": parts,
        "sources": sources,
    }


def diagram_parts(design):
    """Index the same boxes, arrows and steps across both versions for links and comments."""
    parts = {}

    def ids(view, kind, ident):
        return [diagram.part_id(f"{view}-{state}", kind, ident) for state in diagram.STATES]

    nodes = {node["id"]: node for node in design["containers"]["nodes"]}
    for ident, node in nodes.items():
        parts[f"box:{ident}"] = {
            "label": node["label"],
            "kind": "box",
            "ids": ids("c", "box", ident),
            "view": "containers",
            "icon": diagram.glyph(node["kind"]),
        }
    for edge in design["containers"].get("edges", []):
        ident = edge["id"]
        route = f"{nodes[edge['from']]['label']} to {nodes[edge['to']]['label']}"
        parts[f"edge:{ident}"] = {
            "label": f"{route}: {edge.get('label', '')}",
            "kind": "edge",
            "view": "containers",
            "ids": ids("c", "edge", ident),
        }
    for i, flow in enumerate(design["flows"], 1):
        view = f"flow{i}"
        flow_id = flow.get("id", view)
        for participant in flow["participants"]:
            parts[f"box:{participant['box']}"]["ids"].extend(ids(view, "box", participant["id"]))
        for step, number in zip(flow["steps"], diagram.step_numbers(flow), strict=True):
            ident = step["id"]
            part = {
                "label": f"{flow['name']}, step {number}: {step.get('label', '')}",
                "kind": "step",
                "ids": ids(view, "step", ident),
                "view": "flows",
                "mark": f"{view}:step:{ident}",
            }
            key = f"step:{flow_id}/{ident}"
            require(key not in parts, f"duplicate diagram part {key!r}")
            parts[key] = part
    return parts


def model(data):
    design = data["design"]
    marks = {}
    if data["reviews"]:
        for finding in data["findings"]:
            for key in dict.fromkeys(part for group in finding["parts"] for part in group.split("+")):
                target = data["parts"][key].get("mark", key.removeprefix("box:"))
                marks.setdefault(target, []).append([finding["id"], finding["text"], finding["perspective"]])
    try:
        layout = diagram.layout({**design, "findings": marks})
        containers = {s: diagram.svg_containers(layout, s) for s in diagram.STATES}
        flows = [
            {
                "name": flow["name"],
                "new": flow.get("in") == ["after"],
                "versions": {
                    s: diagram.svg_flow(flow, s, layout, f"flow{i}") if diagram.visible(flow, s) else ""
                    for s in diagram.STATES
                },
            }
            for i, flow in enumerate(design["flows"], 1)
        ]
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"design.json:1: {exc}") from exc
    result = {k: v for k, v in data.items() if k not in ("sources", "request", "design")}
    return {
        **result,
        **{k: design[k] for k in ("title", "summary", "scope", "accepted")},
        "requirements": [
            {**req, "wording": hashlib.sha256(req["text"].encode()).hexdigest()} for req in data["requirements"]
        ],
        "containers": containers,
        "flows": flows,
    }


def conversation(folder: Path) -> page.Conversation:
    return page.Conversation(
        folder,
        "conversation.jsonl",
        ".conversation-seen",
        ".server",
        ITEMS,
        "architect",
        "architect.py serve CHANGE --no-browser",
    )


def serve(folder: Path, port: int, open_browser: bool) -> None:
    model(read_folder(folder))
    conv = conversation(folder)

    class Handler(page.Handler):
        conversation = conv
        methods = (*ITEMS, "delete", "accept")

        def do_GET(self):
            if self.conversation_get():
                return
            url = urlsplit(self.path)
            try:
                if url.path in ASSETS:
                    name, kind = ASSETS[url.path]
                    self.send(200, (HERE / name).read_bytes(), kind + "; charset=utf-8")
                elif url.path == "/design.json":
                    self.send_json(model(read_folder(folder)))
                elif url.path == "/rev":
                    files = [*(folder / name for name in FILES), *(HERE / name for name, _ in ASSETS.values())]
                    rev = hashlib.sha256()
                    for path in files:
                        rev.update(read_text(path.parent, path.name).encode())
                    self.send(200, rev.hexdigest().encode(), "text/plain")
                elif url.path == "/source":
                    args = parse_qs(url.query)
                    path = args.get("file", [""])[0]
                    source = read_folder(folder)["sources"].get(path)
                    if source is None:
                        self.send_error(404)
                    else:
                        lines = source.read_text(encoding="utf-8").splitlines()
                        line = args.get("line", [""])[0]
                        if line.isdecimal() and 0 < int(line) <= len(lines):
                            n = int(line)
                            lines = [f"{i + 1:>5}  {lines[i]}" for i in range(max(0, n - 4), min(len(lines), n + 3))]
                        self.send(200, "\n".join(lines).encode(), "text/plain; charset=utf-8")
                else:
                    self.send_error(404)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                self.send(400, str(exc).encode(), "text/plain; charset=utf-8")

    with http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler) as server:
        url = f"http://127.0.0.1:{server.server_address[1]}/"
        conv.address.write_text(url, encoding="utf-8")
        print(f"Serving {folder} at {url}. Each action is printed as one JSON line.", flush=True)
        try:
            if open_browser:
                webbrowser.open(url)
            page.stop_like_ctrl_c()
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            conv.address.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    commands = {
        name: sub.add_parser(name, help=help_text)
        for name, help_text in (
            ("serve", "serve the live design"),
            ("check", "validate the change folder"),
            ("wait", "wait for new user actions"),
            ("reply", "reply in the conversation"),
            ("status", "mark an item with its current state"),
            ("pending", "list unfinished items"),
        )
    }
    for command in commands.values():
        command.add_argument("change", type=Path)
    commands["serve"].add_argument("--port", type=int, default=0)
    commands["serve"].add_argument("--no-browser", action="store_true")
    commands["wait"].add_argument("--timeout", type=float, default=600)
    commands["reply"].add_argument("text")
    commands["reply"].add_argument("--to", metavar="ID")
    commands["status"].add_argument("state", choices=page.STATES)
    commands["status"].add_argument("ids", nargs="+")
    args = parser.parse_args(argv)
    folder = args.change.expanduser().resolve()
    if not folder.is_dir():
        parser.error(f"{folder} is not a directory")
    conv = conversation(folder)
    try:
        if args.command == "check":
            model(read_folder(folder))
            print(f"Valid change folder: {folder}")
        elif args.command == "serve":
            serve(folder, args.port, not args.no_browser)
        elif args.command == "wait":
            return conv.wait(args.timeout)
        elif args.command == "reply":
            conv.reply(args.text, args.to)
        elif args.command == "status":
            conv.set_status(args.state, args.ids)
        else:
            conv.pending()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
