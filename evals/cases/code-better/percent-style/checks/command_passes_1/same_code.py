import ast
import os
import subprocess
import sys

path, names = sys.argv[1], sys.argv[2:]


def parts(source):
    lines = source.splitlines()
    found = {}
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found[node.name] = "\n".join(lines[node.lineno - 1 : node.end_lineno])
            last = node.body[-1]
            found[node.name + "[-1]"] = "\n".join(lines[last.lineno - 1 : last.end_lineno])
    return found


planted = subprocess.run(
    ["git", "show", f"{os.environ['START_COMMIT']}:{path}"], capture_output=True, text=True, check=True
).stdout
before, after = parts(planted), parts(open(path).read())
for name in names:
    assert after.get(name) == before[name], f"{name} changed:\n{after.get(name)}"
