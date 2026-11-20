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
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import diagram  # noqa: E402
import page  # noqa: E402

FILES = ("design.json", "requirements.json", "perspectives.json", "decisions.json", "spec.json", "request.md")
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
    for key, kind in schema.items():
        require(type(record.get(key)) is kind, f"{key}: expected {kind.__name__}")


def index(records):
    require(isinstance(records, list), "expected a list of records")
    result = {}
    for item in records:
        fields(item, id=str)
        ident = item["id"]
        require(ident and ident not in result, f"empty or duplicate ID {ident!r}")
        result[ident] = item
    return result


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
    data = {}
    for name in FILES:
        try:
            raw = (folder / name).read_text(encoding="utf-8")
            data[Path(name).stem] = raw if name == "request.md" else json.loads(raw)
        except (OSError, ValueError) as exc:
            raise ValueError(f"{name}: {exc}") from exc
    design = data["design"]
    try:
        fields(design, title=str, summary=str, scope=str, accepted=list, containers=dict, flows=list)
        require(set(design["accepted"]) <= set(TABS), "unknown accepted section")
        errors = diagram.validate(design)
        require(not errors, "; ".join(errors))
        for flow in design["flows"]:
            fields(flow, name=str)
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"design.json: {exc}") from exc

    sources = {}
    try:
        for req in index(data["requirements"]).values():
            fields(req, kind=str, text=str, source=dict)
            source = req["source"]
            if source == {"guessed": True}:
                continue
            fields(source, file=str)
            target = sources[source["file"]] = source_file(folder, source["file"])
            if source["file"] == "request.md":
                fields(source, sentence=str)
                require(source["sentence"] and source["sentence"] in data["request"], "request sentence is missing")
            if "line" in source:
                fields(source, line=int)
                require(
                    0 < source["line"] <= len(target.read_text(encoding="utf-8").splitlines()), "invalid source line"
                )
            if "symbol" in source:
                fields(source, symbol=str)
    except (AttributeError, KeyError, OSError, TypeError, ValueError) as exc:
        raise ValueError(f"requirements.json: {exc}") from exc

    req_ids = {r["id"] for r in data["requirements"]}
    try:
        for decision in index(data["decisions"]).values():
            fields(decision, title=str, drivers=list, chosen=str, alternatives=list, drawback=str)
            require(set(decision["drivers"]) <= req_ids, f"{decision['id']}: unknown driver")
            for alternative in decision["alternatives"]:
                fields(alternative, option=str, why=str)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"decisions.json: {exc}") from exc

    try:
        parts = diagram_parts(design)
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"design.json: {exc}") from exc
    try:
        fields(data["perspectives"], perspectives=list)
        perspectives = index(data["perspectives"]["perspectives"])
        for perspective in perspectives.values():
            fields(perspective, name=str, applies=bool, why=str, source=str, findings=list)
            if "columns" in perspective:
                fields(perspective["columns"], finding=str, response=str)
            require(perspective["applies"] or not perspective["findings"], "findings require an applicable perspective")
            for finding in index(perspective["findings"]).values():
                fields(finding, parts=list, finding=str, response=str)
                if "category" in finding:
                    fields(finding, category=str)
                require(finding["parts"], f"{finding['id']}: expected at least one part")
                for group in finding["parts"]:
                    require(
                        isinstance(group, list) and group and set(group) <= parts.keys(),
                        f"{finding['id']}: unknown or ambiguous diagram part in {group!r}",
                    )
        review = data["perspectives"].get("review")
        if review is not None:
            fields(review, changes=list, rerun=list)
            require(all(isinstance(change, str) for change in review["changes"]), "expected change descriptions")
            require(
                set(review["rerun"]) <= {k for k, p in perspectives.items() if p["applies"]}, "invalid review scope"
            )
        else:
            require(not any(p["findings"] for p in perspectives.values()), "findings require a completed review")
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"perspectives.json: {exc}") from exc

    try:
        require(isinstance(data["spec"], list), "expected a list of spec rows")
        for row in data["spec"]:
            fields(row, origin=str, count=int, example=str, source=str)
            require(row["count"] > 0, "expected a positive rule count")
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"spec.json: {exc}") from exc
    return {**data, "parts": parts, "sources": sources}


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
    counts = Counter(step["id"] for flow in design["flows"] for step in flow["steps"])
    for i, flow in enumerate(design["flows"], 1):
        view = f"flow{i}"
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
            parts[part["mark"]] = part
            if counts[ident] == 1:
                parts[f"step:{ident}"] = part
    return parts


def model(data):
    design = data["design"]
    marks = {}
    for perspective in data["perspectives"]["perspectives"]:
        for finding in perspective["findings"]:
            for key in dict.fromkeys(part for group in finding["parts"] for part in group):
                target = data["parts"][key].get("mark", key.removeprefix("box:"))
                badge = [finding["id"], finding["finding"], perspective["id"]]
                if badge not in marks.setdefault(target, []):
                    marks[target].append(badge)
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
                        rev.update(path.read_bytes())
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
