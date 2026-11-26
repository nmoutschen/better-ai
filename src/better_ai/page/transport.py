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

MAX_LINE = 4 * 1024 * 1024


class ProcessTransport:
    """The driver thread owns the codec. Reader threads only drain the child's pipes."""

    def __init__(self, argv, cwd, env, codec, *, pass_fds=()):
        self.codec = codec(self._send)
        self._messages = queue.Queue(maxsize=16)
        self._events = deque()
        self._tail = deque(maxlen=10)
        self._tail_lock = threading.Lock()
        self._closed = threading.Event()
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
        for reader in self._readers:
            reader.start()

    @property
    def stderr(self) -> str:
        with self._tail_lock:
            return "\n".join(self._tail)

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
            while line := self._proc.stderr.readline(4096):
                with self._tail_lock:
                    self._tail.append(line.decode("utf-8", errors="replace").rstrip())
        except OSError:
            pass

    def _send(self, message: dict) -> None:
        data = memoryview((json.dumps(message, ensure_ascii=True) + "\n").encode("ascii"))
        fd = self._proc.stdin.fileno()
        deadline = time.monotonic() + 0.5
        while data:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([], [fd], [], remaining)[1]:
                raise TimeoutError("harness did not read its stdin")
            try:
                data = data[os.write(fd, data) :]
            except BlockingIOError:
                continue

    def open(self, cwd: str, resume: str | None) -> None:
        self.codec.open(cwd, resume)

    def prompt(self, text: str) -> None:
        self.codec.prompt(text)

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
        if message is None:
            return SimpleNamespace(kind="failed", outcome="crashed", text=self.stderr)
        self._events.extend(self.codec.receive(message))
        # Even a frame with no state change is harness activity for the stall timer.
        return self._events.popleft() if self._events else SimpleNamespace(kind="output")

    def close(self) -> None:
        if self._closed.is_set():
            return
        self._closed.set()
        self._proc.stdin.close()
        with contextlib.suppress(ProcessLookupError):
            os.killpg(self.pid, signal.SIGTERM)
        with contextlib.suppress(subprocess.TimeoutExpired):
            self._proc.wait(timeout=0.2)
        # The session leader can exit as soon as it receives cancel, leaving its workers.
        with contextlib.suppress(ProcessLookupError):
            os.killpg(self.pid, signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired):
            self._proc.wait(timeout=0.5)
        for reader, stream in zip(self._readers, (self._proc.stdout, self._proc.stderr), strict=True):
            reader.join(timeout=0.2)
            if not reader.is_alive():
                stream.close()
