"""Pair one tab and bind each permission answer to the driver's in-memory copy of a tool call."""

import hashlib
import json
import os
import re
import secrets
import stat
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import webauthn


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


def credential_file():
    if sys.platform == "darwin":
        data = Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    if not data.is_absolute():
        data = Path.home() / ".local" / "share"
    return data / "better-ai" / "page-credential.json"


def load_credential(path):
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except FileNotFoundError:
        return None
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_size > 8192
            or (os.name == "posix" and (info.st_mode & 0o077 or info.st_uid != os.getuid()))
        ):
            raise ValueError("Credential file must be private")
        key = json.load(stream)
    if not isinstance(key, dict) or not all(isinstance(key.get(k), str) for k in ("id", "x", "y")):
        raise ValueError("Invalid stored credential")
    webauthn.decode(key["id"])
    webauthn.public_point(bytes.fromhex(key["x"]), bytes.fromhex(key["y"]))
    return key


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
    path = Path(name).resolve()
    protected = {
        "appdata",
        "application support",
        "claude",
        "codex",
        "opencode",
        "cursor",
        "droid",
        "devin",
        "better-ai",
    }
    return not any(p.startswith(".") or p.casefold() in protected for p in Path(name).parts + path.parts)


@dataclass
class Request:
    wire_id: object
    tool: str
    arguments: str
    options: tuple
    callback: Callable
    challenge: str = ""
    choice: str = ""


class ApprovalGate:
    def __init__(
        self, unit_path, origin, *, require_presence=True, credential_path=None, archive=None, record_verbs=()
    ):
        self.unit = Path(unit_path).absolute()
        self.origin = origin
        self.require_presence = require_presence
        self.path = Path(credential_path) if credential_path is not None else credential_file()
        self.credential = load_credential(self.path) if require_presence else None
        self.deadline = time.monotonic() + 120
        self.enrollment_challenge = ""
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

    def enrolled(self):
        with self.lock:
            return not self.require_presence or self.credential is not None

    def _enrolling(self):
        if self.enrolled() or time.monotonic() >= self.deadline:
            raise ValueError("Enrollment is closed")

    def begin_enrollment(self):
        with self.lock:
            self._enrolling()
            self.enrollment_challenge = secrets.token_urlsafe(32)
            return {
                "challenge": self.enrollment_challenge,
                "rp": {"id": "localhost", "name": "Better AI approvals"},
                "user": {"id": secrets.token_urlsafe(32), "name": "local-user", "displayName": "Local user"},
                "pubKeyCredParams": [{"type": "public-key", "alg": -7}],
                "attestation": "none",
                "authenticatorSelection": {"userVerification": "preferred"},
            }

    def finish_enrollment(self, proof):
        with self.lock:
            self._enrolling()
            challenge, self.enrollment_challenge = self.enrollment_challenge, ""
            if not challenge:
                raise ValueError("Begin enrollment first")
            key = webauthn.register(proof, challenge, self.origin)
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            # Publish only complete bytes and never replace the winning enrollment of another server.
            temp = self.path.with_name(".credential-" + secrets.token_hex(12))
            with os.fdopen(os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as output:
                try:
                    json.dump(key, output)
                    output.flush()
                    os.link(temp, self.path)
                finally:
                    temp.unlink()
            self.credential = key

    def receive(self, event, callback):
        with self.lock:
            try:
                tool = display(event.tool)
                args = display(event.arguments)
                if not isinstance(event.tool, str) or not event.tool or len(tool) + len(args) > 131072:
                    raise ValueError
                repeatable = repeatable_read(event.tool, event.arguments)
            except (ValueError, TypeError, RecursionError, OSError, RuntimeError):
                callback("deny", "Cannot display the full tool request")
                return
            if "allow_once" not in event.options:
                callback("deny", "Request has no allow-once option")
                return
            if repeatable and (tool, args) in self.grants:
                callback("allow_once", "Allowed earlier for this session")
                return
            if (
                event.tool == "Bash"
                and isinstance(event.arguments, dict)
                and set(event.arguments) == {"command"}
                and self.digest is not None
                and verb_command(event.arguments["command"], self.unit, self.archive, self.record_verbs)
                and self._hash() == self.digest
            ):
                self.notice = "The page agent can run its page commands without asking."
                callback("allow_once", "Approved page command")
                return
            options = ("allow_once", "allow_session", "deny") if repeatable else ("allow_once", "deny")
            self.pending[secrets.token_urlsafe(24)] = Request(event.request_id, tool, args, options, callback)

    def snapshot(self):
        with self.lock:
            return {
                "notice": self.notice,
                "last_outcome": self.last_outcome,
                "approvals": [
                    {"id": rid, "tool": item.tool, "arguments": item.arguments, "options": list(item.options)}
                    for rid, item in self.pending.items()
                ],
            }

    def waiting(self):
        with self.lock:
            return bool(self.pending)

    def _get(self, rid):
        if not isinstance(rid, str) or rid not in self.pending:
            raise ValueError(self.outcomes.get(rid, "Unknown approval") if isinstance(rid, str) else "Unknown approval")
        return self.pending[rid]

    def challenge(self, rid, choice):
        with self.lock:
            item = self._get(rid)
            if choice not in item.options or choice == "deny":
                raise ValueError("Invalid approval choice")
            if not self.require_presence:
                return None
            if not self.credential:
                raise ValueError("Enroll first")
            item.challenge, item.choice = secrets.token_urlsafe(32), choice
            return {
                "challenge": item.challenge,
                "rpId": "localhost",
                "userVerification": "preferred",
                "allowCredentials": [{"type": "public-key", "id": self.credential["id"]}],
            }

    def _finish(self, rid, reason):
        del self.pending[rid]
        self.last_outcome = self.outcomes[rid] = reason

    def answer(self, rid, choice, proof=None):
        with self.lock:
            item = self._get(rid)
            if choice not in item.options:
                raise ValueError("Invalid approval choice")
            if choice != "deny" and self.require_presence:
                challenge, item.challenge = item.challenge, ""
                if not self.credential or not challenge or item.choice != choice:
                    raise ValueError("Request needs a fresh WebAuthn assertion")
                webauthn.verify(proof, challenge, self.origin, self.credential)
            if choice == "allow_session":
                self.grants.add((item.tool, item.arguments))
            allowed = choice != "deny"
            reason = (
                "allowed for this session"
                if choice == "allow_session"
                else ("allowed once" if allowed else "denied by the user")
            )
            self._finish(rid, reason)
            item.callback("allow_once" if allowed else "deny", reason)

    def closed(self, event):
        with self.lock:
            for rid, item in list(self.pending.items()):
                if event.request_id == item.wire_id:
                    self._finish(rid, event.text or event.outcome or "expired")

    def close(self, reason):
        with self.lock:
            self.grants.clear()
            self.notice = ""
            for rid, item in list(self.pending.items()):
                self._finish(rid, reason)
                item.callback("deny", reason)
