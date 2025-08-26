# syntax=docker/dockerfile:1.7
FROM ubuntu:22.04

ARG APP_USER=app
ARG APP_UID=10001
ARG APP_GID=10001

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false

# Base OS + Python + tooling (lean, no recommendeds)
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv python3-full python3-dev \
      ca-certificates curl git tini build-essential \
      xz-utils bash \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and writable dirs
RUN groupadd -g ${APP_GID} ${APP_USER} && \
    useradd -m -u ${APP_UID} -g ${APP_GID} -s /bin/bash ${APP_USER} && \
    mkdir -p /app && chown -R ${APP_USER}:${APP_USER} /app

# Install Node.js 20.x for Gemini CLI
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
      curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends \
      nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Cursor CLI for the app user
USER ${APP_USER}
# RUN curl https://cursor.com/install -fsS | bash

# Install Gemini CLI using npx instead of npm install
RUN npx @google/gemini-cli@preview --version

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/home/app/node_modules/.bin/gemini", "--help"]