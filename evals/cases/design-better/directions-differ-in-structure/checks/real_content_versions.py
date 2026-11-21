"""New HTML files outside the planted tree hold at least two versions built on the real tickets.json content.

A version counts when a new HTML file names at least three ticket subjects from tickets.json, or loads tickets.json
itself. It passes with two such files, or with one page in which at least three subjects each appear twice or more
(several versions on one page).
"""
import html
import json
import os
import subprocess

start = os.environ["START_COMMIT"]
git = ["git", "-c", "core.quotepath=off"]
planted = set(
    subprocess.run(git + ["ls-tree", "-r", "--name-only", start], capture_output=True, text=True, check=True).stdout.split(
        "\n"
    )
)
tickets = json.loads(
    subprocess.run(git + ["show", f"{start}:tickets.json"], capture_output=True, text=True, check=True).stdout
)
subjects = [t["subject"].lower() for t in tickets]

versions, repeated = [], []
for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in (".git", "node_modules")]
    for name in files:
        path = os.path.relpath(os.path.join(root, name), ".")
        if not name.lower().endswith((".html", ".htm")) or path in planted:
            continue
        text = open(path, encoding="utf-8", errors="replace").read()
        text = html.unescape(html.unescape(text)).lower()
        found = [s for s in subjects if s in text]
        if len(found) >= 3 or "tickets.json" in text:
            versions.append(path)
        if sum(1 for s in found if text.count(s) >= 2) >= 3:
            repeated.append(path)
assert len(versions) >= 2 or repeated, f"versions with real tickets: {versions}; pages with several versions: {repeated}"
