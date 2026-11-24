"""Verify the shipped record commit function and an intervening-writer control."""

import ast
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

SOURCE = Path(__file__).resolve().parents[2] / "src/better_ai/paths.py"
IMAGE = "ghcr.io/bigtalk-org/docker-nagini@sha256:0a77b3dddfafb87393f2aef82e6ce8d29d37e5af95d7480d14f977e4f0b1fe3a"
MARKER = "# nagini: "

# This describes the filesystem boundary. The commit function itself comes from SOURCE.
FILESYSTEM_CONTRACTS = """\
from typing import Optional
from nagini_contracts.contracts import Acc, Assert, ContractOnly, Ensures, Old, Pure, Requires, Result

@Pure
@ContractOnly
def same_contents(current: Optional[bytes], expected: Optional[bytes]) -> bool:
    pass

class _RecordFile:
    def __init__(self, contents: Optional[bytes]) -> None:
        Ensures(Acc(self.contents) and self.contents is contents)
        self.contents: Optional[bytes] = contents

    @ContractOnly
    def matches(self, expected: Optional[bytes]) -> bool:
        Requires(Acc(self.contents))
        Ensures(Acc(self.contents) and self.contents is Old(self.contents))
        Ensures(Result() == same_contents(self.contents, expected))
        pass

    @ContractOnly
    def publish(self, replacement: bytes) -> None:
        Requires(Acc(self.contents))
        Ensures(Acc(self.contents) and self.contents is replacement)
        pass

    @ContractOnly
    def allow_intervening_writer(self) -> None:
        Requires(Acc(self.contents))
        Ensures(Acc(self.contents))
        pass
"""


def commit_cases(source: str) -> tuple[str, str]:
    (original,) = [
        node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == "_commit_locked"
    ]
    assert original.end_lineno is not None
    lines = source.splitlines(keepends=True)[original.lineno - 1 : original.end_lineno]
    contracts = set()
    for index, line in enumerate(lines):
        if line.lstrip().startswith(MARKER):
            indent, contract = line.split(MARKER, 1)
            match ast.parse(contract).body:
                case [ast.Expr(value=ast.Call(func=ast.Name(id="Requires" | "Ensures")))]:
                    pass
                case _:
                    raise ValueError("expected a Requires or Ensures contract")
            contracts.add(index + 1)
            lines[index] = indent + contract

    verified = "".join(lines)
    (generated,) = ast.parse(verified).body
    assert isinstance(generated, ast.FunctionDef)
    generated.body = [statement for statement in generated.body if statement.lineno not in contracts]
    if not contracts or ast.dump(generated) != ast.dump(original):
        raise ValueError("proof input must retain the production body")

    (publish,) = [
        statement.lineno - 1
        for statement in generated.body
        if isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and isinstance(statement.value.func, ast.Attribute)
        and statement.value.func.attr == "publish"
    ]
    lines[publish:publish] = [
        "    record.allow_intervening_writer()\n",
        "    Assert(same_contents(record.contents, expected))\n",
    ]
    return verified, "".join(lines)


def verify(folder: Path, name: str) -> subprocess.CompletedProcess:
    output = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--platform",
            "linux/amd64",
            "--network",
            "none",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--mount",
            f"type=bind,source={folder},target=/code,readonly",
            IMAGE,
            f"/code/{name}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    print(output.stdout, end="")
    return output


def main() -> None:
    production, interrupted = commit_cases(SOURCE.read_text(encoding="utf-8"))
    with TemporaryDirectory() as scratch:
        folder = Path(scratch)
        (folder / "production.py").write_text(FILESYSTEM_CONTRACTS + "\n" + production, encoding="utf-8")
        (folder / "interrupted.py").write_text(FILESYSTEM_CONTRACTS + "\n" + interrupted, encoding="utf-8")
        if verify(folder, "production.py").returncode:
            raise SystemExit("Nagini did not verify the production function")
        rejection = verify(folder, "interrupted.py")
        if (
            rejection.returncode != 1
            or "Assertion same_contents(record.contents, expected) might not hold" not in rejection.stdout
        ):
            raise SystemExit("expected Nagini to reject publication after an intervening writer")
        print("Intervening writer rejected as expected.")


if __name__ == "__main__":
    main()
