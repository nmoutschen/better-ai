# Sandbox for one eval sample: Python for the planted repositories, Node for Claude Code, git for the
# starting commit, and a headless Chromium with Playwright for cases that render and operate a page. Built once by compose; each sample gets a fresh container.
FROM node:22-bookworm-slim AS node

FROM python:3.12.12-slim-bookworm

ARG CLAUDE_CODE_VERSION=2.1.327
# The same ruff as evals/uv.lock, so a case that names the project's linter can run it here.
ARG RUFF_VERSION=0.17.5

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates libatomic1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "ruff==${RUFF_VERSION}"

# Playwright for Python and its Chromium, shared by every user, so an agent can render and operate a page
# and a hidden check can read a rendered page's computed styles.
ARG PLAYWRIGHT_VERSION=1.65.2
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright
RUN pip install --no-cache-dir "playwright==${PLAYWRIGHT_VERSION}" \
    && playwright install --with-deps chromium \
    && chmod -R a+rX /opt/ms-playwright \
    && rm -rf /var/lib/apt/lists/*

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && npm install -g --no-fund --no-audit "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
    && npm cache clean --force

# The agent and the judge run as separate non-root users with empty homes: no CLAUDE.md, memory or skills.
RUN useradd --create-home --shell /bin/bash agent \
    && useradd --create-home --shell /bin/bash judge \
    && git config --system safe.directory '*' \
    && git config --system user.name Inspect \
    && git config --system user.email inspect@example.invalid \
    && git config --system init.defaultBranch main

COPY run-claude /usr/local/bin/run-claude
RUN chmod 755 /usr/local/bin/run-claude

WORKDIR /work
CMD ["sleep", "infinity"]
