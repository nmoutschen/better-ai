"""The Claude permission prompt tool uses only its standard streams and an inherited channel."""

from __future__ import annotations

import argparse
import json
import secrets
import socket
import sys
import threading
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

MCP_SERVER = "better_page"
MCP_TOOL = "approve"
CLAUDE_PROMPT_TOOL = f"mcp__{MCP_SERVER}__{MCP_TOOL}"
MAX_MESSAGE = 128 * 1024


def claude_permission_config(interpreter: Path, bundle: Path, fd: int) -> dict:
    return {
        "mcpServers": {
            MCP_SERVER: {"command": str(interpreter), "args": [str(bundle), "permission-relay", "--fd", str(fd)]}
        }
    }


def _deny(reason: str) -> dict:
    return {"behavior": "deny", "message": reason}


def _load(line: bytes | str) -> dict:
    try:
        data = json.loads(line)
        return data if isinstance(data, dict) else {}
    except (ValueError, RecursionError):
        return {}


@dataclass
class Pending:
    ack: threading.Event = field(default_factory=threading.Event)
    done: threading.Event = field(default_factory=threading.Event)
    answer: dict | None = None


class Relay:
    def __init__(self, channel: socket.socket, *, ack_timeout: float = 10):
        self.channel = channel
        self.channel.settimeout(min(0.25, ack_timeout))
        self.ack_timeout = ack_timeout
        self.pending: dict[str, Pending] = {}
        self.lock = threading.Lock()
        self.write_lock = threading.Lock()
        self.closed = False
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def __enter__(self) -> Relay:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
        self.reader.join()

    def close(self) -> None:
        with self.lock:
            if self.closed:
                return
            self.closed = True
            self.channel.close()
            for pending in self.pending.values():
                pending.ack.set()
                pending.done.set()

    def _read(self) -> None:
        buffer = b""
        try:
            while True:
                try:
                    chunk = self.channel.recv(4096)
                except TimeoutError:
                    continue
                if not chunk:
                    return
                *lines, buffer = (buffer + chunk).split(b"\n")
                if len(buffer) > MAX_MESSAGE:
                    return
                for line in lines:
                    if len(line) > MAX_MESSAGE:
                        return
                    self._receive(_load(line))
        except OSError:
            pass
        finally:
            self.close()

    def _receive(self, message: dict) -> None:
        request_id = message.get("id")
        if not isinstance(request_id, str):
            return
        with self.lock:
            pending = self.pending.get(request_id)
            if pending is None or pending.done.is_set():
                return
            if message.get("type") == "ack":
                pending.ack.set()
            elif message.get("type") == "answer" and pending.ack.is_set():
                pending.answer = message
                pending.done.set()

    def approve(self, arguments: dict) -> dict:
        tool, inputs = arguments.get("tool_name"), arguments.get("input")
        if not isinstance(tool, str) or not tool or not isinstance(inputs, dict):
            return _deny("the permission request lacks its tool or arguments")
        request_id = secrets.token_hex(16)
        pending = Pending()
        message = json.dumps({"type": "permission", "id": request_id, "arguments": arguments}).encode() + b"\n"
        if len(message) > MAX_MESSAGE:
            return _deny("the permission request is too large to relay")
        with self.lock:
            if self.closed:
                return _deny("the permission relay is closed")
            self.pending[request_id] = pending
        try:
            with self.write_lock:
                self.channel.sendall(message)
            if not pending.ack.wait(self.ack_timeout):
                return _deny("the page driver did not acknowledge the permission request")
            pending.done.wait()
            if pending.answer is None:
                return _deny("the permission relay closed")
            if pending.answer.get("allow") is True:
                return {"behavior": "allow", "updatedInput": inputs}
            reason = pending.answer.get("reason")
            return _deny(reason if isinstance(reason, str) and reason else "the page denied permission")
        except OSError:
            # A partial write makes the rest of the channel unusable.
            self.close()
            return _deny("the permission relay closed")
        finally:
            with self.lock:
                self.pending.pop(request_id, None)


def _tools() -> dict:
    return {
        "tools": [
            {
                "name": MCP_TOOL,
                "description": "Ask the user for tool permission on the page",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string"},
                        "input": {"type": "object"},
                        "tool_use_id": {"type": "string"},
                    },
                    "required": ["tool_name", "input"],
                },
            }
        ]
    }


def _serve(relay: Relay, lines: Iterable[str], out) -> None:
    lock = threading.Lock()

    def send(request_id, **body):
        with lock:
            out(json.dumps({"jsonrpc": "2.0", "id": request_id, **body}))

    def approve(request_id, arguments):
        result = relay.approve(arguments)
        send(request_id, result={"content": [{"type": "text", "text": json.dumps(result)}]})

    with ThreadPoolExecutor(max_workers=8) as workers:
        try:
            for line in lines:
                message = _load(line) if len(line) <= MAX_MESSAGE else {}
                method, request_id = message.get("method"), message.get("id")
                if type(request_id) not in (int, str):
                    continue
                params = message.get("params")
                params = params if isinstance(params, dict) else {}
                if method == "initialize":
                    send(
                        request_id,
                        result={
                            "protocolVersion": "2025-06-18",
                            "capabilities": {"tools": {}},
                            "serverInfo": {"name": MCP_SERVER, "version": "1"},
                        },
                    )
                elif method == "tools/list":
                    send(request_id, result=_tools())
                elif method == "ping":
                    send(request_id, result={})
                elif method == "tools/call" and params.get("name") == MCP_TOOL:
                    arguments = params.get("arguments")
                    workers.submit(approve, request_id, arguments if isinstance(arguments, dict) else {})
                else:
                    send(request_id, error={"code": -32601, "message": "method not supported"})
        finally:
            relay.close()


def arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--fd", type=int, required=True, help=argparse.SUPPRESS)


def run(args: argparse.Namespace, context) -> int:
    if args.fd < 3:
        return 1
    try:
        channel = socket.socket(fileno=args.fd)
    except OSError:
        return 1
    with Relay(channel) as relay:
        _serve(relay, context.stdin or sys.stdin, context.out)
    return 0
