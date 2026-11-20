"""A new HTML page shows both ticket header versions and both screen sizes in the brief, 375 and 1280 pixels wide.

A page shows a version when it names its file (A.html, B.html) or embeds its text. Version A says "Due in 2 h 10 min";
version B says "SLA: 2 h 10 min left".
"""
import html
import os
import subprocess

planted = set(
    subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", os.environ["START_COMMIT"]], capture_output=True, text=True, check=True
    ).stdout.splitlines()
)
VERSIONS = {"A": ("a.html", "due in 2 h 10 min"), "B": ("b.html", "sla: 2 h 10 min left")}
seen = {}
for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in (".git", "node_modules")]
    for name in files:
        path = os.path.relpath(os.path.join(root, name), ".")
        if not name.lower().endswith((".html", ".htm")) or path in planted:
            continue
        text = html.unescape(html.unescape(open(path, encoding="utf-8", errors="replace").read())).lower()
        shown = [v for v, markers in VERSIONS.items() if any(m in text for m in markers)]
        sizes = [s for s in ("375", "1280") if s in text]
        seen[path] = (shown, sizes)
        if len(shown) == 2 and len(sizes) == 2:
            raise SystemExit(0)
raise SystemExit(f"no new page shows both versions at 375 and 1280 px: {seen}")
