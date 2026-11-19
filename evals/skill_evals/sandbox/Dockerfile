# Sandbox for one eval sample: Python for the planted repositories, Node for Claude Code, and git for
# the starting commit. Built once by compose; each sample gets a fresh container.
FROM node:22-bookworm-slim AS node

FROM python:3.12.12-slim-bookworm

ARG CLAUDE_CODE_VERSION=2.1.327

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
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
