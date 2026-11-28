"""Pair one tab, and the one command form the driver approves without asking."""

import os
import re
import secrets
import shlex
import sys
import threading
from pathlib import Path

from . import REPLY_STATES


class Pairing:
    """One tab at a time. A token is good once; the tab that exchanges it gets a new secret, and the old tab's secret
    stops working at that moment, not when the token is made (S84, S85)."""

    def __init__(self, origin):
        self.origin = origin
        self.changed = threading.Condition()
        self.token = self.secret = ""
        self.generation = 0  # counts the pairings, for the one that waits for the next

    def issue(self):
        with self.changed:
            self.token = secrets.token_urlsafe(32)
            return self.token

    def revoke(self):
        """Give up the token that was issued and not used: it pairs nothing from now on."""
        with self.changed:
            self.token = ""

    @staticmethod
    def matches(provided, expected):
        return bool(
            expected and isinstance(provided, str) and provided.isascii() and secrets.compare_digest(provided, expected)
        )

    def exchange(self, token, origin):
        with self.changed:
            if origin != self.origin or not self.matches(token, self.token):
                raise ValueError("opened elsewhere")
            self.token = ""
            self.secret = secrets.token_urlsafe(32)
            self.generation += 1
            self.changed.notify_all()
            return self.secret

    def wait_after(self, generation, seconds):
        """Whether a tab paired after `generation`, waiting up to `seconds` for it."""
        with self.changed:
            return self.changed.wait_for(lambda: self.generation > generation, seconds)

    def valid(self, secret, origin):
        with self.changed:
            return origin == self.origin and self.matches(secret, self.secret)


# Only these shell words are accepted outside the quoted heredoc: a bare word of the characters shlex.quote leaves
# bare, or a word as shlex.quote writes one it quotes ('...', with each ' written as '"'"'). The interpreter, archive and
# unit must be exactly shlex.quote of their paths; every other word must be bare.
WORD = re.compile(r"[A-Za-z0-9_@%+=:,./-]+|'[^']*'(?:\"'\"'[^']*')*")
BARE = re.compile(r"[A-Za-z0-9_@%+=:,./-]+")
IDENT = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")
TAG = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,31}")
LINE = re.compile(r"[0-9]+")  # the value of --read: a line of the log, as pending prints it
FLAGS = {
    "reply": {"--by", "--to", "--state", "--read"},
    "status": {"--by", "--read"},
    "pending": set(),
    "check": set(),
    "summary": set(),
    "specs": set(),
    "add": {"--by", "--for", "--id"},
    "set": {"--by", "--for", "--unset", "--raw"},
}
# Every skill has these verbs; the others are approved only where the unit's skill has them.
SHARED_VERBS = ("status", "reply", "pending", "check")
SKILL_VERBS = ("summary", "specs", "add", "set")
NAMES = {"--by", "--for"}


def verbs_of(skill_verbs):
    """The verbs approved without asking for a unit whose skill has `skill_verbs`, in a fixed order."""
    return SHARED_VERBS + tuple(verb for verb in SKILL_VERBS if verb in skill_verbs)


def approved_form(command, unit, verbs):
    """The one sentence that says which command is approved without asking: the turn's header and the denial hold it."""
    return (
        f"{command} <verb> {shlex.quote(str(unit))} <arguments>, where <verb> is one of {', '.join(verbs_of(verbs))}, "
        "--read <n> on reply and status with n the line pending gives, "
        "text only as a quoted heredoc (<<'EOF', the text, then EOF on its own line), "
        "and --by or --for naming an agent other than user"
    )


# Claude Code's Bash input is {command, description} and may add timeout (bash_prefix_request in
# tests/fixtures/page_wire/claude_2_1_332.json); run_in_background and dangerouslyDisableSandbox, from the same tool's
# input schema, run the command another way than the form says.
CLAUDE_BASH_KEYS = frozenset({"command", "description", "timeout"})
# Codex runs a command as "<shell> -lc <command>" and sends that line in `command` (command_request in
# tests/fixtures/page_wire/codex_0_172_0.json); a zsh-exec-bridge subcommand comes as the command itself (approvalId
# in CommandExecutionRequestApprovalParams, `codex app-server generate-json-schema` 0.172.0). The params are the same
# under every approvalPolicy and sandbox. Only kind command runs a command; writeStdin and humanCommand do not.
LOGIN_SHELLS = frozenset({"bash", "sh", "zsh"})


# The harnesses whose shell request shape is on record (shell_request): only on these is a call approved without asking.
AUTO_APPROVING = frozenset({"claude", "codex"})
NO_FORM = "none: each call is asked on the page"


def header_form(harness, command, unit, verbs):
    """What a turn's header says is approved without asking on `harness` (S95; D24 for the harnesses not on record)."""
    return approved_form(command, unit, verbs) if harness in AUTO_APPROVING else NO_FORM


def shell_request(harness, tool, arguments):
    """(the shell command a tool request runs, whether it runs it as written), or None for a request that runs no
    shell command in a shape on record. ACP and Droid record no shell request shape, so theirs are asked."""
    if not isinstance(arguments, dict) or not isinstance(arguments.get("command"), str):
        return None
    command = arguments["command"]
    if harness == "claude" and tool == "Bash":
        return command, set(arguments) <= CLAUDE_BASH_KEYS
    if harness == "codex" and tool == "Command" and arguments.get("kind") in (None, "command"):
        try:
            words = shlex.split(command)
        except ValueError:
            return command, True
        shell, *rest = words or [""]
        if len(rest) == 2 and rest[0] in ("-lc", "-c") and os.path.isabs(shell) and Path(shell).name in LOGIN_SHELLS:
            return rest[1], True
        return command, True
    return None


def own_call(command, archive):
    """Whether a shell command names the driver's own better.pyz by its absolute path, as it is or quoted."""
    return isinstance(command, str) and (str(archive) in command or shlex.quote(str(archive)) in command)


def verb_command(command, unit, archive, verbs, interpreter=None):
    """Recognize the approved form directly; never interpret or normalize arbitrary shell syntax."""
    if not isinstance(command, str) or "\0" in command or "\r" in command:
        return False
    head, sep, body = command.partition("\n")
    if sep:
        head, marker, tag = head.rpartition(" <<'")
        if not marker or not tag.endswith("'") or not TAG.fullmatch(tag[:-1]):
            return False
        lines = body.removesuffix("\n").split("\n")
        if lines[-1] != tag[:-1] or tag[:-1] in lines[:-1]:
            return False
    words = []
    while head:
        match = WORD.match(head)
        if not match:
            return False
        words.append(match[0])
        head = head[match.end() :]
        if head and not head.startswith(" "):
            return False
        head = head.lstrip(" ")
    if len(words) < 4:
        return False
    first, script, verb, target, *args = words
    if (
        first != shlex.quote(interpreter or sys.executable)
        or script != shlex.quote(str(archive))
        or target != shlex.quote(str(unit))
        or verb not in verbs_of(verbs)
        or not all(BARE.fullmatch(arg) for arg in args)
    ):
        return False
    positional = []
    it = iter(args)
    for arg in it:
        if IDENT.fullmatch(arg):
            positional.append(arg)
        elif arg not in FLAGS[verb]:
            return False
        else:
            value = next(it, "")
            if arg == "--raw":
                # The file a record's rule reads to check a quote: an absolute path of bare characters only.
                if not (value.startswith("/") and BARE.fullmatch(value) and "/../" not in value + "/"):
                    return False
                continue
            if arg == "--read":
                if not LINE.fullmatch(value):
                    return False
                continue
            if not IDENT.fullmatch(value) or (arg in NAMES and value == "user"):
                return False
            if arg == "--state" and value not in REPLY_STATES:
                return False
    if verb == "status":
        # Never accepted: the user's word accepts, not the agent's (decision D8).
        return len(positional) >= 2 and positional[0] in {"seen", "asked", "working", "done"}
    return len(positional) == int(verb in {"add", "set"})
