"""Inject the contracts from the production commit function into Nagini input."""

import ast
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / "src/better_ai/paths.py"
ADAPTER = HERE / "production_commit_adapter.py"
MARKER = "# nagini: "


def annotated_commit(source: str) -> str:
    (function,) = [
        node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == "_commit_locked"
    ]
    assert function.end_lineno is not None
    lines = source.splitlines(keepends=True)[function.lineno - 1 : function.end_lineno]
    instrumented = []
    contract_lines = set()
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(MARKER):
            indentation = line[: len(line) - len(stripped)]
            contract = stripped.removeprefix(MARKER)
            match ast.parse(contract).body:
                case [ast.Expr(value=ast.Call(func=ast.Name(id="Requires" | "Ensures")))]:
                    pass
                case _:
                    raise ValueError("Nagini annotations must be Requires or Ensures expressions")
            contract_lines.add(len(instrumented) + 1)
            instrumented.append(indentation + contract)
        else:
            instrumented.append(line)
    result = "".join(instrumented)
    (generated,) = ast.parse(result).body
    assert isinstance(generated, ast.FunctionDef)
    generated.body = [node for node in generated.body if node.lineno not in contract_lines]
    if not contract_lines or ast.dump(generated) != ast.dump(function):
        raise ValueError("expected the production commit body with verification contracts alongside it")
    return result


if __name__ == "__main__":
    print(ADAPTER.read_text(encoding="utf-8"))
    print(annotated_commit(SOURCE.read_text(encoding="utf-8")))
