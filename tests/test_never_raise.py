"""No script of any skill ever shows a traceback or drops a request, whatever it is fed or whatever fails inside it.

One harness for the whole class. It finds every script with a `main` under skills/*/scripts/ and every page server's
request handler itself, so a script added later is checked without a line here (the commands this file runs a new
script with are asked for by a test that fails until they are added). For each it:

  - checks that `main` is wrapped by `schema.never_raise`, and injects exceptions (RuntimeError, ZeroDivisionError,
    KeyError, RecursionError, MemoryError) into every function the script's commands call: none escapes, and one
    that reaches the wrapper is a single stderr line and exit code 1;
  - injects the same into every function a request calls on each page server: the answer is never a dropped request
    or a traceback in the server's log; a failure is a 500 with one line, or for the JSON-RPC endpoint the error
    object;
  - feeds each loader every file of its folder as unreadable, bad UTF-8, raw garbage, nested 300, 2,000 and 50,000
    deep, and holding a lone surrogate: the answer is an error entry, never an exception;
  - puts a lone surrogate in every string and every key of the example records of every kind of file: schema.py
    reports it, and what a page shows from the record can be written as UTF-8.
"""

import ast
import contextlib
import copy
import http.client
import http.server
import importlib.util
import inspect
import io
import json
import os
import re
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sweep  # noqa: E402
import test_architect_formats as architects  # noqa: E402
import test_board_formats as boards  # noqa: E402
import test_page as pages  # noqa: E402
import test_show_schema as shows  # noqa: E402

ROOT = HERE.parent
SKILLS = ROOT / "skills"
EXCEPTIONS = (RuntimeError, KeyError, RecursionError, MemoryError)
DEPTHS = (300, 2000, 50000)
SURROGATE = "a\ud800b"
# The steps of a request that page.Handler's guard is made of: patching one to fail takes the guard itself away.
GUARDS = ("guarded", "setup", "handle", "finish")


def is_guard(owner, name: str) -> bool:
    """Whether `owner.name` is page.Handler's own guard step, by identity: a class of a script that has a method of
    the same name is not."""
    page = sys.modules.get("page")
    handler = getattr(page, "Handler", None)
    return name in GUARDS and owner is handler


# What every script calls from the standard library, where a script's own closures cannot be patched by name.
STDLIB = [
    (Path, "read_text"),
    (Path, "read_bytes"),
    (Path, "write_text"),
    (Path, "stat"),
    (json, "loads"),
    (json, "dumps"),
]


# ---------------------------------------------------------------- discovery


def all_scripts() -> list:
    return sorted(SKILLS.glob("*/scripts/**/*.py"))


def top_level_problems(path: Path) -> list:
    """Why a script is neither a library nor a program. A library's top level only imports, defines and assigns (and
    may put its own folder on sys.path). A program has, besides that, one `if __name__ == "__main__":` block that calls
    one wrapped entry point. Any other top-level statement runs code with no guard."""
    tree = ast.parse(path.read_text())
    block = main_block(tree)
    problems = []
    for node in tree.body:
        if node is block or isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AsyncFunctionDef)):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue  # a docstring
        if isinstance(node, ast.Expr) and ast.unparse(node.value).startswith("sys.path.insert("):
            continue
        problems.append(f"line {node.lineno}: top-level code outside a guarded program: {ast.unparse(node)[:60]}")
    return [*problems, *(entry_of(path, tree)[1] if block is not None else [])]


def main_block(tree: ast.Module):
    """The `if __name__ == "__main__":` block of a module, or None."""
    for node in tree.body:
        if isinstance(node, ast.If) and ast.unparse(node.test).replace("'", '"') == '__name__ == "__main__"':
            return node
    return None


def entry_of(path: Path, tree: ast.Module | None = None) -> tuple:
    """(the name of the function a script's `__main__` block calls, the problems with it): the block must do nothing
    but call one module-level function, as `sys.exit(entry())` or `entry()`, and that function must be wrapped by
    never_raise, whatever its name."""
    tree = tree or ast.parse(path.read_text())
    block = main_block(tree)
    if block is None:
        return None, []
    problems, name = [], None
    only = block.body[0] if len(block.body) == 1 else None
    call = only.value if isinstance(only, ast.Expr) and isinstance(only.value, ast.Call) else None
    if call is not None and ast.unparse(call.func) == "sys.exit" and len(call.args) == 1:
        call = call.args[0] if isinstance(call.args[0], ast.Call) else None
    if call is None or not isinstance(call.func, ast.Name) or call.args or call.keywords:
        problems.append("its __main__ block is not just a call of one function (module-level script?)")
    else:
        name = call.func.id
        defined = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
        if not defined:
            problems.append(f"{name} is not a module-level function")
        elif not any("never_raise" in ast.unparse(d) for d in defined[0].decorator_list):
            problems.append(f"{name} is not wrapped by never_raise")
    return name, problems


def scripts_with_main() -> list:
    """Every script with a `__main__` block, whatever its entry point is called."""
    return [p for p in all_scripts() if main_block(ast.parse(p.read_text())) is not None]


def server_classes(path: Path) -> tuple:
    """(the classes of a script that subclass page.Handler, the classes that are request handlers any other way)."""
    tree = ast.parse(path.read_text())
    classes = {n.name: [ast.unparse(b) for b in n.bases] for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    own = path.name == "page.py"
    outside: set = set()
    changed = True
    while changed:  # a class deriving from one that is a handler another way is one too
        changed = False
        for name, bases in classes.items():
            if name in outside or (own and name == "Handler"):
                continue
            if any(b.endswith("RequestHandler") or b in outside for b in bases):
                outside.add(name)
                changed = True
    paged = [n for n, bases in classes.items() if "page.Handler" in bases and n not in outside]
    return paged, sorted(outside)


def scripts_with_a_handler() -> list:
    return [p for p in all_scripts() if server_classes(p)[0]]


MODULES: dict = {}


def module_of(path: Path):
    """A script as its own skill ships it: its folder is on sys.path, as when it runs."""
    if path not in MODULES:
        sys.path.insert(0, str(path.parent))
        name = f"never_raise_{path.parent.parent.name}_{path.stem}"
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        entry, _ = entry_of(path)
        if entry:
            module.entry = getattr(module, entry)  # what the harness runs, whatever it is called
        MODULES[path] = module
    return MODULES[path]


def name_of(path: Path) -> str:
    return f"{path.parent.parent.name}/{path.name}"


def schema_module():
    return module_of(SKILLS / "architect-better" / "scripts" / "schema.py")


# ---------------------------------------------------------------- the commands of each script, on a fresh folder


def architect_commands(root: Path) -> list:
    folder = architects.make_folder(root)
    perspective = architects.read(folder, "perspectives.jsonl")[0]["id"]
    return [
        ["check", folder],
        ["specs", folder, "--out", root / "specs.md"],
        ["review", folder, "--perspectives", perspective],
        ["reply", folder, "hello"],
        ["status", folder, "seen", "m-1"],
        ["pending", folder],
        ["wait", folder, "--timeout", "0.1"],
    ]


def diagram_commands(root: Path) -> list:
    design = root / "design.json"
    design.write_text(json.dumps(architects.design()), encoding="utf-8")
    return [
        ["check", design],
        ["render", design, "--out", root / "svg"],
        ["register", "--out", root / "register.html"],
    ]


def board_folder(root: Path) -> Path:
    folder = root / "board"
    folder.mkdir()
    boards.support(folder)
    return folder


def board_commands(root: Path) -> list:
    folder = board_folder(root)
    return [
        ["check", folder],
        ["snapshot", folder, "--out", root / "snapshot.html"],
        ["pending", folder],
        ["reply", folder, "hello"],
        ["status", folder, "seen", "m-1"],
        ["wait", folder, "--timeout", "0.1"],
    ]


def show_folder(root: Path) -> Path:
    folder = root / "slides"
    folder.mkdir()
    (folder / "spec.json").write_text(json.dumps(shows.full_spec()), encoding="utf-8")
    return folder


def show_commands(root: Path) -> list:
    folder = show_folder(root)
    spec = folder / "spec.json"
    return [
        ["check", spec],
        ["render", spec, "--out", root / "o.html"],
        ["render", spec, "--format", "text"],
        ["render", spec, "--format", "md", "--ascii"],
        ["render", spec, "--format", "text", "--screen-reader"],
        ["pending", folder],
        ["reply", folder, "hello"],
        ["status", folder, "seen", "m-1"],
        ["wait", folder, "--timeout", "0.1"],
    ]


def canvas_folder(root: Path) -> Path:
    folder = root / "versions"
    folder.mkdir()
    for label in "ab":
        (folder / f"{label}.html").write_text(f"<html><body><p>{label}</p></body></html>", encoding="utf-8")
    return folder


def canvas_commands(root: Path) -> list:
    folder = canvas_folder(root)
    return [
        ["show", folder / "a.html", folder / "b.html", "--out", folder / "page.html"],
        ["pending", folder],
        ["reply", folder, "hello"],
        ["status", folder, "seen", "m-1"],
        ["wait", folder, "--timeout", "0.1"],
    ]


def folder_with_a_reply(skill: str, root: Path) -> Path:
    """A folder holding a conversation log with one agent reply, written the way the skill's own script writes it."""
    folder = {"show-better": show_folder, "design-better": canvas_folder}[skill](root)
    module = module_of(SKILLS / skill / "scripts" / {"show-better": "show.py", "design-better": "canvas.py"}[skill])
    with contextlib.redirect_stdout(io.StringIO()):
        module.conversation(folder).reply("hello", None)
    return folder


PROGRAMS = {
    "architect-better": "architect.py",
    "research-better": "board.py",
    "show-better": "show.py",
    "design-better": "canvas.py",
}
SCHEMA_FOLDERS = {
    "architect-better": lambda root: architects.make_folder(root),
    "research-better": board_folder,
    "show-better": lambda root: folder_with_a_reply("show-better", root),
    "design-better": lambda root: folder_with_a_reply("design-better", root),
}


def schema_commands(skill: str, root: Path) -> list:
    return [["check", SCHEMA_FOLDERS[skill](root)]]


COMMANDS = {
    "architect-better/architect.py": architect_commands,
    "architect-better/diagram.py": diagram_commands,
    "research-better/board.py": board_commands,
    "show-better/show.py": show_commands,
    "design-better/canvas.py": canvas_commands,
}


def commands_of(path: Path, root: Path) -> list:
    if path.name == "schema.py":
        return schema_commands(path.parent.parent.name, root)
    return COMMANDS[name_of(path)](root)


# ---------------------------------------------------------------- running a command in process


class Strict:
    """A stream that refuses what a real one refuses: stdout is UTF-8 and strict, so a lone surrogate fails to print
    as it does in a terminal (io.StringIO takes anything); stderr escapes what it cannot hold, as Python's does."""

    def __init__(self, errors: str = "strict"):
        self.raw = io.BytesIO()
        self.stream = io.TextIOWrapper(self.raw, encoding="utf-8", errors=errors, write_through=True)

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def getvalue(self) -> str:
        self.stream.flush()
        return self.raw.getvalue().decode("utf-8")


def invoke(module, argv: list):
    """(exit code, stdout, stderr, the exception that escaped) of `module.main` on `argv`, on streams like a real
    terminal's."""
    out, err = Strict(), Strict("backslashreplace")
    escaped, code = None, 0
    main = module.entry
    takes_argv = bool(inspect.signature(getattr(main, "__wrapped__", main)).parameters)
    arguments = [str(a) for a in argv]
    patched = mock.patch.object(sys, "argv", ["script", *arguments])
    with patched, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(arguments) if takes_argv else main()
        except SystemExit as stop:
            code = stop.code
        except BaseException as error:  # noqa: BLE001 - what escapes is what these tests are about
            escaped = error
    return code, out.getvalue(), err.getvalue(), escaped


def watched(module) -> dict:
    """id of a code object -> (owner, name) of each function and method that can be patched by name: the script's, the
    shared schema.py's and page.py's."""
    page = getattr(module, "page", None)  # the modules this script itself imported
    owners = [module, page]
    if "architect-better" in module.__name__:  # schema.py is identical in every skill: its functions are tried once
        owners += [getattr(module, "schema", None), getattr(page, "schema", None)]
    found = {id(getattr(o, n).__code__): (o, n) for o, n in STDLIB}  # by identity: equal code objects compare equal
    for owner in owners:
        for name, value in list(vars(owner).items()) if owner is not None else []:
            if inspect.isfunction(value) and value.__module__ == owner.__name__ and name != "entry":
                found[id(value.__code__)] = (owner, name)
            elif inspect.isclass(value) and value.__module__ == owner.__name__:
                for attr, member in list(vars(value).items()):
                    if inspect.isfunction(member) and not attr.startswith(("__", "do_")) and not is_guard(value, attr):
                        found[id(member.__code__)] = (value, attr)
    return found


def called(module, run, extra: dict | None = None) -> list:
    """The (owner, name) of each watched function (and each STDLIB one) that `run()` calls, in any thread, `main`
    itself left out."""
    table = {**watched(module), **(extra or {})}
    seen = set()

    def profile(frame, event, arg):
        if event == "call" and id(frame.f_code) in table:
            seen.add(table[id(frame.f_code)])

    threading.setprofile(profile)
    sys.setprofile(profile)
    try:
        run()
    finally:
        sys.setprofile(None)
        threading.setprofile(None)
    return sorted((t for t in seen if t[1] != "main"), key=lambda t: (getattr(t[0], "__name__", ""), t[1]))


def raising(target, error):
    """Patch `target` (owner, name) to raise `error`. A check hook is called through schema.HOOKS, so that is patched."""
    owner, name = target
    hooks = getattr(owner, "HOOKS", None)
    if isinstance(hooks, dict):
        original = getattr(owner, name, None)
        for hook_name, function in hooks.items():
            if function is original:
                return mock.patch.dict(hooks, {hook_name: mock.Mock(side_effect=error())})
    return mock.patch.object(owner, name, side_effect=error())


WRAPPER_LINE = re.compile(r"^[\w. ]+: (?:could not be \w+: .+|nested too deeply)$")


def one_stderr_line(text: str) -> bool:
    return len(text.strip().splitlines()) == 1


# ---------------------------------------------------------------- the wrapper


class Wrapper(unittest.TestCase):
    def wrapped(self, raised):
        @schema_module().never_raise("thing", "read")
        def entry():
            raise raised

        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            return entry(), err.getvalue()

    def test_any_exception_is_exit_1_and_one_line(self):
        for error in (RuntimeError("r"), ZeroDivisionError("z"), KeyError("k"), MemoryError(), ValueError("v")):
            with self.subTest(error=type(error).__name__):
                self.assertEqual(self.wrapped(error), (1, f"thing: could not be read: {type(error).__name__}\n"))

    def test_too_deep_says_so(self):
        self.assertEqual(self.wrapped(RecursionError()), (1, "thing: nested too deeply\n"))

    def test_an_environment_error_keeps_its_reason_and_the_file_and_the_verb_is_the_commands(self):
        schema = schema_module()

        @schema.never_raise("thing", {"serve": "served", "": "checked"})
        def entry(argv):
            raise OSError(98, "Address already in use", "/some/where")

        for argv, line in (
            (["serve", "x"], "thing: could not be served: Address already in use (/some/where)\n"),
            (["--flag", "other"], "thing: could not be checked: Address already in use (/some/where)\n"),
        ):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(entry(argv), 1)
            self.assertEqual(err.getvalue(), line)

    def test_a_server_that_cannot_listen_says_so_in_the_commands_own_words(self):
        busy = socket.socket()
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        port = busy.getsockname()[1]
        try:
            for script, command, build in (
                ("architect-better/architect.py", "serve", architect_serving),
                ("research-better/board.py", "watch", board_serving),
            ):
                with self.subTest(script=script), tempfile.TemporaryDirectory() as d:
                    folder = build(Path(d))[0][0]
                    code, out, err, escaped = invoke(
                        module_of(SKILLS / script.split("/")[0] / "scripts" / script.split("/")[1]),
                        [command, folder, "--port", port, "--no-browser"],
                    )
                    self.assertIsNone(escaped)
                    self.assertEqual(code, 1)
                    self.assertRegex(err.strip(), r"^[\w ]+: could not be served: .*(in use|ddress)")
                    self.assertEqual(len(err.strip().splitlines()), 1)
        finally:
            busy.close()

    def test_a_corrupt_seen_or_address_file_is_a_file_error_with_the_wrappers_line_not_a_usage_error(self):
        for path in scripts_with_a_handler():
            for broken in ("seen", "address"):
                with self.subTest(script=name_of(path), broken=broken), tempfile.TemporaryDirectory() as d:
                    module = module_of(path)
                    args, folder = HANDLERS[name_of(path)][1](Path(d))
                    conv = module.conversation(folder)
                    conv.address.write_text("not an address" if broken == "address" else "http://127.0.0.1:1/")
                    conv.seen.write_text("x" if broken == "seen" else "0")
                    code, out, err, escaped = invoke(module, ["wait", folder, "--timeout", "0.2"])
                    self.assertIsNone(escaped)
                    self.assertEqual(code, 1)
                    self.assertNotIn("usage", err)
                    self.assertTrue(any(WRAPPER_LINE.match(line) for line in err.splitlines()), err)

    def test_exit_codes_and_interrupts_pass_through(self):
        for raised in (SystemExit(2), SystemExit("x"), KeyboardInterrupt()):
            with self.subTest(raised=repr(raised)), self.assertRaises(type(raised)):
                self.wrapped(raised)

    def test_every_script_that_runs_as_a_program_calls_one_wrapped_entry_point(self):
        scripts = scripts_with_main()
        self.assertGreaterEqual(len(scripts), 9)  # architect, diagram, board, show, canvas, four schema
        for path in scripts:
            with self.subTest(script=name_of(path)):
                entry, problems = entry_of(path)
                self.assertEqual(problems, [])
                self.assertTrue(hasattr(getattr(module_of(path), entry), "__wrapped__"))

    def test_every_file_under_scripts_is_a_library_or_a_program_with_a_wrapped_entry_point(self):
        self.assertGreaterEqual(len(all_scripts()), 13)
        for path in all_scripts():
            with self.subTest(script=name_of(path)):
                self.assertEqual(top_level_problems(path), [])

    def test_every_request_handler_is_a_page_handler(self):
        for path in all_scripts():
            with self.subTest(script=name_of(path)):
                self.assertEqual(server_classes(path)[1], [], "subclass page.Handler, which guards every request")

    def test_every_script_with_a_main_has_commands_to_run_here(self):
        for path in scripts_with_main():
            if path.name != "schema.py":
                self.assertIn(name_of(path), COMMANDS, f"{name_of(path)} has a main: add its commands to COMMANDS")
        for path in scripts_with_a_handler():
            self.assertIn(name_of(path), HANDLERS, f"{name_of(path)} serves a page: add it to HANDLERS")


class Injected(unittest.TestCase):
    """An exception raised in any function a command calls, or in what it reads, never escapes `main`."""

    def test_no_exception_escapes_a_command_and_one_that_reaches_the_wrapper_is_one_line(self):
        for path in scripts_with_main():
            module = module_of(path)
            with tempfile.TemporaryDirectory() as d:
                count = len(commands_of(path, Path(d)))
            for index in range(count):
                with tempfile.TemporaryDirectory() as d:
                    argv = commands_of(path, Path(d))[index]
                    targets = called(module, lambda module=module, argv=argv: invoke(module, argv))
                pairs = [(target, error) for target in targets for error in EXCEPTIONS]
                for target, error in sweep.cases(pairs, key=lambda p: p[1]):
                    with self.subTest(script=name_of(path), command=str(argv[0]), at=target[1], error=error.__name__):
                        with tempfile.TemporaryDirectory() as d:
                            argv = commands_of(path, Path(d))[index]
                            with raising(target, error):
                                code, out, err, escaped = invoke(module, argv)
                        self.assertIsNone(escaped, f"{type(escaped).__name__} escaped main")
                        self.assertNotIn("Traceback", err)
                        wrapper_lines = [line for line in err.splitlines() if WRAPPER_LINE.match(line)]
                        if wrapper_lines:  # the exception reached the wrapper: that is one line and exit 1
                            self.assertEqual(len(wrapper_lines), 1, err)
                            self.assertEqual(code, 1)


# ---------------------------------------------------------------- the page servers


class Captured(Exception):
    pass


REAL_SERVER = http.server.ThreadingHTTPServer


def served_page(folder: Path) -> Path:
    path = folder / "page.html"
    path.write_text("<html><body><p>x</p></body></html>", encoding="utf-8")
    return path


def architect_serving(root: Path) -> tuple:
    folder = architects.make_folder(root)
    return (folder, 0, False), folder


def board_serving(root: Path) -> tuple:
    folder = board_folder(root)
    return (folder, 0, False, 0.0), folder


def show_serving(root: Path) -> tuple:
    folder = show_folder(root)
    return (served_page(folder), 0, False), folder


def canvas_serving(root: Path) -> tuple:
    folder = canvas_folder(root)
    return (served_page(folder), 0, False), folder


# script -> (the function that starts the server, what it is given on a fresh folder, the events the page sends)
HANDLERS = {
    "architect-better/architect.py": ("serve", architect_serving, "architect"),
    "research-better/board.py": ("watch", board_serving, "board"),
    "show-better/show.py": ("serve", show_serving, "show"),
    "design-better/canvas.py": ("serve", canvas_serving, "canvas"),
}
PATHS = [
    "/",
    "/index.html",
    "/listening",
    "/events?after=0",
    "/wait?after=0",
    "/board.json",
    "/design.json",
    "/rev",
    "/source?file=x.md&line=1",
    "/files/0/a.css",
    "/architect.js",
    "/nope",
]
RPC_FAILS = '"code": -32603'


def request(port: int, method: str, path: str, body: bytes | None = None) -> tuple:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
    headers = {}
    if method == "POST":
        headers = {"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{port}"}
    try:
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


def rpc(method: str, params: dict) -> bytes:
    return json.dumps({"jsonrpc": "2.0", "id": 7, "method": method, "params": params}).encode()


def requests_of(page_name: str) -> list:
    """Every request the harness makes: each GET path, each event the page may send, and a few that are wrong."""
    sent = [("GET", p, None) for p in PATHS]
    sent += [("POST", "/rpc", rpc(method, params)) for method, params in pages.VALID[page_name].items()]
    sent += [("POST", "/rpc", b"{"), ("POST", "/rpc", rpc("nope", {})), ("POST", "/rpc", b"[" * 50000)]
    return sent


class ServedPage:
    """One page's request handler, found by running the script's serve function with a server that only hands the
    handler class back, then served for real from this process."""

    def __init__(self, path: Path, root: Path, broken: tuple | None = None):
        self.module = module_of(path)
        function, build, self.page = HANDLERS[name_of(path)]
        args, self.folder = build(root)
        with contextlib.redirect_stdout(io.StringIO()):
            self.module.conversation(self.folder).reply("hello", None)  # so a request has an event to answer with
        if broken is not None:  # a file of the folder that is not what it should be: (its name, how, what)
            put_in(self.folder / broken[0], broken[1], broken[2])

        class Fake:
            def __init__(self, address, handler):
                holder.append(handler)
                raise Captured

        holder: list = []
        patched = mock.patch.object(http.server, "ThreadingHTTPServer", Fake)
        with patched, contextlib.redirect_stdout(io.StringIO()), contextlib.suppress(Captured):
            getattr(self.module, function)(*args)
        self.handler = holder[0]
        self.server = REAL_SERVER(("127.0.0.1", 0), self.handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, args=(0.01,), daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    def extra(self) -> dict:
        return {
            id(m.__code__): (self.handler, n)
            for n, m in vars(self.handler).items()
            if inspect.isfunction(m) and not n.startswith(("__", "do_"))
        }


class Serving(unittest.TestCase):
    def answers(self, served: ServedPage, sent: list):
        """Each request's (status, body); a dropped connection fails the test."""
        with contextlib.redirect_stdout(Strict()):  # a page's event is printed for the agent
            return [request(served.port, method, path, body) for method, path, body in sent]

    def check_answers(self, served, sent, answers, err, injected=False):
        self.assertNotIn("Traceback", err.getvalue())
        for (method, path, body), (status, data) in zip(sent, answers, strict=True):
            with self.subTest(request=f"{method} {path}"):
                if status == 500:
                    self.assertTrue(one_stderr_line(data.decode()), data)
                if path == "/rpc" and status == 200 and body not in (None,):
                    self.assertIn("jsonrpc", json.loads(data))

    def test_every_handler_is_found_and_answers_every_request(self):
        for path in scripts_with_a_handler():
            with self.subTest(script=name_of(path)), tempfile.TemporaryDirectory() as d:
                served = ServedPage(path, Path(d))
                sent = requests_of(served.page)
                try:
                    with contextlib.redirect_stderr(io.StringIO()) as err:
                        answers = self.answers(served, sent)
                finally:
                    served.close()
                self.check_answers(served, sent, answers, err)

    def test_no_exception_in_what_a_request_calls_drops_it_or_shows_a_traceback(self):
        for path in scripts_with_a_handler():
            with tempfile.TemporaryDirectory() as d:
                served = ServedPage(path, Path(d))
                sent = requests_of(served.page)
                try:
                    by_target: dict = {}  # each function, and the requests that call it
                    for one in sent:
                        send = lambda served=served, one=one: self.answers(served, [one])  # noqa: E731
                        for target in called(served.module, send, served.extra()):
                            by_target.setdefault(target, []).append(one)
                    pairs = [(target, own, error) for target, own in by_target.items() for error in EXCEPTIONS]
                    for target, own, error in sweep.cases(pairs, key=lambda p: p[2]):
                        with self.subTest(script=name_of(path), at=target[1], error=error.__name__):
                            with raising(target, error), contextlib.redirect_stderr(io.StringIO()) as err:
                                answers = self.answers(served, own)
                            self.check_answers(served, own, answers, err)
                finally:
                    served.close()


def raw_exchange(port: int, data: bytes, how: str) -> bytes:
    """Send bytes and then close the connection politely, or reset it; what the server sent back."""
    sock = socket.create_connection(("127.0.0.1", port), timeout=10)
    try:
        sock.sendall(data)
        if how == "reset":
            time.sleep(0.05)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            return b""
        sock.shutdown(socket.SHUT_WR)
        chunks = []
        while chunk := sock.recv(65536):
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        sock.close()


CUT_OFF = [
    b"GET /dash",
    b"GET /events?after=0 HTTP/1.1\r\nHost: 127.0.0.1\r\n",
    b"POST /rpc HTTP/1.1\r\nHost: 127.0.0.1\r\nOrigin: http://127.0.0.1\r\nContent-Type: application/json\r\n"
    b"Content-Length: 100\r\n\r\n" + b'{"a"',
    b"\x00\xff\r\n\r\n",
]


class RequestLifecycle(unittest.TestCase):
    """What happens outside do_GET and do_POST: a client that is cut off or reset mid-request, and an answer that
    fails after it has started. None prints a traceback, and the stream never holds a second status line."""

    def test_a_client_cut_off_or_reset_mid_request_leaves_no_traceback_and_the_server_answers_on(self):
        for path in scripts_with_a_handler():
            with self.subTest(script=name_of(path)), tempfile.TemporaryDirectory() as d:
                served = ServedPage(path, Path(d))
                try:
                    with contextlib.redirect_stderr(io.StringIO()) as err:
                        for data in CUT_OFF:
                            for how in ("close", "reset"):
                                raw_exchange(served.port, data, how)
                        time.sleep(0.3)  # the server's threads finish what they were doing
                        status, _ = request(served.port, "GET", "/listening")
                finally:
                    served.close()
                self.assertNotIn("Traceback", err.getvalue())
                self.assertEqual(status, 200)

    def test_an_answer_that_fails_after_its_headers_are_out_closes_the_stream_without_a_second_status_line(self):
        for path in scripts_with_a_handler():
            with self.subTest(script=name_of(path)), tempfile.TemporaryDirectory() as d:
                served = ServedPage(path, Path(d))

                class Late(served.handler):
                    def do_GET(self):
                        self.send(200, b"x" * 20, "text/plain")
                        raise RuntimeError("after the body began")

                server = REAL_SERVER(("127.0.0.1", 0), Late)
                threading.Thread(target=server.serve_forever, args=(0.01,), daemon=True).start()
                try:
                    with contextlib.redirect_stderr(io.StringIO()) as err:
                        got = raw_exchange(
                            server.server_address[1], b"GET / HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n", "close"
                        )
                finally:
                    server.shutdown()
                    server.server_close()
                    served.close()
                self.assertNotIn("Traceback", err.getvalue())
                self.assertEqual(got.count(b"HTTP/1."), 1, got[:300])
                self.assertTrue(got.endswith(b"x" * 20))


SERVED_CORRUPTIONS = [
    ("bad UTF-8", "bytes", b'{"id": "\xff\xfe"}\n'),
    ("an object 2,000 deep", "bytes", b'{"a":' * 2000 + b"1" + b"}" * 2000 + b"\n"),
    ("a lone surrogate in the first string", "surrogate", 0),
    ("a lone surrogate in the last key", "surrogate", -1),
]


class ServedBrokenFiles(unittest.TestCase):
    def answers_quietly(self, served, sent):
        with contextlib.redirect_stdout(io.StringIO()):
            return [request(served.port, m, p, b) for m, p, b in sent]

    def test_a_page_answers_every_request_without_a_500_when_a_file_it_reads_is_broken(self):
        for path in scripts_with_a_handler():
            with tempfile.TemporaryDirectory() as d:
                probe = ServedPage(path, Path(d))
                files = [f for f in folder_files(probe.folder) if f.suffix in (".json", ".jsonl")]
                probe.close()
            sent = requests_of(HANDLERS[name_of(path)][2])
            pairs = [(relative, corruption) for relative in files for corruption in SERVED_CORRUPTIONS]
            for relative, (label, how, content) in sweep.cases(pairs, key=[lambda p: p[1][0], lambda p: str(p[0])]):
                with self.subTest(script=name_of(path), file=str(relative), broken=label):
                    with tempfile.TemporaryDirectory() as d:
                        served = ServedPage(path, Path(d), (relative, how, content))
                        try:
                            with contextlib.redirect_stderr(io.StringIO()) as err:
                                answers = self.answers_quietly(served, sent)
                        finally:
                            served.close()
                    self.assertNotIn("Traceback", err.getvalue())
                    self.assertEqual(
                        [(m, p) for (m, p, _), (status, _) in zip(sent, answers, strict=True) if status >= 500], []
                    )


# ---------------------------------------------------------------- the loaders, on files that are not what they should be

# skill -> (script, how to build a folder, the loader's answer for a folder)
LOADERS = {
    "architect-better": ("architect.py", lambda root: architects.make_folder(root), lambda m, f: m.load(f)),
    "research-better": ("board.py", board_folder, lambda m, f: m.load(f)),
}
CONVERSATIONS = {
    "architect-better": ("architect.py", lambda root: architects.make_folder(root)),
    "research-better": ("board.py", board_folder),
    "show-better": ("show.py", lambda root: folder_with_a_reply("show-better", root)),
    "design-better": ("canvas.py", lambda root: folder_with_a_reply("design-better", root)),
}


def places(value) -> list:
    """Each string value and each key of a JSON value, as (kind, path to the object holding it, its key or index),
    walked without recursion."""
    found, pending = [], [(value, ())]
    while pending:
        item, path = pending.pop()
        if isinstance(item, dict):
            for key, child in item.items():
                found.append(("key", path, key))
                pending.append((child, (*path, key)))
        elif isinstance(item, list):
            pending.extend((child, (*path, i)) for i, child in enumerate(item))
        elif isinstance(item, str) and path:
            found.append(("value", path[:-1], path[-1]))
    return found


def with_a_surrogate(record, place):
    """A copy of `record` with a lone surrogate in the string, or in the key, at `place`; and where it is."""
    record = copy.deepcopy(record)
    kind, path, key = place
    holder = record
    for step in path:
        holder = holder[step]
    if kind == "value":
        holder[key] = SURROGATE
        return record, (*path, key)
    renamed = {(key + "\ud800" if k == key else k): v for k, v in holder.items()}
    holder.clear()
    holder.update(renamed)
    return record, (*path, key + "\ud800")


def garbage() -> list:
    """(label, bytes) of a file that is not what it should be."""
    found = [("bad utf-8", b'{"id": "\xff\xfe"}\n'), ("raw", b"{\n"), ("nul", b"\x00\x00"), ("empty", b"")]
    for depth in DEPTHS:
        found.append((f"list {depth} deep", b"[" * depth + b"]" * depth + b"\n"))
        found.append((f"object {depth} deep", b'{"a":' * depth + b"1" + b"}" * depth + b"\n"))
        found.append(
            (f"object holding a list {depth} deep", b'{"id":"x","type":"t","a":' + b"[" * depth + b"]" * depth + b"}\n")
        )
    return found


def folder_files(folder: Path) -> list:
    return sorted(p.relative_to(folder) for p in folder.rglob("*") if p.is_file() and ".git" not in p.parts)


def put_in(path: Path, how: str, content):
    if how == "unreadable":
        path.chmod(0)
    elif how == "directory":
        path.unlink()
        path.mkdir()
    elif how == "surrogate":
        if path.suffix not in (".json", ".jsonl"):
            return False
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        first = json.loads(lines[0]) if path.suffix == ".jsonl" else json.loads(text)
        mine = [p for p in places(first)]
        if not mine:
            return False
        changed, _ = with_a_surrogate(first, mine[content % len(mine)])
        lines[0 if path.suffix == ".jsonl" else 0] = json.dumps(changed, ensure_ascii=True)
        path.write_text("\n".join(lines) + "\n" if path.suffix == ".jsonl" else lines[0], encoding="utf-8")
    else:
        path.write_bytes(content)
    return True


def corruptions(skip_unreadable: bool = os.geteuid() == 0) -> list:
    found = [(f"garbage: {label}", "bytes", data) for label, data in garbage()]
    found += [
        ("a lone surrogate in the first string", "surrogate", 0),
        ("a lone surrogate in the last key", "surrogate", -1),
    ]
    found += [("a directory instead of the file", "directory", None)]
    if not skip_unreadable:
        found.append(("unreadable", "unreadable", None))
    return found


# Functions a loader calls whose failure leaves the folder's answer whole: they only add to it (a mtime, a clock).
HARMLESS: set = set()


class Loaders(unittest.TestCase):
    def broken(self, build, relative: Path, how: str, content, module=None):
        """A fresh folder with `relative` made into `how`; the folder. With `module`, the folder has a conversation
        log first."""
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        folder = build(Path(d.name))
        if module is not None and not (folder / relative).exists():
            with contextlib.redirect_stdout(io.StringIO()):
                module.conversation(folder).reply("hello", None)
        target = folder / relative
        self.addCleanup(lambda: target.exists() and not target.is_dir() and target.chmod(0o644))
        put_in(target, how, content)
        return folder

    def assert_clean(self, answer):
        self.assertIsInstance(answer, dict)
        json.dumps(answer, allow_nan=False)
        json.dumps(answer, ensure_ascii=False, allow_nan=False).encode("utf-8")

    def test_a_loader_answers_with_an_error_entry_for_every_file_that_is_not_what_it_should_be(self):
        for skill, (script, build, load) in LOADERS.items():
            module = module_of(SKILLS / skill / "scripts" / script)
            with tempfile.TemporaryDirectory() as d:
                files = folder_files(build(Path(d)))
            pairs = [(relative, corruption) for relative in files for corruption in corruptions()]
            for relative, (label, how, content) in sweep.cases(pairs, key=lambda p: p[1][0]):
                with self.subTest(skill=skill, file=str(relative), broken=label):
                    folder = self.broken(build, relative, how, content)
                    answer = load(module, folder)
                    self.assert_clean(answer)
                    if how in ("surrogate", "unreadable") or (how == "bytes" and content):
                        self.assertTrue(answer["errors"] or relative.name == "conversation.jsonl", "no error entry")
                    code, out, err, escaped = invoke(module, ["check", folder])
                    self.assertIsNone(escaped)
                    self.assertNotIn("Traceback", err)
                    self.assertFalse(any(WRAPPER_LINE.match(line) for line in err.splitlines()), err)

    def test_a_loader_never_raises_whatever_fails_inside_it(self):
        """Not only file content: an exception in any function a loader calls is an error entry, so the page shows
        its errors band and not a failure."""
        for skill, (script, build, load) in LOADERS.items():
            module = module_of(SKILLS / skill / "scripts" / script)
            with tempfile.TemporaryDirectory() as d:
                folder = build(Path(d))
                targets = called(module, lambda module=module, load=load, folder=folder: load(module, folder))
            targets = [
                t
                for t in targets
                if not (t[1] in ("load", "collect") or t[0] is not module and t[1] in ("loads", "dumps"))
            ]  # not the loader itself; json is used by the answer's own encoding
            pairs = [(target, error) for target in targets for error in EXCEPTIONS]
            for target, error in sweep.cases(pairs, key=lambda p: p[1]):
                with self.subTest(skill=skill, at=target[1], error=error.__name__):
                    with tempfile.TemporaryDirectory() as d:
                        folder = build(Path(d))
                        with raising(target, error):
                            answer = load(module, folder)
                    self.assert_clean(answer)
                    self.assertTrue(answer["errors"] or target[1] in HARMLESS, "no error entry")

    def test_the_conversation_log_never_raises_whatever_it_holds(self):
        for skill, (script, build) in CONVERSATIONS.items():
            module = module_of(SKILLS / skill / "scripts" / script)
            for label, how, content in corruptions():
                with self.subTest(skill=skill, broken=label):
                    folder = self.broken(build, Path("conversation.jsonl"), how, content, module)
                    conv = module.conversation(folder)
                    self.assertIsInstance(conv.events(), list)
                    for command in ("pending", "reply"):
                        code, out, err, escaped = invoke(
                            module, [command, folder, *(["hi"] if command == "reply" else [])]
                        )
                        self.assertIsNone(escaped)
                        self.assertNotIn("Traceback", err)
                        writing_to_a_file_that_cannot_be_written = command == "reply" and how in (
                            "unreadable",
                            "directory",
                        )
                        if not writing_to_a_file_that_cannot_be_written:  # that one's reason is the wrapper's line
                            self.assertFalse(any(WRAPPER_LINE.match(line) for line in err.splitlines()), err)


# ---------------------------------------------------------------- a lone surrogate in every string and key of every kind

PAGE_SKILLS = {
    "architect": "architect-better",
    "canvas": "design-better",
    "show": "show-better",
    "board": "research-better",
}
AT = "2026-11-21T10:00:00Z"


def example_records() -> list:
    """(skill, label, the file name the record would have, the record) for the examples of every kind of file."""
    found = []
    for kind in architects.KINDS:
        for title, record in architects.examples(kind):
            found.append(("architect-better", f"{kind}: {title}", kind, record))
    for kind, items in boards.EXAMPLES.items():
        sample = kind.replace("<id>", "X-1").replace("<agent>", "agent")
        for item in items:
            found.append(("research-better", f"{kind}: {item['label']}", sample, item["record"]))
    found.append(("show-better", "a spec of every kind of slide", "spec.json", shows.full_spec()))
    for kind in shows.KIND_OK:
        found.append(("show-better", f"a {kind} slide", "spec.json", shows.spec_of(shows.visual(kind))))
    for page_name, events in pages.VALID.items():
        for method, params in events.items():
            record = {"type": method, "at": AT, "by": "user", **params}
            found.append((PAGE_SKILLS[page_name], f"{page_name} {method} event", "conversation.jsonl", record))
    return found


def encodable(text: str) -> bool:
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


class Surrogates(unittest.TestCase):
    """A string or a key holding a lone surrogate (JSON `\\ud800`) is not text: it cannot be written as UTF-8, so no
    page or terminal can show it. schema.py says so, and what a page shows of the record can be written."""

    def docs(self, skill: str) -> dict:
        return schema_module().load_schemas(SKILLS / skill / "schemas")

    def test_the_examples_are_enough_to_cover_every_kind(self):
        kinds = {(skill, sample) for skill, _, sample, _ in example_records()}
        self.assertGreaterEqual(len(kinds), 19)

    def test_every_string_and_every_key_of_every_example_that_holds_a_surrogate_is_reported_and_stripped(self):
        schema = schema_module()
        cache: dict = {}
        examples = example_records()
        for skill, _label, sample, _record in examples:
            docs = cache.setdefault(skill, self.docs(skill))
            self.assertTrue(schema._match(Path("/folder") / sample, docs), f"{skill} {sample}: no schema")
        every = [(*example, place) for example in examples for place in places(example[3])]
        keys = [lambda c: (c[0], c[2]), lambda c: c[4][0]]  # each kind of file, and string or key
        for skill, label, sample, record, place in sweep.cases(every, key=keys):
            docs = cache[skill]
            found = schema._match(Path("/folder") / sample, docs)
            changed, at = with_a_surrogate(record, place)
            with self.subTest(skill=skill, example=label, place=schema._render(at)):
                problems = schema.validate_record(changed, [doc for _, doc in found], docs, None)
                self.assertIn(schema._render(at), {p.field for p in problems})
                errors = [schema.Error("f", 1, p.field, p.message) for p in problems]
                self.assertTrue(all(encodable(str(e)) for e in errors))
                shown = schema.strip_invalid(changed, errors)
                json.dumps(shown, ensure_ascii=False).encode("utf-8")

    def test_a_file_holding_one_is_an_error_line_and_nothing_else(self):
        schema = schema_module()
        cache: dict = {}
        for skill, label, sample, record in sweep.cases(example_records(), key=[lambda e: e[0], lambda e: e[2]]):
            docs = cache.setdefault(skill, self.docs(skill))
            for place in (places(record)[0], places(record)[-1]):
                changed, at = with_a_surrogate(record, place)
                with self.subTest(skill=skill, example=label), tempfile.TemporaryDirectory() as d:
                    path = Path(d) / sample
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(changed) + "\n", encoding="utf-8")
                    errors = schema.check_file(path, docs, {})
                    self.assertTrue(any(schema._render(at) == e.field for e in errors), [str(e) for e in errors])
                    self.assertTrue(all(encodable(str(e)) for e in errors))

    def test_a_surrogate_at_every_place_of_the_first_record_of_every_file_is_a_clean_exit_for_check_pending_and_load(
        self,
    ):
        for skill, build in SCHEMA_FOLDERS.items():
            script = PROGRAMS[skill]
            module = module_of(SKILLS / skill / "scripts" / script)
            checker = module_of(SKILLS / skill / "scripts" / "schema.py")
            with tempfile.TemporaryDirectory() as d:
                files = [f for f in folder_files(build(Path(d))) if f.suffix in (".json", ".jsonl")]
            for relative in files:
                with tempfile.TemporaryDirectory() as d:
                    folder = build(Path(d))
                    text = (folder / relative).read_text(encoding="utf-8")
                    count = len(places(json.loads(text.splitlines()[0] if relative.suffix == ".jsonl" else text)))
                for index in sweep.cases(range(count), key=lambda i: 0 if i == 0 else 2 if i == count - 1 else 1):
                    with self.subTest(skill=skill, file=str(relative), place=index), tempfile.TemporaryDirectory() as d:
                        folder = build(Path(d))
                        put_in(folder / relative, "surrogate", index)
                        for runner, command in ((module, "check"), (module, "pending"), (checker, "check")):
                            code, out, err, escaped = invoke(runner, [command, folder])
                            self.assertIsNone(escaped)
                            self.assertFalse(any(WRAPPER_LINE.match(line) for line in err.splitlines()), err)
                        if skill in LOADERS:
                            load = LOADERS[skill][2]
                            self.assert_clean(load(module, folder))

    def assert_clean(self, answer):
        json.dumps(answer, ensure_ascii=False, allow_nan=False).encode("utf-8")

    def test_each_scripts_check_command_reports_one_in_a_folder_without_a_traceback(self):
        for skill, build in SCHEMA_FOLDERS.items():
            with tempfile.TemporaryDirectory() as d:
                folder = build(Path(d))
                files = [p for p in folder_files(folder) if p.suffix in (".json", ".jsonl")]
                target = next((p for p in files if p.name != "conversation.jsonl"), files[0])
                put_in(folder / target, "surrogate", 0)
                for script in ("schema.py",):
                    run = subprocess.run(
                        [sys.executable, "-I", str(SKILLS / skill / "scripts" / script), "check", str(folder)],
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    with self.subTest(skill=skill, script=script, file=str(target)):
                        self.assertEqual(run.returncode, 1, run.stderr[-300:])
                        self.assertNotIn("Traceback", run.stderr)
                        self.assertNotIn("could not be", run.stderr)
                        self.assertRegex(run.stdout, r"not text|ud800")

    def test_show_check_reports_one_in_any_part_of_a_spec_as_a_spec_error(self):
        module = module_of(SKILLS / "show-better" / "scripts" / "show.py")
        spec = shows.full_spec()
        for place in sweep.cases(places(spec), key=lambda p: p[0]):
            changed, at = with_a_surrogate(spec, place)
            with self.subTest(place=place[1:]), tempfile.TemporaryDirectory() as d:
                path = Path(d) / "spec.json"
                path.write_text(json.dumps(changed), encoding="utf-8")
                code, out, err, escaped = invoke(module, ["check", path])
                self.assertIsNone(escaped)
                self.assertEqual(code, 1)
                self.assertTrue(encodable(out + err))
                self.assertNotRegex(err, WRAPPER_LINE.pattern.replace("^", "(?m)^"))


# ---------------------------------------------------------------- nesting far past the recursion limit, by command


def nest(kind: str, depth: int) -> str:
    return ("[" * depth + "]" * depth) if kind == "list" else ('{"a":' * depth + "1" + "}" * depth)


def traceback_of(*args) -> str:
    """The command's last traceback line, or '' when it printed none."""
    done = subprocess.run([sys.executable, "-I", *map(str, args)], capture_output=True, text=True, timeout=120)
    return done.stderr.strip().splitlines()[-1] if "Traceback" in done.stderr else ""


def spec_with(field_in_panel: bool, nested: str) -> str:
    """A slides spec holding `nested` in the free `document` field, or as the body of a text panel."""
    panel = {"headline": "A clear point here.", "kind": "text", "body": ["x"]}
    text = json.dumps({"type": "slides", "title": "T", "document": "@@", "panels": [panel]})
    if field_in_panel:
        panel["body"] = "@@"
        text = json.dumps({"type": "slides", "title": "T", "panels": [panel]})
    return text.replace('"@@"', nested)


class DeepInput(unittest.TestCase):
    def commands(self, root: Path, nested: str) -> dict:
        """The commands to run, by label, each on a file or folder that holds `nested` in one place."""
        show = SKILLS / "show-better" / "scripts"
        research = SKILLS / "research-better" / "scripts"
        commands = {}
        for where, in_panel in (("document", False), ("body", True)):
            path = root / f"{where}.json"
            path.write_text(spec_with(in_panel, nested))
            commands[f"show check {where}"] = [show / "show.py", "check", path]
            commands[f"show render {where}"] = [show / "show.py", "render", path, "--out", root / "o.html"]
            commands[f"schema check {where}"] = [show / "schema.py", "check", path]
        slides = root / "slides"
        slides.mkdir()
        (slides / "conversation.jsonl").write_text('{"type":"note","id":"m-1","text":' + nested + "}\n")
        commands["show pending"] = [show / "show.py", "pending", slides]

        board = root / "board"
        board.mkdir()
        boards.support(board)
        (board / "questions" / "Q-deep.json").write_text('{"type":"question","id":"Q-deep","x":' + nested + "}")
        commands["board check"] = [research / "board.py", "check", board]
        commands["board snapshot"] = [research / "board.py", "snapshot", board, "--out", board / "o.html"]
        commands["schema check board"] = [research / "schema.py", "check", board]
        return commands

    def test_no_command_prints_a_traceback_for_a_deeply_nested_file(self):
        pairs = [(depth, kind) for depth in (300, 950, *DEPTHS[1:]) for kind in ("list", "dict")]
        for depth, kind in sweep.cases(pairs, key=[lambda p: p[0], lambda p: p[1]]):
            with self.subTest(depth=depth, kind=kind), tempfile.TemporaryDirectory() as d:
                commands = self.commands(Path(d), nest(kind, depth))
                problems = {label: traceback_of(*args) for label, args in commands.items()}
                self.assertEqual({k: v for k, v in problems.items() if v}, {})


# ---------------------------------------------------------------- numbers a renderer cannot take


class IntegerTyping(unittest.TestCase):
    """An integral float is not an integer: a renderer's range(3.0) fails, so a field the schemas call an integer
    refuses 3.0 and the check, not the renderer, says so."""

    def test_every_integer_the_schemas_name_refuses_an_integral_float(self):
        schema = schema_module()
        found = 0
        for path in sorted(SKILLS.glob("*/schemas/*.schema.json")):
            docs = schema.load_schemas(path.parent)
            pending = [json.loads(path.read_text(encoding="utf-8"))]
            while pending:
                node = pending.pop()
                if isinstance(node, dict):
                    kind = node.get("type")
                    if kind == "integer" or (isinstance(kind, list) and "integer" in kind):
                        found += 1
                        with self.subTest(schema=path.name, node=str(node)[:60]):
                            problems = schema.validate_instance(3.0, {**node, "type": kind}, docs)
                            self.assertTrue(problems, "3.0 passes as an integer")
                    pending.extend(node.values())
                elif isinstance(node, list):
                    pending.extend(node)
        self.assertGreater(found, 5)

    def test_a_spec_that_check_accepts_with_an_integer_made_a_float_renders(self):
        module = module_of(SKILLS / "show-better" / "scripts" / "show.py")
        spec = shows.full_spec()
        whole, pending = [], [(spec, ())]
        while pending:  # each place that holds a whole number, as (the path to its holder, its key)
            item, path = pending.pop()
            pairs = item.items() if isinstance(item, dict) else enumerate(item) if isinstance(item, list) else ()
            for key, child in pairs:
                if isinstance(child, int) and not isinstance(child, bool):
                    whole.append((path, key))
                else:
                    pending.append((child, (*path, key)))
        self.assertTrue(whole)
        for path, key in whole:
            changed = copy.deepcopy(spec)
            holder = changed
            for step in path:
                holder = holder[step]
            holder[key] = float(holder[key])
            with self.subTest(place=(*path, key)), tempfile.TemporaryDirectory() as d:
                target = Path(d) / "spec.json"
                target.write_text(json.dumps(changed), encoding="utf-8")
                code, out, err, escaped = invoke(module, ["check", target])
                if not code:  # check accepts it: the renderer must take it
                    code, out, err, escaped = invoke(module, ["render", target, "--out", Path(d) / "o.html"])
                    self.assertFalse(code, err)
                    self.assertFalse(any(WRAPPER_LINE.match(line) for line in err.splitlines()), err)


if __name__ == "__main__":
    unittest.main()
