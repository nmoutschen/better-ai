"""Pair one tab, and the one command form the driver approves without asking."""

import re
import secrets
import sys
import threading


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
