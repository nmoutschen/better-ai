"""The sample sandbox: a Docker image with Python, Node, git and Claude Code, behind an allowlist proxy.

`compose.yaml` builds the image once and starts a fresh sandbox and proxy for each sample; the proxy
forwards HTTPS only to the hosts in `proxy-allow.txt`.
"""

from pathlib import Path

COMPOSE = str(Path(__file__).with_name("compose.yaml").resolve())
