"""Pair one tab and bind each permission answer to the driver's in-memory copy of a tool call."""

import hashlib
import json
import os
import re
import secrets
import sys
import threading
from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path


class Pairing:
    def __init__(self, origin):
        self.origin = origin
        self.lock = threading.Lock()
        self.token = self.secret = ""

    def issue(self):
        with self.lock:
            self.secret = ""
            self.token = secrets.token_urlsafe(32)
            return self.token

    @staticmethod
    def matches(provided, expected):
        return bool(
            expected and isinstance(provided, str) and provided.isascii() and secrets.compare_digest(provided, expected)
        )

    def exchange(self, token, origin):
        with self.lock:
            if origin != self.origin or not self.matches(token, self.token):
                raise ValueError("opened elsewhere")
            self.token = ""
            self.secret = secrets.token_urlsafe(32)
            return self.secret

    def valid(self, secret, origin):
        with self.lock:
            return origin == self.origin and self.matches(secret, self.secret)


# Only these literal shell words are accepted outside the single-quoted input.
WORD = re.compile(r"[A-Za-z0-9_./-]+|'[^'\n]*'")
IDENT = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")
FLAGS = {
    "reply": {"--by", "--to", "--state"},
    "status": {"--by", "--text"},
    "pending": set(),
    "add": {"--by", "--for", "--id"},
    "set": {"--by", "--for", "--unset"},
}


def verb_command(command, unit, archive, record_verbs):
    """Recognize a small grammar directly; never interpret or normalize arbitrary shell syntax."""
    if not isinstance(command, str) or "\0" in command or "\r" in command:
        return False
    head, sep, body = command.partition("\n")
    if sep:
        head, marker, tag = head.rpartition(" <<'")
        if not marker or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,31}'", tag):
            return False
        lines = body.removesuffix("\n").split("\n")
        if lines[-1] != tag[:-1] or tag[:-1] in lines[:-1]:
            return False
    else:
        literal = re.fullmatch(r"(.+) <<<'[^'\n]*'", head)
        if literal:
            head = literal[1]
    words = []
    while head:
        match = WORD.match(head)
        if not match:
            return False
        words.append(match[0].strip("'"))
        head = head[match.end() :]
        if head and not head.startswith(" "):
            return False
        head = head.lstrip(" ")
    if len(words) < 4:
        return False
    interpreter, script, verb, target, *args = words
    if (
        interpreter != sys.executable
        or script != str(archive)
        or target != str(unit)
        or verb not in ({"pending", "reply", "status"} | (set(record_verbs) & {"add", "set"}))
    ):
        return False
    positional = []
    it = iter(args)
    for arg in it:
        if IDENT.fullmatch(arg):
            positional.append(arg)
        elif arg not in FLAGS[verb] or (arg != "--text" and not IDENT.fullmatch(next(it, ""))):
            return False
    if verb == "status":
        return len(positional) >= 2 and positional[0] in {"seen", "asked", "working", "done", "accepted"}
    return len(positional) == int(verb in {"add", "set"})


def display(value):
    # ASCII JSON spelling makes controls, bidi overrides and non-ASCII lookalikes explicit.
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False)
        .replace("<", r"\u003c")
        .replace(">", r"\u003e")
        .replace("&", r"\u0026")
        .replace("\x7f", r"\u007f")
    )


def repeatable_read(tool, args):
    # Match only a known read schema. An unfamiliar operation always needs its own answer.
    if tool != "Read" or not isinstance(args, dict) or set(args) != {"file_path"}:
        return False
    name = args["file_path"]
    if not isinstance(name, str) or not Path(name).is_absolute():
        return False
    paths = (Path(name), Path(name).resolve())
    protected = {
        "appdata",
        "application support",
        "claude",
        "codex",
        "opencode",
        "opencode.json",
        "opencode.jsonc",
        "factory",
        "cursor",
        "droid",
        "devin",
        "better-ai",
    }
    if any(part.startswith(".") or part.casefold() in protected for path in paths for part in path.parts):
        return False
    for variable in (
        "CLAUDE_CONFIG_DIR",
        "CODEX_HOME",
        "CURSOR_CONFIG_DIR",
        "OPENCODE_CONFIG",
        "OPENCODE_CONFIG_DIR",
        "FACTORY_HOME",
        "FACTORY_CONFIG_DIR",
        "DEVIN_CONFIG_DIR",
    ):
        value = os.environ.get(variable)
        if value:
            config = Path(value).expanduser().absolute()
            if any(path.is_relative_to(root) for path in paths for root in (config, config.resolve())):
                return False
    return True


@dataclass
class Request:
    wire_id: object
    tool: str
    arguments: str
    options: tuple
    callback: Callable[[str, str], Future[bool]]
    sending: bool = False


class ApprovalGate:
    def __init__(self, unit_path, *, archive=None, record_verbs=()):
        self.unit = Path(unit_path).absolute()
        self.archive = Path(archive).absolute() if archive else None
        self.record_verbs = tuple(record_verbs)
        self.digest = self._hash()
        self.lock = threading.RLock()
        self.pending = {}
        self.outcomes = {}
        self.grants = set()
        self.notice = ""
        self.last_outcome = ""

    def _hash(self):
        if self.archive is not None:
            try:
                return hashlib.sha256(self.archive.read_bytes()).digest()
            except OSError:
                return None
        return None

    def receive(self, event, callback):
        with self.lock:
            try:
                tool = display(event.tool)
                args = display(event.arguments)
                if not isinstance(event.tool, str) or not event.tool or len(tool) + len(args) > 131072:
                    raise ValueError
                tool_id = getattr(event, "tool_id", None)
                repeatable = repeatable_read(tool_id, event.arguments)
            except (ValueError, TypeError, RecursionError, OSError, RuntimeError):
                callback("deny", "Cannot display the full tool request")
                return
            if "allow_once" not in event.options:
                callback("deny", "Request has no allow-once option")
                return
            options = ("allow_once", "allow_session", "deny") if repeatable else ("allow_once", "deny")
            rid = secrets.token_urlsafe(24)
            item = self.pending[rid] = Request(event.request_id, tool, args, options, callback)
            if repeatable and (tool, args) in self.grants:
                self._send(rid, item, "allow_once", "Allowed earlier for this session")
            elif (
                tool_id == "Bash"
                and isinstance(event.arguments, dict)
                and set(event.arguments) == {"command"}
                and self.digest is not None
                and verb_command(event.arguments["command"], self.unit, self.archive, self.record_verbs)
                and self._hash() == self.digest
            ):
                self._send(rid, item, "allow_once", "Approved page command", page_command=True)

    def snapshot(self):
        with self.lock:
            return {
                "notice": self.notice,
                "last_outcome": self.last_outcome,
                "approvals": [
                    {"id": rid, "tool": item.tool, "arguments": item.arguments, "options": list(item.options)}
                    for rid, item in self.pending.items()
                    if not item.sending
                ],
            }

    def waiting(self):
        with self.lock:
            return bool(self.pending)

    def _get(self, rid):
        if not isinstance(rid, str) or rid not in self.pending:
            raise ValueError(self.outcomes.get(rid, "Unknown approval") if isinstance(rid, str) else "Unknown approval")
        if self.pending[rid].sending:
            raise ValueError("Approval answer is being delivered")
        return self.pending[rid]

    def _finish(self, rid, reason):
        del self.pending[rid]
        self.last_outcome = self.outcomes[rid] = reason

    def _send(self, rid, item, choice, reason, *, page_command=False):
        item.sending = True

        def settled(future):
            try:
                delivered = future.result() is True
            except Exception:
                delivered = False
            with self.lock:
                if rid not in self.pending:
                    return
                if delivered and choice == "allow_session":
                    self.grants.add((item.tool, item.arguments))
                if delivered and page_command:
                    self.notice = "The page agent can run its page commands without asking."
                self._finish(rid, reason if delivered else "expired")

        try:
            delivery = item.callback("deny" if choice == "deny" else "allow_once", reason)
            delivery.add_done_callback(settled)
        except Exception:
            if rid in self.pending:
                self._finish(rid, "expired")

    def answer(self, rid, choice):
        with self.lock:
            item = self._get(rid)
            if choice not in item.options:
                raise ValueError("Invalid approval choice")
            allowed = choice != "deny"
            reason = (
                "allowed for this session"
                if choice == "allow_session"
                else ("allowed once" if allowed else "denied by the user")
            )
            self._send(rid, item, choice, reason)

    def closed(self, event):
        with self.lock:
            for rid, item in list(self.pending.items()):
                if event.request_id == item.wire_id:
                    self._finish(rid, event.text or event.outcome or "expired")

    def close(self, reason):
        with self.lock:
            self.grants.clear()
            self.notice = ""
            unanswered = [item for item in self.pending.values() if not item.sending]
            for rid in list(self.pending):
                self._finish(rid, reason)
        for item in unanswered:
            try:
                item.callback("deny", reason)
            except Exception:
                # A disconnected recipient must not prevent the others from receiving their denial.
                continue
