#!/usr/bin/env python3
"""Build each skill's scripts/better.pyz from src/better_ai/, and check that the committed ones match.

    python3 tools/build.py                      write skills/<skill>/scripts/better.pyz for every skill
    python3 tools/build.py --check [--base REF] rebuild and report every way the repository disagrees with the source
    python3 tools/build.py --compare            only compare a built tree with the source (no git, no stray scan)
    python3 tools/build.py --which HASH         print the commit whose sources have this source hash

    --src DIR      the folder that holds better_ai/ (default: <root>/src)
    --skills DIR   the folder that holds <skill>/scripts/better.pyz, to write or to compare (default: <root>/skills)
    --root DIR     the repository (default: the folder above tools/); only git steps use it

The build needs Python 3.12 or later: its zipapp sorts entries, so the bytes do not depend on the file system. The
.pyz it writes runs on Python 3.10. This file reads the source tree as data: it never imports or runs it, so a CI job
can run a trusted copy of it over a pull request's checkout. Only the standard library is used.
"""

from __future__ import annotations

import sys

MIN_PYTHON = (3, 12)
if sys.version_info < MIN_PYTHON:
    sys.stderr.write(
        f"build.py: needs Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or later, this is {sys.version_info[0]}."
        f"{sys.version_info[1]}. Run it with python3.12 or newer; the .pyz it writes runs on Python 3.10.\n"
    )
    raise SystemExit(2)

import argparse  # noqa: E402
import ast  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import platform  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402
import zipapp  # noqa: E402
import zipfile  # noqa: E402
from pathlib import Path  # noqa: E402

FIXED_MTIME = 946684800  # 2000-01-01T00:00:00Z, for every staged file and folder
INTERPRETER = "/usr/bin/env python3"
PACKAGE = "better_ai"
BUILD_INFO = f"{PACKAGE}/_build.json"
BASE_FIELDS = ("type", "at", "by")
HASH_LENGTH = 16
BUILD_COMMAND = "python3 tools/build.py"
SKIPPED_PARTS = {"__pycache__"}


class BuildError(Exception):
    """A problem with the source tree or skills.json: nothing is written."""


# ---------------------------------------------------------------- reading the source


def read_tree(src: Path) -> dict[str, bytes]:
    """Every file under <src>/better_ai as {"better_ai/<path>": bytes}. Symlinks are refused."""
    base = src / PACKAGE
    if not base.is_dir() or base.is_symlink():
        raise BuildError(f"{base}: not a folder. Pass --src with the folder that holds {PACKAGE}/")
    files: dict[str, bytes] = {}
    for folder, dirs, names in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in SKIPPED_PARTS)
        for d in dirs:
            if (Path(folder) / d).is_symlink():
                raise BuildError(f"{Path(folder) / d}: a symlink. The build does not follow symlinks; remove it")
        for name in sorted(names):
            path = Path(folder) / name
            if name.endswith(".pyc"):
                continue
            if path.is_symlink():
                raise BuildError(f"{path}: a symlink. The build does not follow symlinks; remove it")
            files[path.relative_to(src).as_posix()] = path.read_bytes()
    return files


def parse_config(raw: bytes) -> dict:
    try:
        cfg = json.loads(raw)
    except ValueError as err:
        raise BuildError(f"{PACKAGE}/skills.json: not JSON ({err})") from err
    problem = None
    if not isinstance(cfg, dict):
        problem = "must be an object"
    elif not isinstance(cfg.get("format_cutoff"), str):
        problem = "format_cutoff must be a string"
    elif not isinstance(cfg.get("shared"), list) or not all(isinstance(s, str) for s in cfg["shared"]):
        problem = "shared must be a list of paths"
    elif not isinstance(cfg.get("skills"), dict) or not cfg["skills"]:
        problem = "skills must be an object with at least one skill"
    else:
        for name, entry in cfg["skills"].items():
            if not isinstance(entry, dict) or not isinstance(entry.get("package"), str):
                problem = f"skills.{name} must be an object with a package"
    if problem is None:
        for entry in [*cfg["shared"], *(f"{PACKAGE}/{s['package']}/" for s in cfg["skills"].values())]:
            parts = entry.split("/")
            if entry.startswith("/") or ".." in parts or not entry.startswith(f"{PACKAGE}/") or "" in parts[:-1]:
                problem = f"path {entry!r} must be relative, under {PACKAGE}/, without .."
    if problem:
        raise BuildError(f"{PACKAGE}/skills.json: {problem}")
    return cfg


def skill_files(tree: dict[str, bytes], cfg: dict, skill: str) -> dict[str, bytes]:
    """The files of one skill's .pyz, before _build.json: the shared paths, its package and the root __main__.py."""
    entries = [*cfg["shared"], f"{PACKAGE}/{cfg['skills'][skill]['package']}/"]
    files: dict[str, bytes] = {}
    for entry in entries:
        if entry.endswith("/"):
            found = {k: v for k, v in tree.items() if k.startswith(entry)}
            if not found:
                raise BuildError(f"skills.json: {skill}: {entry}: no files. Fix the path or add the files")
            files.update(found)
        elif entry in tree:
            files[entry] = tree[entry]
        else:
            raise BuildError(f"skills.json: {skill}: {entry}: no such file. Fix the path or add the file")
    entry_point = f"{PACKAGE}/_entry.py"
    if entry_point not in files:
        raise BuildError(f"skills.json: {skill}: {entry_point} is not in shared; it becomes the root __main__.py")
    files["__main__.py"] = files[entry_point]
    return files


def source_hash(files: dict[str, bytes], skills_json: bytes) -> str:
    """Over the sorted paths and bytes of the files that go into the .pyz plus skills.json, never tools/build.py."""
    items = dict(files)
    items[f"{PACKAGE}/skills.json"] = skills_json
    digest = hashlib.sha256()
    for name in sorted(items):
        data = items[name]
        digest.update(name.encode() + b"\0" + str(len(data)).encode() + b"\0" + data)
    return digest.hexdigest()[:HASH_LENGTH]


class Source:
    """The source as data: its files, skills.json and the per-skill file sets, hashes and build info."""

    def __init__(self, tree: dict[str, bytes]):
        raw = tree.get(f"{PACKAGE}/skills.json")
        if raw is None:
            raise BuildError(f"{PACKAGE}/skills.json: missing")
        self.tree = tree
        self.raw_config = raw
        self.cfg = parse_config(raw)
        self.files = {s: skill_files(tree, self.cfg, s) for s in self.cfg["skills"]}
        self.hashes = {s: source_hash(f, raw) for s, f in self.files.items()}

    @classmethod
    def from_dir(cls, src: Path) -> Source:
        return cls(read_tree(src))

    def archive_files(self, skill: str) -> dict[str, bytes]:
        info = {
            "skill": skill,
            "package": self.cfg["skills"][skill]["package"],
            "hash": self.hashes[skill],
            "cutoff": self.cfg["format_cutoff"],
        }
        files = dict(self.files[skill])
        files[BUILD_INFO] = (json.dumps(info, sort_keys=True, indent=2) + "\n").encode()
        return files


# ---------------------------------------------------------------- building


def write_archive(files: dict[str, bytes], dest: Path) -> None:
    """Stage the files with one modification time and fixed permissions, then zipapp them with stored entries."""
    with tempfile.TemporaryDirectory(prefix="better-build-") as scratch:
        stage = Path(scratch) / "stage"
        stage.mkdir()
        folders: set[Path] = set()
        for name in sorted(files):
            path = stage / name
            for parent in path.parents:
                if parent == stage:
                    break
                folders.add(parent)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(files[name])
            os.chmod(path, 0o644)
            os.utime(path, (FIXED_MTIME, FIXED_MTIME))
        for folder in sorted(folders):
            os.chmod(folder, 0o755)
            os.utime(folder, (FIXED_MTIME, FIXED_MTIME))
        dest.parent.mkdir(parents=True, exist_ok=True)
        zipapp.create_archive(stage, dest, interpreter=INTERPRETER, compressed=False)


def pyz_path(skills: Path, skill: str) -> Path:
    return skills / skill / "scripts" / "better.pyz"


def build_into(source: Source, skills: Path) -> dict[str, Path]:
    out = {}
    for skill in source.cfg["skills"]:
        out[skill] = pyz_path(skills, skill)
        write_archive(source.archive_files(skill), out[skill])
    return out


# ---------------------------------------------------------------- reading a .pyz


def read_pyz(path: Path) -> tuple[dict[str, tuple], dict | None]:
    """The entries of a .pyz as {name: (crc, size, date_time, external_attr)} and its _build.json, if readable."""
    with zipfile.ZipFile(path) as z:
        entries = {i.filename: (i.CRC, i.file_size, i.date_time, i.external_attr) for i in z.infolist()}
        try:
            info = json.loads(z.read(BUILD_INFO))
        except (KeyError, ValueError):
            info = None
        return entries, info


def entry_hashes(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as z:
        return {i.filename: hashlib.sha256(z.read(i)).hexdigest() for i in z.infolist() if not i.is_dir()}


def differing_entries(a: Path, b: Path) -> list[str]:
    ea, _ = read_pyz(a)
    eb, _ = read_pyz(b)
    return sorted(n for n in set(ea) | set(eb) if ea.get(n) != eb.get(n))


# ---------------------------------------------------------------- schema steps


def _record_nodes(doc: dict):
    """The subschemas that describe one record type: the root, each $defs value, each root allOf `then`."""
    yield doc
    for value in (doc.get("$defs") or {}).values():
        if isinstance(value, dict):
            yield value
    for branch in doc.get("allOf") or []:
        if isinstance(branch, dict) and isinstance(branch.get("then"), dict):
            yield branch["then"]


def _node_types(node: dict) -> list[str]:
    prop = (node.get("properties") or {}).get("type")
    if not isinstance(prop, dict):
        return []
    if isinstance(prop.get("const"), str):
        return [prop["const"]]
    if isinstance(prop.get("enum"), list):
        return [v for v in prop["enum"] if isinstance(v, str)]
    return []


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def _prefixes(x_id) -> list[str]:
    if not isinstance(x_id, dict):
        return []
    if isinstance(x_id.get("prefix"), str):
        return [x_id["prefix"]]
    if isinstance(x_id.get("map"), dict):
        return sorted({v for v in x_id["map"].values() if isinstance(v, str)})
    return []


def bundled_schemas(files: dict[str, bytes]) -> dict[str, dict]:
    out = {}
    for name, data in files.items():
        if name.endswith(".schema.json") and "/schemas/" in name:
            try:
                doc = json.loads(data)
            except ValueError:
                continue
            if isinstance(doc, dict):
                out[name] = doc
    return out


def unit_kind_failures(skill: str, schemas: dict[str, dict]) -> list[tuple[str, str, str]]:
    """S58, per skill: a record type is declared for one place, and two record types do not share an id prefix."""
    places: dict[str, dict[str, tuple[str, ...]]] = {}
    prefixes: dict[str, dict[str, str]] = {}
    for name, doc in sorted(schemas.items()):
        place = tuple(sorted(doc.get("x-files") or ()))
        for node in _record_nodes(doc):
            for rtype in _node_types(node):
                places.setdefault(rtype, {})[name] = place
        for node in _walk(doc):
            if "x-id" not in node:
                continue
            types = _node_types(node) or ["?"]
            for prefix in _prefixes(node["x-id"]):
                for rtype in types:
                    prefixes.setdefault(prefix, {})[rtype] = name
    failures = []
    for rtype, where in sorted(places.items()):
        distinct = {p for p in where.values()}
        if len(distinct) > 1 or any(len(p) > 1 for p in distinct):
            detail = "; ".join(f"{n.rsplit('/', 1)[-1]}: {', '.join(p) or 'no x-files'}" for n, p in where.items())
            failures.append(
                (
                    "duplicate type",
                    f"{skill}: {rtype}",
                    f"the type maps to more than one file ({detail}); keep it in one file or rename one type",
                )
            )
    for prefix, owners in sorted(prefixes.items()):
        if len(owners) > 1:
            detail = ", ".join(f"{t} ({n.rsplit('/', 1)[-1]})" for t, n in sorted(owners.items()))
            failures.append(
                ("overlapping prefix", f"{skill}: {prefix}", f"claimed by {detail}; give each type its own prefix")
            )
    return failures


def base_field_failures(schemas: dict[str, dict]) -> list[tuple[str, str, str]]:
    """C6: every record type requires type, at and by. Page event schemas (`*-events.schema.json`) are input the
    server stamps, so they are not records."""
    failures = []
    for name, doc in sorted(schemas.items()):
        if name.endswith("-events.schema.json") or not doc.get("x-files"):
            continue
        for node in _record_nodes(doc):
            for rtype in _node_types(node):
                for field in BASE_FIELDS:
                    if field not in (node.get("required") or []):
                        failures.append(
                            ("base fields", name, f"type {rtype} does not require {field}: add it to `required`")
                        )
    return sorted(set(failures))


# ---------------------------------------------------------------- imports


def _module_exists(files: dict[str, bytes], dotted: str) -> bool:
    path = dotted.replace(".", "/")
    return f"{path}.py" in files or f"{path}/__init__.py" in files


def import_failures(skill: str, files: dict[str, bytes], tree: dict[str, bytes]) -> list[tuple[str, str, str]]:
    stdlib = set(sys.stdlib_module_names) | {"__future__"}
    failures = []
    for name in sorted(files):
        if not name.endswith(".py"):
            continue
        try:
            module = ast.parse(files[name], filename=name)
        except SyntaxError as err:
            failures.append(("import", f"{skill}: {name}", f"does not parse ({err.msg}, line {err.lineno})"))
            continue
        package = name.rsplit("/", 1)[0].replace("/", ".") if "/" in name else ""
        for node in ast.walk(module):
            wanted: list[str] = []
            if isinstance(node, ast.Import):
                wanted = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    parts = package.split(".") if package else []
                    keep = len(parts) - (node.level - 1)
                    if keep < 0:
                        failures.append(("import", f"{skill}: {name}", "relative import goes above the root"))
                        continue
                    wanted = [".".join([*parts[:keep], *(node.module.split(".") if node.module else [])])]
                else:
                    wanted = [node.module or ""]
            for dotted in wanted:
                top = dotted.split(".")[0]
                if not dotted:
                    continue
                if top != PACKAGE and top in stdlib:
                    continue
                if top != PACKAGE:
                    failures.append(
                        (
                            "import",
                            f"{skill}: {dotted}",
                            f"imported by {name}: neither standard library nor under src/{PACKAGE}/; "
                            "the build ships no third-party code",
                        )
                    )
                elif not _module_exists(files, dotted):
                    where = (
                        "is in src/ but not in this skill's .pyz: add its path to skills.json, or do not import it"
                        if _module_exists(tree, dotted)
                        else "does not exist under src/"
                    )
                    failures.append(("import", f"{skill}: {dotted}", f"imported by {name}: {where}"))
    return sorted(set(failures))


# ---------------------------------------------------------------- git


def git(root: Path, *args: str, check: bool = True, data: bytes | None = None) -> bytes:
    result = subprocess.run(["git", "-C", str(root), *args], input=data, capture_output=True)
    if check and result.returncode != 0:
        raise BuildError(f"git {' '.join(args)}: {result.stderr.decode(errors='replace').strip()}")
    return result.stdout if result.returncode == 0 else b""


def stray_failures(root: Path, source: Source) -> list[tuple[str, str, str]]:
    tracked = git(root, "ls-files", "-z", "--", "skills").decode().split("\0")
    allowed = {f"skills/{s}/scripts/better.pyz" for s in source.cfg["skills"]}
    failures = []
    for path in sorted(p for p in tracked if p):
        in_scripts = re.match(r"skills/[^/]+/scripts/", path)
        in_schemas = re.match(r"skills/[^/]+/schemas/", path)
        if (in_scripts or in_schemas) and path not in allowed:
            failures.append(("stray", path, "not produced by the build: remove it, or list it in skills.json"))
    return failures


def build_with_src_failures(root: Path, base: str) -> list[tuple[str, str, str]]:
    has_build = (
        subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", f"{base}:tools/build.py"], capture_output=True
        ).returncode
        == 0
    )
    if not has_build:
        return []  # the base has no build yet: this change introduces it
    names = git(root, "diff", "--name-only", "-z", base, "HEAD").decode().split("\0")
    if "tools/build.py" in names and any(n.startswith("src/") for n in names):
        return [
            (
                "build changed with src",
                "tools/build.py",
                "land the build change in its own PR: the base build is the reference for the source change",
            )
        ]
    return []


def tree_at(root: Path, commit: str) -> dict[str, bytes]:
    listing = git(root, "ls-tree", "-r", "-z", commit, "--", f"src/{PACKAGE}").decode().split("\0")
    wanted = {}
    for line in listing:
        if not line:
            continue
        meta, path = line.split("\t", 1)
        mode, kind, sha = meta.split()
        rel = path.removeprefix("src/")
        skipped = any(p in SKIPPED_PARTS for p in rel.split("/")) or rel.endswith(".pyc")
        if kind == "blob" and mode != "120000" and not skipped:
            wanted[rel] = sha
    out = git(root, "cat-file", "--batch", data="".join(f"{s}\n" for s in wanted.values()).encode())
    blobs: dict[str, bytes] = {}
    pos = 0
    for sha in wanted.values():
        end = out.index(b"\n", pos)
        _, _, size = out[pos:end].split()
        blobs[sha] = out[end + 1 : end + 1 + int(size)]
        pos = end + 1 + int(size) + 1
    return {rel: blobs[sha] for rel, sha in wanted.items()}


def which(root: Path, prefix: str) -> list[tuple[str, str, str]]:
    """(commit, skill, hash) for every commit, newest first, whose sources hash to a value starting with `prefix`."""
    found = []
    for commit in git(root, "rev-list", "HEAD", "--", "src").decode().split():
        try:
            source = Source(tree_at(root, commit))
        except BuildError:
            continue
        for skill, value in source.hashes.items():
            if value.startswith(prefix.lower()):
                found.append((commit, skill, value))
    return found


# ---------------------------------------------------------------- checks


def summary_text(source: Source, built: dict[str, Path], build_py: Path) -> str:
    lines = [
        "## better.pyz build",
        "",
        f"tools/build.py sha256: `{hashlib.sha256(build_py.read_bytes()).hexdigest()}`",
        "",
    ]
    for skill, path in built.items():
        lines += [f"### {skill}", "", f"source hash: `{source.hashes[skill]}`", "", "| entry | sha256 |", "|---|---|"]
        lines += [f"| {n} | `{h}` |" for n, h in sorted(entry_hashes(path).items())]
        lines.append("")
    return "\n".join(lines)


def run_check(args, source: Source, skills: Path, root: Path | None) -> list[tuple[str, str, str]]:
    failures: list[tuple[str, str, str]] = []
    with tempfile.TemporaryDirectory(prefix="better-check-") as scratch:
        first = build_into(source, Path(scratch) / "one")
        second = build_into(source, Path(scratch) / "two")
        for skill in source.cfg["skills"]:
            rel = f"skills/{skill}/scripts/better.pyz"
            if first[skill].read_bytes() != second[skill].read_bytes():
                diff = differing_entries(first[skill], second[skill]) or ["the archive bytes only, no entry"]
                failures.append(
                    (
                        "not reproducible",
                        rel,
                        f"two builds differ in: {', '.join(diff)}; remove what varies in the build",
                    )
                )
        for skill, built in first.items():
            rel = f"skills/{skill}/scripts/better.pyz"
            committed = pyz_path(skills, skill)
            if not committed.is_file():
                failures.append(("stale", rel, f"no committed build; run `{BUILD_COMMAND}` and commit it"))
                continue
            if committed.read_bytes() == built.read_bytes():
                continue
            try:
                _, info = read_pyz(committed)
            except zipfile.BadZipFile:
                info = None
            if not info or info.get("hash") != source.hashes[skill]:
                failures.append(("stale", rel, f"the source changed since the committed build; run `{BUILD_COMMAND}`"))
            else:
                failures.append(
                    (
                        "not reproducible across environments",
                        rel,
                        f"hash {source.hashes[skill]} matches but bytes differ in: "
                        f"{', '.join(differing_entries(committed, built)) or 'the archive bytes only'}; "
                        f"built here with Python {platform.python_version()} on {platform.platform()}",
                    )
                )
        if root is not None:
            failures += stray_failures(root, source)
            if args.base:
                failures += build_with_src_failures(root, args.base)
            else:
                print("note: no --base given, skipped the check that tools/build.py and src/ change in separate PRs")
        schemas_by_skill = {s: bundled_schemas(f) for s, f in source.files.items()}
        for skill, schemas in schemas_by_skill.items():
            failures += unit_kind_failures(skill, schemas)
        every = {}
        for schemas in schemas_by_skill.values():
            every.update(schemas)
        failures += base_field_failures(every)
        for skill, files in source.files.items():
            failures += import_failures(skill, files, source.tree)
        text = summary_text(source, first, Path(__file__))
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(text + "\n")
    else:
        print(text)
    return failures


# ---------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    os.environ["TZ"] = "UTC"
    if hasattr(time, "tzset"):
        time.tzset()
    here = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(prog="build.py", description="Build and check each skill's better.pyz.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="rebuild and report every disagreement with the source")
    mode.add_argument("--compare", action="store_true", help="compare a built tree with the source; no git needed")
    mode.add_argument("--which", metavar="HASH", help="print the commit whose sources have this source hash")
    parser.add_argument("--base", metavar="REF", help="with --check: the PR's base commit, for the build-and-src rule")
    parser.add_argument("--src", type=Path, help="the folder that holds better_ai/ (default: <root>/src)")
    parser.add_argument("--skills", type=Path, help="the folder of <skill>/scripts/better.pyz (default: <root>/skills)")
    parser.add_argument("--root", type=Path, default=here, help="the repository, for the git steps")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    src = (args.src or root / "src").resolve()
    skills = (args.skills or root / "skills").resolve()
    try:
        if args.which:
            found = which(root, args.which)
            for commit, skill, value in found:
                print(f"{commit} {skill} {value}")
            if not found:
                print(f"which: {args.which}: no commit has sources with that hash", file=sys.stderr)
            return 0 if found else 1
        source = Source.from_dir(src)
        if args.check or args.compare:
            failures = run_check(args, source, skills, root if args.check else None)
            for kind, subject, fix in failures:
                print(f"{kind}: {subject}: {fix}", file=sys.stderr)
            return 1 if failures else 0
        failures = [x for s, fl in source.files.items() for x in unit_kind_failures(s, bundled_schemas(fl))]
        if failures:
            for kind, subject, fix in failures:
                print(f"{kind}: {subject}: {fix}", file=sys.stderr)
            return 1
        for skill, path in build_into(source, skills).items():
            print(f"wrote {path} ({source.hashes[skill]})")
        return 0
    except BuildError as err:
        print(f"build.py: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
