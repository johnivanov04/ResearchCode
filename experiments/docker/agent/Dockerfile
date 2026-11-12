# Agent container for ResearchCode Phase 4 trials (identical for both conditions).
#
# Provides Python 3.12, uv, Git, Node.js 22, and Claude Code 2.1.319, running as an
# unprivileged user with an empty home directory, so no settings, memory, or instruction
# files from the experimenter's machine are visible. Only the trial workspace is mounted.
# Network access goes through the filtering proxy (docker/proxy); see docs/RUNNING_TRIALS.md.
#
# Build: rc-exp build-images   (tag researchcode-agent:2.1.319)

# node:22-bookworm-slim (Node.js 22.23.4), pinned by digest
FROM node@sha256:18052396bf1d0c6e0a8c58181b5c1457da19409efbd5032a3f4d86974e74d13c AS node
# ghcr.io/astral-sh/uv:0.12.19, pinned by digest
FROM ghcr.io/astral-sh/uv@sha256:04d046b13e60d6bcec73cbc5e1cad25d680dea90c8573340950a0ac2d1aef424 AS uv

# python:3.12.14-slim-bookworm, pinned by digest
FROM python@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
COPY --from=uv /uv /uvx /usr/local/bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ARG CLAUDE_CODE_VERSION=2.1.319
RUN npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" && npm cache clean --force

RUN useradd --create-home --uid 1000 --shell /bin/bash agent
USER agent
ENV DISABLE_AUTOUPDATER=1 \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
    UV_LINK_MODE=copy
WORKDIR /workspace
CMD ["bash"]
