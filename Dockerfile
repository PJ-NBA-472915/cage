FROM ubuntu:questing

ARG REPOSITORY
ARG BRANCH
ARG SETUP_SCRIPT
ARG REPO_NAME="repo"
ARG ENTRYPOINT="scripts/entrypoints/sleep.sh"

RUN apt-get update && apt-get install -y \
    git

WORKDIR /tmp/setup

COPY ${SETUP_SCRIPT:-scripts/environments/basic-echo.sh} .
RUN chmod +x ${SETUP_SCRIPT} \
  && ./${SETUP_SCRIPT}

WORKDIR /workspace

RUN git clone ${REPOSITORY} ${REPO_NAME}

WORKDIR /workspace/${REPO_NAME}

RUN git checkout -B ${BRANCH}

COPY ${ENTRYPOINT} .
RUN chmod +x ${ENTRYPOINT}

CMD ["./${ENTRYPOINT}"]