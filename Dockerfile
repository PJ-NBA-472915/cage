# syntax=docker/dockerfile:1.7
FROM ubuntu:questing

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
      xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and writable dirs
RUN groupadd -g ${APP_GID} ${APP_USER} && \
    useradd -m -u ${APP_UID} -g ${APP_GID} -s /bin/bash ${APP_USER} && \
    mkdir -p /app && chown -R ${APP_USER}:${APP_USER} /app

# Install Cursor CLI for the app user
USER ${APP_USER}
RUN curl https://cursor.com/install -fsS | bash

WORKDIR /app

# Create virtual environment and install Python deps
RUN python3 -m venv /app/venv

# Copy requirements and install in virtual environment
COPY --chown=${APP_USER}:${APP_USER} requirements.txt /app/requirements.txt
RUN /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Create logs directory for supervisor
RUN mkdir -p /app/logs && chown -R ${APP_USER}:${APP_USER} /app/logs

# Copy supervisor configuration
COPY --chown=${APP_USER}:${APP_USER} supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy supervisor control script
COPY --chown=${APP_USER}:${APP_USER} scripts/supervisor-control.sh /usr/local/bin/supervisor-control
RUN chmod +x /usr/local/bin/supervisor-control

# Entrypoint & daemon
COPY --chown=${APP_USER}:${APP_USER} pod-entrypoint.sh /usr/local/bin/pod-entrypoint.sh
COPY --chown=${APP_USER}:${APP_USER} agent_daemon_consolidated.py /app/agent_daemon_consolidated.py
RUN chmod +x /usr/local/bin/pod-entrypoint.sh

USER ${APP_USER}

# Update PATH to include virtual environment
ENV PATH="/app/venv/bin:/home/app/.local/bin:$PATH"

EXPOSE 8080

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["pod-entrypoint.sh"]