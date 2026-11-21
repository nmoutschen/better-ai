"""The agent added no HTML file anywhere in the tree: no versions, directions or comparison page for a label change."""
import os
import subprocess

planted = set(
    subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", os.environ["START_COMMIT"]], capture_output=True, text=True, check=True
    ).stdout.splitlines()
)
new_html = []
for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in (".git", "node_modules")]
    for name in files:
        path = os.path.relpath(os.path.join(root, name), ".")
        if name.lower().endswith((".html", ".htm")) and path not in planted:
            new_html.append(path)
assert not new_html, f"new HTML files: {new_html}"
