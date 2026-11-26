"""Run a harness codec over a dedicated child process's JSON lines."""

from __future__ import annotations

import contextlib
import ctypes
import json
import os
import queue
import select
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path
from types import SimpleNamespace

MAX_LINE = 4 * 1024 * 1024


def _darwin_birth(pid: int) -> str | None:
    # PROC_PIDTBSDINFO's public layout in XNU's bsd/sys/proc_info.h.
    class BSDInfo(ctypes.Structure):
        _fields_ = [
            ("flags", ctypes.c_uint32),
            ("status", ctypes.c_uint32),
            ("xstatus", ctypes.c_uint32),
            ("pid", ctypes.c_uint32),
            ("before_names", ctypes.c_uint32 * 8),
            ("comm", ctypes.c_char * 16),
            ("name", ctypes.c_char * 32),
            ("after_names", ctypes.c_uint32 * 6),
            ("seconds", ctypes.c_uint64),
            ("microseconds", ctypes.c_uint64),
        ]

    native = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
    native.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
    info = BSDInfo()
    if native.proc_pidinfo(pid, 3, 0, ctypes.byref(info), ctypes.sizeof(info)) != ctypes.sizeof(info):
        return None
    if info.pid != pid or not info.seconds or not 0 <= info.microseconds < 1_000_000:
        return None
    native.sysctlbyname.argtypes = [
        ctypes.c_char_p,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_size_t),
        ctypes.c_void_p,
        ctypes.c_size_t,
    ]
    boot = ctypes.create_string_buffer(64)
    size = ctypes.c_size_t(len(boot))
    if native.sysctlbyname(b"kern.bootsessionuuid", boot, ctypes.byref(size), None, 0) or not boot.value:
        return None
    return f"{boot.value.decode('ascii')}:{info.seconds}:{info.microseconds}"


def process_birth(pid: int | None) -> str | None:
    """An OS birth marker for comparison before touching a recorded process."""
    if type(pid) is not int or pid <= 0 or pid > 2**31 - 1:
        return None
    try:
        if sys.platform == "darwin":
            return _darwin_birth(pid)
        if sys.platform == "linux":
            boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            # The command name in field 2 can contain spaces and parentheses. Fields start after its last ')'.
            _, separator, fields = Path(f"/proc/{pid}/stat").read_text(errors="replace").rpartition(")")
            started = fields.split()[19]  # field 22: start ticks since boot
            if separator and boot and started.isascii() and started.isdigit():
                return f"{boot}:{started}"
    except (OSError, AttributeError, IndexError, UnicodeError):
        return None
    return None


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
        self.started = process_birth(self.pid)
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
