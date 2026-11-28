"""Run a harness codec over a dedicated child process's JSON lines."""

from __future__ import annotations

import contextlib
import json
import os
import queue
import select
import signal
import subprocess
import threading
import time
from collections import deque
from types import SimpleNamespace

STDERR_OUTPUT = object()
WRITE_FAILED = object()
MAX_LINE = 4 * 1024 * 1024
WRITE_TIMEOUT = 5


def _ps(field: str, pid: int) -> str | None:
    """One `ps` field of a process, or None when it does not exist."""
    if type(pid) is not int or pid <= 0 or pid > 2**31 - 1:
        return None
    try:
        done = subprocess.run(
            ["ps", "-ww", "-o", f"{field}=", "-p", str(pid)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    text = done.stdout.strip()
    return text if done.returncode == 0 and text else None


def process_command(pid: int | None) -> str | None:
    """The command line of a running process, to compare with what was recorded before ending it."""
    return _ps("command", pid) if pid is not None else None


def process_started(pid: int | None) -> str | None:
    """When a running process started, as `ps` prints it."""
    return _ps("lstart", pid) if pid is not None else None


def same_command(command: str | None, argv) -> bool:
    """Whether a `ps` command line is the recorded argv. `ps` shows the resolved path of argv[0], which can have another name, so the arguments decide."""
    if not command or not isinstance(argv, list) or not argv:
        return False
    rest = " ".join(str(part) for part in argv[1:])
    name = os.path.basename(str(argv[0]))
    if rest:
        return command.endswith(" " + rest)
    return os.path.basename(command) == name


def end_orphan(pid, argv) -> bool:
    """End the process group of an earlier server's harness child, only if its command line is the recorded one."""
    if type(pid) is not int or pid <= 1 or not isinstance(argv, list) or not argv:
        return False
    if not same_command(process_command(pid), argv):
        return False
    for signum in (signal.SIGTERM, signal.SIGKILL):
        try:
            if os.getpgid(pid) != pid:
                return False
            os.killpg(pid, signum)
        except ProcessLookupError:
            return True
        if signum == signal.SIGTERM:
            time.sleep(0.2)
    return True


class ProcessTransport:
    """The driver thread owns the codec. Reader threads only drain the child's pipes."""

    def __init__(self, argv, cwd, env, codec, *, pass_fds=()):
        self.codec = codec(self._send)
        self._messages = queue.Queue(maxsize=16)
        self._events = deque()
        self._tail = deque(maxlen=10)
        self._tail_lock = threading.Lock()
        self._closed = threading.Event()
        self._outbox = queue.Queue()
        self.argv = [str(part) for part in argv]
        self._proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            pass_fds=pass_fds,
        )
        self.pid = self._proc.pid
        os.set_blocking(self._proc.stdin.fileno(), False)
        self._readers = [
            threading.Thread(target=target, daemon=True) for target in (self._read_messages, self._read_stderr)
        ]
        self._writer = threading.Thread(target=self._write_messages, daemon=True)
        for thread in (*self._readers, self._writer):
            thread.start()

    @property
    def stderr(self) -> str:
        with self._tail_lock:
            return "".join(self._tail)

    def _put(self, message) -> None:
        while not self._closed.is_set():
            try:
                self._messages.put(message, timeout=0.1)
                return
            except queue.Full:
                pass

    def _read_messages(self) -> None:
        try:
            while line := self._proc.stdout.readline(MAX_LINE + 1):
                if len(line) > MAX_LINE:
                    break
                try:
                    message = json.loads(line)
                except ValueError:
                    continue
                if isinstance(message, dict):
                    self._put(message)
        except OSError:
            pass
        self._put(None)

    def _read_stderr(self) -> None:
        try:
            while chunk := self._proc.stderr.read1(4096):
                with self._tail_lock:
                    self._tail.append(chunk.decode("utf-8", errors="replace"))
                self._put(STDERR_OUTPUT)
        except OSError:
            pass

    def _send(self, message: dict) -> None:
        """Hand the message to the writer thread, so a harness that stops reading never blocks the driver loop."""
        self._outbox.put((json.dumps(message, ensure_ascii=True) + "\n").encode("ascii"))

    def _write_messages(self) -> None:
        """The only thread that touches stdin: it writes, and it closes the pipe when it is told to stop or fails."""
        stdin = self._proc.stdin
        fd = stdin.fileno()
        try:
            while (data := self._outbox.get()) is not None:
                data = memoryview(data)
                deadline = time.monotonic() + WRITE_TIMEOUT
                while data:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not select.select([], [fd], [], remaining)[1]:
                        raise TimeoutError("harness did not read its stdin")
                    try:
                        data = data[os.write(fd, data) :]
                    except BlockingIOError:
                        continue
        except (OSError, ValueError):
            # A write that is late or partial leaves the harness in an unknown state: the driver ends it.
            self._put(WRITE_FAILED)
        finally:
            with contextlib.suppress(OSError, ValueError):
                stdin.close()

    def open(self, cwd: str, resume: str | None) -> None:
        self.codec.open(cwd, resume)

    def prompt(self, text: str, uuid: str | None = None) -> None:
        self.codec.prompt(text, uuid)

    def cancel(self) -> None:
        self.codec.cancel()

    def answer(self, request_id: int | str, choice: str, reason: str = "") -> bool:
        return self.codec.answer(request_id, choice, reason)

    def poll(self, timeout: float):
        if self._events:
            return self._events.popleft()
        try:
            message = self._messages.get(timeout=timeout)
        except queue.Empty:
            return None
        if message is STDERR_OUTPUT:
            return SimpleNamespace(kind="output")
        if message is WRITE_FAILED:
            return SimpleNamespace(kind="failed", outcome="crashed", text="the harness did not read its input")
        if message is None:
            return SimpleNamespace(kind="failed", outcome="crashed", text=self.stderr)
        self._events.extend(self.codec.receive(message))
        # A frame the codec knows but maps to no event is still harness activity, and a known message (S112).
        return self._events.popleft() if self._events else SimpleNamespace(kind="frame")

    def close(self) -> None:
        """End the harness's process group and return only once it is gone."""
        if self._closed.is_set():
            return
        self._closed.set()
        self._outbox.put(None)
        signal_error = None
        for signum in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(self.pid, signum)
            except ProcessLookupError:
                break
            except PermissionError as error:
                signal_error = error
            if signum == signal.SIGTERM:
                # Reap the leader after the final signal so the group ID cannot be reused.
                time.sleep(0.2)
        with contextlib.suppress(subprocess.TimeoutExpired):
            self._proc.wait(timeout=0.5)
        for reader, stream in zip(self._readers, (self._proc.stdout, self._proc.stderr), strict=True):
            reader.join(timeout=0.2)
            if not reader.is_alive():
                stream.close()
        # On macOS a group that contains only unreaped processes can refuse a signal.
        if signal_error is not None and (
            self._proc.returncode is None or any(reader.is_alive() for reader in self._readers)
        ):
            raise signal_error
        self._writer.join(timeout=0.5)
        deadline = time.monotonic() + 2
        while self._group_alive() and time.monotonic() < deadline:
            time.sleep(0.05)
        if self._group_alive():
            raise OSError("the harness's process group did not end")

    def _group_alive(self) -> bool:
        self._proc.poll()
        try:
            os.killpg(self.pid, 0)
        except (ProcessLookupError, PermissionError):
            return False
        return True
